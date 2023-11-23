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
            
            goal_hit = self.get_goal_hit(proto_game, goal)
            if goal_hit.assisted:
                assister_id = self.get_assister_id(proto_game, goal_hit)
                assister = player_map[assister_id]
                goal.assister = assister.name
            else:
                goal.assister = ""

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
        goal_hits = [hit for hit in proto_game.game_stats.hits if hit.goal]
        for i in range(len(goal_hits) - 1, -1, -1):
            if goal_hits[i].frame_number < goal.frame_number:
                return goal_hits[i]
            
    @staticmethod
    def get_assister_id(proto_game, goal_hit):
        assist_hits = [hit for hit in proto_game.game_stats.hits if hit.assist]
        for i in range(len(assist_hits) - 1, -1, -1):
            if assist_hits[i].frame_number < goal_hit.frame_number:
                return assist_hits[i].player_id.id