from typing import Dict

import numpy as np
import pandas as pd

from carball.generated.api import game_pb2
from carball.generated.api.player_pb2 import Player
from carball.json_parser.game import Game
from ....analysis.stats.stats import BaseStat

class GoalStats(BaseStat):
    def calculate_stat(self, proto_stat, game: Game, proto_game: game_pb2.Game, player_map: Dict[str, Player], data_frame: pd.DataFrame):
        team_names = self.get_team_names(proto_game)
        goals_sorted = sorted(proto_stat.goals, key=lambda x: x.frame_number)
        blue_goals = 0
        orange_goals = 0
        start_frame = 0
        assist_count = 0
        for goal in goals_sorted:
            frame_num = goal.frame_number
            scorer = player_map[goal.player_id.id]
            goal.is_orange = scorer.is_orange
            goal.team_name = team_names["orange"] if scorer.is_orange else team_names["blue"]
            
            is_go_ahead = (blue_goals == orange_goals)
            goal.is_go_ahead = is_go_ahead
            if not is_go_ahead:
                if scorer.is_orange:
                    goal.is_tying = (blue_goals - 1 == orange_goals)
                else:
                    goal.is_tying = (blue_goals == orange_goals - 1)
            else:
                goal.is_tying = False
            
            if scorer.is_orange:
                orange_goals += 1
            else:
                blue_goals += 1

            game_data = data_frame.loc[frame_num, ('game')]
            game_secs = game_data['seconds_remaining']
            goal.seconds_remaining = 0 if np.isnan(game_secs) else int(game_data["seconds_remaining"])
            if "is_overtime" in game_data.keys() and game_data["is_overtime"]:
                goal.seconds_remaining *= -1
            
            pos_data = tuple(data_frame.loc[frame_num, ('ball', ['pos_x', 'pos_y', 'pos_z'])])
            goal.ball_pos.pos_x = pos_data[0]
            goal.ball_pos.pos_y = pos_data[1]
            goal.ball_pos.pos_z = pos_data[2]
            if not scorer.is_orange:
                goal.ball_pos.pos_x *= -1 
            
            offset = 1
            while np.isnan(data_frame.loc[frame_num - offset, ('ball', 'vel_x')]):
                offset += 1
            vel_data = tuple(data_frame.loc[frame_num - offset, ('ball', ['vel_x', 'vel_y', 'vel_z'])] / 10)
            goal.ball_vel.pos_x = vel_data[0]
            goal.ball_vel.pos_y = vel_data[1]
            goal.ball_vel.pos_z = vel_data[2]
            
            start_sign = np.sign(goal.ball_pos.pos_y)
            curr_frame = goal.frame_number
            off_half_time = 0
            while np.sign(data_frame['ball']['pos_y'].at[curr_frame]) == start_sign:
                curr_frame -= 1
                off_half_time += data_frame['game', 'delta'].at[curr_frame]
            goal.time_in_off_half = round(off_half_time, 3)

            num_touches = 0
            team_touches = [hit for hit in proto_game.game_stats.hits if player_map[hit.player_id.id].is_orange == goal.is_orange\
                        and hit.frame_number <= goal.frame_number]
            if len(team_touches) == 0:
                goal.cons_team_touches = num_touches
                continue
            curr_touch = team_touches[-1]
            while player_map[curr_touch.player_id.id].is_orange == goal.is_orange:
                num_touches += 1
                prev_hit_frame = curr_touch.previous_hit_frame_number
                if prev_hit_frame == 0:
                    break
                curr_touch = [hit for hit in proto_game.game_stats.hits if hit.frame_number == prev_hit_frame][0]
            goal.cons_team_touches = num_touches

            try:
                ko_hit = [hit for hit in proto_game.game_stats.hits if hit.previous_hit_frame_number == 0 \
                    and hit.frame_number < goal.frame_number][-1]
                ko_frame = ko_hit.frame_number
            except:
                ko_frame = proto_game.game_stats.kickoffs[-1].end_frame_number
            goal.time_after_kickoff = round(data_frame['game', 'delta'].loc[ko_frame:goal.frame_number].sum(), 3)

            goal_hit = self.get_goal_hit(proto_game, goal)
            if goal_hit is not None:
                assist_hit = [hit for hit in proto_game.game_stats.hits if hit.frame_number < goal_hit.frame_number
                    and hit.frame_number > start_frame and hit.match_assist]
            
                if len(assist_hit) > 0:
                    goal.assister = player_map[assist_hit[0].player_id.id].name
                    assist_count += 1
                else:
                    goal.assister = ""
            
            start_frame = goal.frame_number
        if sum([player.assists for player in proto_game.players]) != assist_count:
            print("  Mismatched assists: ", proto_game.game_metadata.name)

    @staticmethod
    def get_team_names(pb_game):
        team_names = {}
        for team in pb_game.teams:
            if team.is_orange:
                team_names['orange'] = team.name
            else:
                team_names['blue'] = team.name
        return team_names

    @staticmethod
    def get_goal_hit(proto_game, goal):
        goal_hits = [hit for hit in proto_game.game_stats.hits if hit.match_goal]
        for i in range(len(goal_hits) - 1, -1, -1):
            if goal_hits[i].frame_number <= goal.frame_number:
                return goal_hits[i]