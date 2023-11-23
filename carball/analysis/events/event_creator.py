import logging
from typing import Dict, Callable

import numpy as np
import pandas as pd

from carball.analysis.events.bump_detection.bump_analysis import BumpAnalysis
from carball.analysis.events.boost_pad_detection.pickup_analysis import PickupAnalysis
from carball.analysis.events.hit_pressure.pressure_analysis import PressureAnalysis
from carball.analysis.events.fifty_fifty.fifty_analysis import FiftyAnalysis
from carball.analysis.events.kickoff_detection.kickoff_analysis import BaseKickoff
from carball.analysis.events.carry_detection import CarryDetection
from carball.analysis.events.hit_detection.base_hit import BaseHit
from carball.analysis.events.hit_detection.hit_analysis import SaltieHit
from carball.analysis.events.dropshot.damage import create_dropshot_damage_events
from carball.analysis.events.dropshot.ball import create_dropshot_ball_events
from carball.generated.api import game_pb2
from carball.generated.api.player_pb2 import Player
from carball.json_parser.game import Game

logger = logging.getLogger(__name__)

class EventsCreator:
    """
        Handles the creation of all events that can then be later used for stats
    """

    def __init__(self, id_creator: Callable):
        self.id_creator = id_creator

    def create_events(self, game: Game, proto_game: game_pb2.Game, player_map: Dict[str, Player],
                      data_frame: pd.DataFrame, kickoff_frames: pd.DataFrame, first_touch_frames: pd.Series,
                      calculate_intensive_events: bool = False):
        """
        Creates all of the event protos.
        :param calculate_intensive_events: Indicates if expensive calculations should run to include additional stats.
        """
        goal_frames = data_frame.game.goal_number.notnull()
        self.create_boostpad_events(proto_game, data_frame)
        self.create_hit_events(game, proto_game, player_map, data_frame, kickoff_frames, first_touch_frames)
        #self.calculate_kickoff_stats(game, proto_game, player_map, data_frame, kickoff_frames, first_touch_frames)
        #self.calculate_ball_carries(game, proto_game, player_map, data_frame[goal_frames])
        #self.create_bumps(game, proto_game, player_map, data_frame[goal_frames])
        #self.create_dropshot_events(game, proto_game, player_map)

        if calculate_intensive_events:
            self.calculate_hit_pressure(game, proto_game, data_frame)
            self.calculate_fifty_fifty(game, proto_game, data_frame)
            # TODO (j-wass): calculate bumps

    def calculate_fifty_fifty(self, game: Game, proto_game: game_pb2.Game, data_frame: pd.DataFrame):
        logger.info("Calculating 50/50s.")
        fiftyAnalysis = FiftyAnalysis(game=game, proto_game=proto_game, data_frame=data_frame)
        fiftyAnalysis.calculate_fifty_fifty_stats()

    def calculate_hit_pressure(self, game: Game, proto_game: game_pb2.Game, data_frame: pd.DataFrame):
        logger.info("Calculating hit pressure.")
        pressureAnalysis = PressureAnalysis(game=game, proto_game=proto_game, data_frame=data_frame)
        pressureAnalysis.calculate_pressure_stats()

    def calculate_kickoff_stats(self, game: Game, proto_game: game_pb2.Game, player_map: Dict[str, Player],
                                data_frame, kickoff_frames, first_touch_frames):
        logger.info("Looking for kickoffs.")
        kickoffs = BaseKickoff.get_kickoffs_from_game(game, proto_game, self.id_creator, player_map, data_frame, kickoff_frames, first_touch_frames)
        logger.info("Found %s kickoffs." % len(kickoffs.keys()))

    def insert_hit(self, proto_game: game_pb2.Game, data_frame: pd.DataFrame, hits, insert_frame, curr_player, collision_distances):
        hits_copy = list(proto_game.game_stats.hits)
        del proto_game.game_stats.hits[:]
        for i in range(len(hits_copy)):
            hit = hits_copy[i]
            old_hit = proto_game.game_stats.hits.add(
                frame_number = hit.frame_number,
                seconds_remaining = hit.seconds_remaining,
                goal_number = hit.goal_number,
                player_id = hit.player_id,
                collision_distance = hit.collision_distance,
                ball_data = hit.ball_data,
                is_kickoff = hit.is_kickoff,
                match_save = hit.match_save,
                match_shot = hit.match_shot,
                match_goal = hit.match_goal,
                match_assist = hit.match_assist
            )
            hits[hit.frame_number] = old_hit
            if hit.frame_number < insert_frame and (i + 1 == len(hits_copy) or hits_copy[i + 1].frame_number > insert_frame):
                if hit.frame_number in collision_distances[curr_player.is_orange][curr_player.name].index:
                    col_dist = collision_distances[curr_player.is_orange][curr_player.name].loc[hit.frame_number]
                else:
                    col_dist = collision_distances[curr_player.is_orange][curr_player.name].loc[hit.frame_number - 1]
                new_hit = proto_game.game_stats.hits.add(
                    frame_number = insert_frame,
                    goal_number = hit.goal_number,
                    player_id = curr_player.id,
                    collision_distance = col_dist,
                    is_kickoff = hit.is_kickoff
                )
                new_hit.ball_data.pos_x = data_frame['ball']['pos_x'].at[insert_frame]
                new_hit.ball_data.pos_y = data_frame['ball']['pos_y'].at[insert_frame]
                new_hit.ball_data.pos_z = data_frame['ball']['pos_z'].at[insert_frame]
                game_info = data_frame.loc[hit.frame_number, 'game']
                game_secs = game_info['seconds_remaining']
                if "is_overtime" in game_info.keys() and game_info['is_overtime']:
                    new_hit.seconds_remaining = -1 if np.isnan(game_secs) else -1 * int(game_secs)
                else:
                    new_hit.seconds_remaining = 0 if np.isnan(game_secs) else int(game_info['seconds_remaining'])
                hits[insert_frame] = new_hit

        return new_hit

    def create_hit_events(self, game: Game, proto_game: game_pb2.Game, player_map: Dict[str, Player],
                          data_frame: pd.DataFrame, kickoff_frames: pd.DataFrame, first_touch_frames: pd.Series):
        """
        Creates all of the events for hits
        """
        logger.info("Looking for hits.")
        hits, collision_distances = BaseHit.get_hits_from_game(game, proto_game, self.id_creator, data_frame, first_touch_frames)
        logger.info("Found %s hits." % len(hits))

        # Scoring hit validation
        # Get frame numbers where scoreboard stats changed
        sb_cols = ['match_goals', 'match_saves', 'match_shots', 'match_assists']
        indices = {}
        for v in player_map.values():
            indices[v.name] = {}
            indices[v.name]['all'] = set()
            for col in sb_cols:
                sb_stat = data_frame[v.name].loc[:, col]
                idx_list = sb_stat[sb_stat.diff() > 0].index.tolist()
                indices[v.name][col] = idx_list
                if col != 'match_assists':
                    indices[v.name]['all'].update(idx_list)
            indices[v.name]['all'] = sorted(indices[v.name]['all'])

        # Check if last hit belongs to player whose stat was changed
        for name in indices.keys():
            curr_player = [player for player in proto_game.players if player.name == name][0]
            for idx in indices[name]['all']:
                hit_list = [hit for hit in proto_game.game_stats.hits if 
                    (hit.player_id.id == curr_player.id.id) and (hit.frame_number <= idx)]
                curr_player_hit = None if len(hit_list) == 0 else hit_list[-1]
                
                team_player_ids = [player.id.id for player in proto_game.players if player.is_orange == curr_player.is_orange]
                last_team_hit = [hit for hit in proto_game.game_stats.hits if 
                    (hit.frame_number <= idx) and (hit.player_id.id in team_player_ids)][-1]

                if curr_player_hit is None or ((last_team_hit.player_id.id != curr_player.id.id) and \
                        (last_team_hit.frame_number - curr_player_hit.frame_number) >= 75):
                    # Hit was misattributed; need to correct
                    curr_player_dist = collision_distances[curr_player.is_orange][curr_player.name].loc[last_team_hit.frame_number]
                    if curr_player_dist > 400:
                        # curr player had 50-50 with opponent, hit needs to be added
                        recent_hit = [hit for hit in proto_game.game_stats.hits if hit.frame_number <= idx][-1]
                        # Insert new hit after recent_hit
                        self.insert_hit(proto_game, data_frame, hits, recent_hit.frame_number + 1, curr_player, collision_distances)
                    else:
                        # Hit by teammate actually belongs to curr player
                        last_team_hit.player_id.id = curr_player.id.id
                        last_team_hit.collision_distance = collision_distances[curr_player.is_orange][curr_player.name].loc[last_team_hit.frame_number]


        # Assign stats separately due to hit corrections
        for name in indices.keys():
            curr_player = [player for player in proto_game.players if player.name == name][0]
            for stat_type in sb_cols:
                for stat_idx in indices[name][stat_type]:
                    hit_list = [hit for hit in proto_game.game_stats.hits if 
                        hit.frame_number <= stat_idx and hit.player_id.id == curr_player.id.id]
                    if len(hit_list) != 0:
                        stat_hit = hit_list[-1]
                    else:
                        min_frame = collision_distances[curr_player.is_orange][curr_player.name].loc[0:stat_idx].idxmin()
                        while len([hit for hit in proto_game.game_stats.hits if hit.frame_number == min_frame]) != 0:
                            min_frame += 1
                        stat_hit = self.insert_hit(proto_game, data_frame, hits, min_frame, curr_player, collision_distances)
                        
                    if stat_type == 'match_goals':
                        stat_hit.match_goal = True
                    elif stat_type == 'match_saves':
                        stat_hit.match_save = True
                    elif stat_type == 'match_shots':
                        stat_hit.match_shot = True
                    else:
                        stat_hit.match_assist = True
                # For game-ending stat hits
                last_hit = [hit for hit in proto_game.game_stats.hits if hit.player_id.id == curr_player.id.id][-1]
                if stat_type == 'match_goals' and len(indices[name][stat_type]) != curr_player.goals:
                    last_hit.match_goal = True
                if stat_type == 'match_saves' and len(indices[name][stat_type]) != curr_player.saves:
                    last_hit.match_save = True
                if stat_type == 'match_shots' and len(indices[name][stat_type]) != curr_player.shots:
                    last_hit.match_shot = True
                if stat_type == 'match_assists' and len(indices[name][stat_type]) != curr_player.assists:
                    last_hit.match_assist = True
   
        SaltieHit.get_saltie_hits_from_game(proto_game, hits, player_map, data_frame, kickoff_frames)
        logger.info("Analysed hits.")

        for curr_player in proto_game.players:
            hit_asst = len([hit for hit in proto_game.game_stats.hits if hit.player_id.id == curr_player.id.id and hit.match_assist])
            hit_goal = len([hit for hit in proto_game.game_stats.hits if hit.player_id.id == curr_player.id.id and hit.match_goal])
            hit_shot = len([hit for hit in proto_game.game_stats.hits if hit.player_id.id == curr_player.id.id and hit.match_shot])
            hit_save = len([hit for hit in proto_game.game_stats.hits if hit.player_id.id == curr_player.id.id and hit.match_save])
            try:
                assert curr_player.assists == hit_asst
            except:
                print("assists", curr_player.name, curr_player.assists, hit_asst, len(indices[curr_player.name]['match_assists']))
            try:
                assert curr_player.goals == hit_goal
            except:
                print("goals", curr_player.name, curr_player.goals, hit_goal, len(indices[curr_player.name]['match_goals']))
            try:
                assert curr_player.shots == hit_shot
            except:
                print("shots", curr_player.name, curr_player.shots, hit_shot, len(indices[curr_player.name]['match_shots']))
            try:
                assert curr_player.saves == hit_save
            except:
                print("saves", curr_player.name, curr_player.saves, hit_save, len(indices[curr_player.name]['match_saves']))

        # self.stats = get_stats(self)

    def calculate_ball_carries(self, game: Game, proto_game: game_pb2.Game, player_map: Dict[str, Player],
                               data_frame: pd.DataFrame):
        logger.info("Looking for carries.")
        carry_detection = CarryDetection()
        carry_data = carry_detection.filter_frames(data_frame)

        for player in player_map:
            carry_detection.create_carry_events(carry_data, player_map[player], proto_game, data_frame)
            # find now continuous data of longer than a second.
        logger.info("Found %s carries.", len(proto_game.game_stats.ball_carries))

    def create_bumps(self, game: Game, proto_game: game_pb2.Game, player_map: Dict[str, Player],
                     data_frame: pd.DataFrame):
        logger.info("Looking for bumps.")
        bumpAnalysis = BumpAnalysis(game=game, proto_game=proto_game)
        bumpAnalysis.get_bumps_from_game(data_frame)
        logger.info("Found %s bumps.", len(proto_game.game_stats.bumps))

    def create_dropshot_events(self, game: Game, proto_game: game_pb2.Game, player_map: Dict[str, Player]):
        create_dropshot_damage_events(game, proto_game)
        create_dropshot_ball_events(game, proto_game, player_map)

    def create_boostpad_events(self, proto_game: game_pb2.Game, data_frame: pd.DataFrame):
        PickupAnalysis.add_pickups(proto_game, data_frame)
