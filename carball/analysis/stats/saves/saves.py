from typing import Dict

import math
import numpy as np
import pandas as pd

from carball.generated.api import game_pb2
from carball.generated.api.player_pb2 import Player
from carball.json_parser.game import Game
from ....analysis.stats.stats import BaseStat

class SaveStat(BaseStat):
    def calculate_stat(self, proto_stat, game: Game, proto_game: game_pb2.Game, player_map: Dict[str, Player], data_frame: pd.DataFrame):
        saves = [hit for hit in proto_game.game_stats.hits if hit.match_save]
        blue_goals, orange_goals = 0, 0
        goal_idx = 0
        num_goals = len(proto_game.game_metadata.goals)
        for save in saves:
            saver = player_map[save.player_id.id]
            while goal_idx < num_goals and proto_game.game_metadata.goals[goal_idx].frame_number < save.frame_number:
                curr_goal = proto_game.game_metadata.goals[goal_idx]
                if curr_goal.is_orange:
                    orange_goals += 1
                else:
                    blue_goals += 1
                goal_idx += 1
                
            try:
                shot = [hit for hit in proto_game.game_stats.hits if hit.match_shot and hit.frame_number < save.frame_number][-1]
                shooter_name = player_map[shot.player_id.id].name
            except:
                prev_opp_touch = [hit for hit in proto_game.game_stats.hits if hit.frame_number < save.frame_number and 
                    player_map[hit.player_id.id].is_orange != saver.is_orange][-1]
                shooter_name = player_map[prev_opp_touch.player_id.id].name
            proto_stat.saves.add(
                frame_number = save.frame_number,
                seconds_remaining = save.seconds_remaining,
                saver = saver.name,
                shooter = shooter_name,
                is_orange = saver.is_orange,
                blue_score = blue_goals,
                orange_score = orange_goals
            )