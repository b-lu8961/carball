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
from carball.generated.api.stats.events_pb2 import Hit
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
                player_id = hit.player_id,
                collision_distance = hit.collision_distance,
                ball_data = hit.ball_data,
                goal_number = hit.goal_number,
                is_kickoff = hit.is_kickoff, 
                match_assist = hit.match_assist,
                match_goal = hit.match_goal,
                match_save = hit.match_save,
                match_shot = hit.match_shot,
                seconds_remaining = hit.seconds_remaining
            )
            if i == 0 and insert_frame < hit.frame_number:
                if insert_frame in collision_distances[curr_player.is_orange][curr_player.name].index:
                    col_dist = collision_distances[curr_player.is_orange][curr_player.name].loc[insert_frame]
                else:
                    try:
                        col_dist = collision_distances[curr_player.is_orange][curr_player.name].loc[insert_frame - 1]
                    except KeyError:
                        col_dist = collision_distances[curr_player.is_orange][curr_player.name].loc[insert_frame + 1]
                new_hit = proto_game.game_stats.hits.add(
                    frame_number = insert_frame,
                    player_id = curr_player.id,
                    collision_distance = col_dist,
                    goal_number = hit.goal_number,
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
                hits[hit.frame_number] = old_hit
            elif hit.frame_number < insert_frame and (i + 1 == len(hits_copy) or hits_copy[i + 1].frame_number >= insert_frame):
                if (i + 1) < len(hits_copy) and hits_copy[i + 1].frame_number == insert_frame:
                    insert_frame += 1

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

                hits[hit.frame_number] = old_hit
                hits[insert_frame] = new_hit
            else:
                # Move on to next hit
                pass

        return new_hit
    
    def insert_hit_v2(self, proto_game, data_frame, collision_distances, curr_player, old_hit=None, point_idx=None):
        if old_hit is None: 
            if len(collision_distances.index) == 0 or np.isnan(collision_distances.idxmin()):
                insert_frame = point_idx - 15
            else:
                insert_frame = collision_distances.idxmin()
        else: 
            insert_frame = old_hit.frame_number - 1

        goal_num = data_frame['game']['goal_number'].at[insert_frame + 1]
        new_hit = Hit(
            frame_number = insert_frame,
            goal_number = 0 if np.isnan(goal_num) else int(goal_num),
            player_id = curr_player.id,
            collision_distance = collision_distances.min() if old_hit is None else collision_distances.at[old_hit.frame_number],
            is_kickoff = False if old_hit is None else old_hit.is_kickoff
        )
        new_hit.ball_data.pos_x = data_frame['ball']['pos_x'].at[insert_frame]
        new_hit.ball_data.pos_y = data_frame['ball']['pos_y'].at[insert_frame]
        new_hit.ball_data.pos_z = data_frame['ball']['pos_z'].at[insert_frame]
        game_info = data_frame.loc[insert_frame, 'game']
        game_secs = game_info['seconds_remaining']
        if "is_overtime" in game_info.keys() and game_info['is_overtime']:
            new_hit.seconds_remaining = -1 if np.isnan(game_secs) else -1 * int(game_secs)
        else:
            new_hit.seconds_remaining = 0 if np.isnan(game_secs) else int(game_info['seconds_remaining'])

        if old_hit is None:
            old_hits = [hit for hit in proto_game.game_stats.hits if hit.frame_number > insert_frame]
            if len(old_hits) == 0:
                old_idx = len(proto_game.game_stats.hits)
            else:
                old_idx = proto_game.game_stats.hits.index(old_hits[0])
                old_hits[0].is_kickoff = False
        else:
            old_idx = proto_game.game_stats.hits.index(old_hit)
            old_hit.is_kickoff = False

        #print("v2", new_hit.frame_number)
        if np.isnan(new_hit.collision_distance):
            pl_x, pl_y, pl_z = data_frame[curr_player.name]['pos_x'].at[insert_frame], data_frame[curr_player.name]['pos_y'].at[insert_frame], data_frame[curr_player.name]['pos_z'].at[insert_frame]
            b_x, b_y, b_z = new_hit.ball_data.pos_x, new_hit.ball_data.pos_y, new_hit.ball_data.pos_z
            dist = np.sqrt((b_x - pl_x)**2 + (b_y - pl_y)**2 + (b_z - pl_z)**2)
            new_hit.collision_distance = dist - 20
        proto_game.game_stats.hits.insert(old_idx, new_hit)
        return new_hit

    def create_hit_events(self, game: Game, proto_game: game_pb2.Game, player_map: Dict[str, Player],
                          data_frame: pd.DataFrame, kickoff_frames: pd.DataFrame, first_touch_frames: pd.Series):
        """
        Creates all of the events for hits
        """
        logger.info("Looking for hits.")
        hits, collision_distances = BaseHit.get_hits_from_game(game, proto_game, self.id_creator, data_frame, first_touch_frames)
        logger.info("Found %s hits." % len(hits))

        # Add missing hits for +2 score
        for player in proto_game.players:
            hit_idx = data_frame[player.name][data_frame[player.name]['match_score'].diff() == 2].index
            ret_hit = [hit.frame_number for hit in proto_game.game_stats.hits if hit.player_id.id == player.id.id]
            for idx in hit_idx:
                nums = [num for num in ret_hit if num >= (idx - 30) and num <= idx]
                if len(nums) == 0:
                    #print(idx, player.name, data_frame['game']['seconds_remaining'].at[idx])
                    close_hits = [hit for hit in proto_game.game_stats.hits if hit.frame_number >= (idx - 30) and hit.frame_number <= idx 
                        and hit.player_id.id != player.id.id]
                    col_dists = collision_distances[(player.is_orange, player.name)].loc[(idx - 30):idx]
                    if len(close_hits) == 0:
                        # New hit
                        self.insert_hit_v2(proto_game, data_frame, col_dists, player, point_idx=idx)
                    else:
                        fifty_hit = close_hits[-1]
                        hit_color = data_frame['ball']['hit_team_no'].at[fifty_hit.frame_number]
                        if hit_color == player.is_orange:
                            # Fifty hit misattributed
                            fifty_hit.player_id.id = player.id.id
                        else:
                            # Insert fifty hit before current one
                            self.insert_hit_v2(proto_game, data_frame, col_dists, player, old_hit=fifty_hit)

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
                last_team_hit_list = [hit for hit in proto_game.game_stats.hits if 
                    (hit.frame_number <= idx) and (hit.player_id.id in team_player_ids)]
                last_team_hit = None if len(last_team_hit_list) == 0 else last_team_hit_list[-1]
                
                if curr_player_hit is None and last_team_hit is None:
                    recent_hit = [hit for hit in proto_game.game_stats.hits if hit.frame_number <= idx][-1]
                    new_hit_frame = recent_hit.frame_number - 1 if idx == recent_hit.frame_number else recent_hit.frame_number + 1
                    #print("insert 0", new_hit_frame)
                    self.insert_hit(proto_game, data_frame, hits, new_hit_frame, curr_player, collision_distances)
                    continue

                if curr_player_hit is None or ((last_team_hit.player_id.id != curr_player.id.id) and \
                        (last_team_hit.frame_number - curr_player_hit.frame_number) >= 75):
                    # Hit was misattributed; need to correct
                    last_team_frame = last_team_hit.frame_number
                    if last_team_hit.frame_number not in collision_distances.index:
                        if last_team_frame - 1 in collision_distances.index:
                            last_team_frame -= 1
                        else:
                            last_team_frame += 1
                    try:
                        curr_player_dist = collision_distances[curr_player.is_orange][curr_player.name].loc[last_team_frame]
                    except KeyError:
                        pl_x, pl_y, pl_z = data_frame[curr_player.name]['pos_x'].at[last_team_frame], data_frame[curr_player.name]['pos_y'].at[last_team_frame], data_frame[curr_player.name]['pos_z'].at[last_team_frame]
                        b_x, b_y, b_z = data_frame['ball']['pos_x'].at[last_team_frame], data_frame['ball']['pos_y'].at[last_team_frame], data_frame['ball']['pos_z'].at[last_team_frame]
                        curr_player_dist = np.sqrt((b_x - pl_x)**2 + (b_y - pl_y)**2 + (b_z - pl_z)**2)
                    if curr_player_dist > 400:
                        # curr player had 50-50 with opponent, hit needs to be added
                        recent_hit = [hit for hit in proto_game.game_stats.hits if hit.frame_number <= idx][-1]
                        # Insert new hit after recent_hit
                        new_hit_frame = recent_hit.frame_number - 1 if idx == recent_hit.frame_number else recent_hit.frame_number + 1
                        if player_map[recent_hit.player_id.id].is_orange != curr_player.is_orange:
                            #print("insert 1", new_hit_frame)
                            self.insert_hit(proto_game, data_frame, hits, new_hit_frame, curr_player, collision_distances)
                    else:
                        # Hit by teammate actually belongs to curr player
                        #print("switch")
                        last_team_hit.player_id.id = curr_player.id.id
                        last_team_hit.collision_distance = collision_distances[curr_player.is_orange][curr_player.name].loc[last_team_frame]


        # Assign stats separately due to hit corrections
        for name in indices.keys():
            curr_player = [player for player in proto_game.players if player.name == name][0]
            for stat_type in sb_cols:
                if len(indices[name][stat_type]) == 0:
                    continue
                
                for stat_idx in indices[name][stat_type]:
                    goal_frames = [goal.frame_number for goal in proto_game.game_metadata.goals if goal.frame_number < stat_idx]
                    if len(goal_frames) > 1:
                        start_frame = goal_frames[-2]
                    else:
                        start_frame = 0

                    hit_list = [hit for hit in proto_game.game_stats.hits if hit.frame_number > start_frame and
                        hit.frame_number <= stat_idx and hit.player_id.id == curr_player.id.id]
                    if len(hit_list) != 0:
                        stat_hit = hit_list[-1]
                    else:
                        min_frame = collision_distances[curr_player.is_orange][curr_player.name].loc[start_frame:stat_idx].idxmin()
                        while len([hit for hit in proto_game.game_stats.hits if hit.frame_number == min_frame]) != 0:
                            min_frame -= 1
                        #print("insert 2", min_frame)
                        stat_hit = self.insert_hit(proto_game, data_frame, hits, min_frame, curr_player, collision_distances)
                        
                    if stat_type == 'match_goals':
                        if stat_hit.match_goal:
                            recent_hit = [hit for hit in proto_game.game_stats.hits if 
                                hit.frame_number <= stat_idx][-1]
                            #print("insert 3", recent_hit.frame_number + 1)
                            stat_hit = self.insert_hit(proto_game, data_frame, hits, recent_hit.frame_number + 1, curr_player, collision_distances)
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
   
        # Delete team hits after a goal hit
        goal_hits = [hit for hit in proto_game.game_stats.hits if hit.match_goal]
        for g_hit in goal_hits:
            goal_color = player_map[g_hit.player_id.id].is_orange
            curr_idx = proto_game.game_stats.hits.index(g_hit)
            goal_df = data_frame['ball'].loc[g_hit.frame_number:]
            stop_row = goal_df[np.isnan(goal_df['vel_x'])].head(1)
            if len(stop_row.index) == 0:
                continue
            else:
                stop_idx = stop_row.index[0]
            while (curr_idx + 1 < len(proto_game.game_stats.hits)) and \
                    (proto_game.game_stats.hits[curr_idx + 1].frame_number <= stop_idx):
                curr_idx += 1
                curr_hit = proto_game.game_stats.hits[curr_idx]
                if not curr_hit.match_goal:
                    hit_color = player_map[curr_hit.player_id.id].is_orange
                    if hit_color == goal_color:
                        print("  delete", g_hit.frame_number, curr_hit.frame_number)
                        if curr_hit.match_assist or curr_hit.match_shot:
                            #print(player_map[curr_hit.player_id.id])
                            prev_player_hit = [hit for hit in proto_game.game_stats.hits if hit.player_id.id == curr_hit.player_id.id 
                                and hit.frame_number < g_hit.frame_number][-1]
                            if curr_hit.match_assist:
                                prev_player_hit.match_assist = True
                            if curr_hit.match_shot:
                                prev_player_hit.match_shot = True
                        proto_game.game_stats.hits.remove(curr_hit)
                        curr_idx -= 1
                
        hits_dict = {hit.frame_number: hit for hit in proto_game.game_stats.hits}
        SaltieHit.get_saltie_hits_from_game(proto_game, hits_dict, player_map, data_frame, kickoff_frames)
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
