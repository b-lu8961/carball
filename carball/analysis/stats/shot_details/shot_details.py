from typing import Dict

import math
import numpy as np
import pandas as pd

from carball.generated.api import game_pb2
from carball.generated.api.player_pb2 import Player
from carball.json_parser.game import Game
from ....analysis.stats.stats import BaseStat
from ....analysis.simulator.ball_simulator import BallSimulator
from ....analysis.constants.field_constants import BALL_SIZE
from ....analysis.simulator.map_constants import GOAL_X, GOAL_Z, MAP_Y

class ShotDetailStats(BaseStat):

    def calculate_stat(self, proto_stat, game: Game, proto_game: game_pb2.Game, player_map: Dict[str, Player], data_frame: pd.DataFrame):
        shots = [hit for hit in proto_game.game_stats.hits if hit.match_shot or hit.match_goal]
        for shot in shots:
            idx_list = [idx for idx in data_frame.index if idx <= shot.frame_number]
            if len(idx_list) == 0:
                print("shot data frame error")
                continue
            
            offset = 0
            while (shot.frame_number - offset) not in data_frame.index:
                offset += 1

            shot_is_orange = player_map[shot.player_id.id].is_orange
            shot_data = proto_stat.shot_details.add(
                distance = ShotDetailStats.get_dist_to_goal(shot.ball_data, shot_is_orange),
                angle = ShotDetailStats.get_angle(shot, shot_is_orange),
                z_angle = ShotDetailStats.get_z_angle(shot, shot_is_orange),
                goalward_speed = ShotDetailStats.get_goalward_speed(data_frame, shot, player_map[shot.player_id.id], offset),
                ball_speed = ShotDetailStats.get_ball_speed(shot),
                prev_touch_type = ShotDetailStats.get_prev_touch_type(proto_game, shot, player_map),
                is_goal = shot.match_goal,
                frame_number = shot.frame_number,
                is_orange = shot_is_orange,
                seconds_remaining = shot.seconds_remaining,
                previous_hit_frame_number = shot.previous_hit_frame_number,
                shooter_name = player_map[shot.player_id.id].name
            )
            ball_frame = data_frame["ball"].loc[shot.frame_number - offset]
            shot_data.ball_pos.pos_x = ball_frame["pos_x"]
            shot_data.ball_pos.pos_y = ball_frame["pos_y"]
            shot_data.ball_pos.pos_z = ball_frame["pos_z"]
            shot_data.ball_vel.pos_x = ball_frame["vel_x"]
            shot_data.ball_vel.pos_y = ball_frame["vel_y"]
            shot_data.ball_vel.pos_z = ball_frame["vel_z"]

            for player in proto_game.players:
                player_frame = data_frame[player.name].loc[shot.frame_number - offset]
                if player.is_orange == shot_is_orange:
                    if player.id.id == shot.player_id.id:
                        ShotDetailStats.add_shooter(shot_data, player_frame)
                    else:
                        ShotDetailStats.add_teammate(shot_data, player_frame)
                else:
                    ShotDetailStats.add_defender(shot_data, player_frame)

            goalside, avg_def, min_def = ShotDetailStats.get_defender_metrics(proto_game, data_frame, shot, player_map, offset)
            shot_data.goalside_defs = goalside
            shot_data.avg_def_goal_dist = avg_def
            shot_data.min_def_ball_dist = min_def

            ball_sim = BallSimulator(data_frame["ball"].loc[shot.frame_number - offset], shot_is_orange)
            on_target = ball_sim.get_is_shot(get_sim_data=True)
            if not on_target and shot.match_goal:
                shot_data.is_on_target = True
                curr_frame = shot.frame_number
                while (curr_frame + 1) in data_frame.index and not np.isnan(data_frame["ball"]["vel_x"].loc[curr_frame + 1]):
                    curr_frame += 1
                shot_data.cross_pos.pos_x = data_frame["ball"]["pos_x"].loc[curr_frame - offset]
                shot_data.cross_pos.pos_y = data_frame["ball"]["pos_y"].loc[curr_frame - offset]
                shot_data.cross_pos.pos_z = data_frame["ball"]["pos_z"].loc[curr_frame - offset]
                min_travel_dist = np.sqrt((shot_data.cross_pos.pos_x - ball_frame["pos_x"])**2 + (shot_data.cross_pos.pos_y - ball_frame["pos_y"])**2 + (shot_data.cross_pos.pos_z - ball_frame["pos_z"])**2)
                travel_time = np.sum(data_frame["game"]["delta"].loc[shot.frame_number - offset : curr_frame - offset])
                shot_data.adj_vel = round(min_travel_dist / travel_time, 3)
            elif on_target:
                shot_data.is_on_target = True
                pos = ball_sim.sim_data[["t", "x", "y", "z"]].tail(1).values
                shot_data.cross_pos.pos_x = pos[0][1]
                shot_data.cross_pos.pos_y = pos[0][2]
                shot_data.cross_pos.pos_z = pos[0][3]
                min_travel_dist = np.sqrt((pos[0][1] - ball_frame["pos_x"])**2 + (pos[0][2] - ball_frame["pos_y"])**2 + (pos[0][3] - ball_frame["pos_z"])**2)
                shot_data.adj_vel = round(min_travel_dist / pos[0][0], 3)
            else:
                continue

    @staticmethod
    def get_shot_features(pb, shot_data):
        curr_shot = []
        curr_shot.append(round(shot_data.distance, 3))
        curr_shot.append(round(shot_data.angle, 3))
        curr_shot.append(round(shot_data.z_angle, 3))
        curr_shot.append(round(shot_data.goalward_speed, 3))
        curr_shot.append(round(shot_data.ball_speed, 3))

        curr_shot.append(shot_data.goalside_defs)
        #curr_shot.append(round(shot_data.avg_def_goal_dist, 3))
        #curr_shot.append(round(shot_data.min_def_ball_dist, 3))
        #xy, yz, both = get_clarity(shot_data)
        #curr_shot.append(xy)
        #curr_shot.append(yz)
        #curr_shot.append(both)
        behind, chal, to_net, in_net, rot = ShotDetailStats.get_def_positioning(shot_data)
        # if (behind + chal + to_net + in_net + rot) > 3:
        #     print(chal, to_net, in_net, rot)
        #     print(pb.game_metadata.name, shot_data.frame_number)
        curr_shot.append(behind)
        curr_shot.append(chal)
        curr_shot.append(to_net)
        curr_shot.append(in_net)
        curr_shot.append(rot)

        #prev_type = shot_data.prev_touch_type
        #if prev_type == 0:
        #    print(game.game_metadata.name, shot_data.is_goal)
        curr_shot.append(int(shot_data.prev_touch_type))
        frames_since = shot_data.frame_number - shot_data.previous_hit_frame_number
        if shot_data.previous_hit_frame_number == 0:
            frames_since = 30 * 3
        curr_shot.append(frames_since)
        
        recent_demos = 0
        start_cutoff = shot_data.frame_number - (30 * 3)
        for demo in pb.game_metadata.demos:
            victim = [player for player in pb.players if player.id.id == demo.victim_id.id][0]
            if victim.is_orange != shot_data.is_orange and \
                    start_cutoff < demo.frame_number and demo.frame_number < shot_data.frame_number:
                recent_demos += 1
        curr_shot.append(recent_demos)
        
        curr_shot.append(shot_data.shooter.boost)
        avg_def_boost = sum([d.boost for d in shot_data.defenders]) / len(shot_data.defenders)
        curr_shot.append(avg_def_boost)
        
        curr_shot.append(int(shot_data.is_goal))
        curr_shot.append(shot_data.frame_number)
        curr_shot.append(shot_data.is_orange)
        
        return curr_shot

    @staticmethod
    def get_clarity(shot):
        ball_x, ball_y, ball_z = shot.ball_pos.pos_x, shot.ball_pos.pos_y, shot.ball_pos.pos_z
        ball_x1, ball_x2 = ball_x - BALL_SIZE, ball_x + BALL_SIZE
        ball_z1, ball_z2 = ball_z - BALL_SIZE, ball_z + BALL_SIZE

        goal_x1, goal_x2 = -GOAL_X / 2, GOAL_X / 2
        goal_y = -MAP_Y / 2 if shot.is_orange else MAP_Y / 2
        slope_xy1 = (goal_y - ball_y) / (goal_x1 - ball_x1)
        int_xy1 = (-goal_x1 * slope_xy1) + goal_y

        slope_xy2 = (goal_y - ball_y) / (goal_x2 - ball_x2)
        int_xy2 = (-goal_x2 * slope_xy2) + goal_y

        goal_z1, goal_z2 = 0, GOAL_Z
        slope_zy1 = (goal_y - ball_y) / (goal_z1 - ball_z1)
        int_zy1 = (-goal_z1 * slope_zy1) + goal_y

        slope_zy2 = (goal_y - ball_y) / (goal_z2 - ball_z2)
        int_zy2 = (-goal_z2 * slope_zy2) + goal_y

        xy, yz, both = 0, 0, 0
        for i in range(len(shot.defenders)):
            opp = shot.defenders[i]
            pl_x, pl_y, pl_z = opp.pos.pos_x, opp.pos.pos_y, opp.pos.pos_z
            is_goalside = False
            xy_check = False
            yz_check = False

            if shot.is_orange and pl_y < (ball_y):
                is_goalside = True
            if not shot.is_orange and pl_y > (ball_y):
                is_goalside = True

            x_val1 = (pl_y - int_xy1) / slope_xy1
            x_val2 = (pl_y - int_xy1) / slope_xy2
            min_x, max_x = min(x_val1, x_val2), max(x_val1, x_val2)
            if is_goalside and min_x < pl_x and pl_x < max_x:
                xy += 1
                xy_check = True

            z_val1 = (pl_y - int_zy1) / slope_zy1
            z_val2 = (pl_y - int_zy2) / slope_zy2
            min_z, max_z = min(z_val1, z_val2), max(z_val1, z_val2)
            if is_goalside and min_z < pl_z and pl_z < max_x:
                yz += 1
                yz_check = True
            if xy_check and yz_check:
                both += 1
        return xy, yz, both
    
    @staticmethod
    def is_behind_ball(ball_pos, pl_pos, ball_dist, is_orange):
        if ball_dist > 600:
            return False
        if (ball_pos.pos_x - BALL_SIZE) < pl_pos.pos_x and pl_pos.pos_x < (ball_pos.pos_x + BALL_SIZE):
            if (ball_pos.pos_z - BALL_SIZE) < pl_pos.pos_z and pl_pos.pos_z < (ball_pos.pos_z + BALL_SIZE):
                if is_orange and pl_pos.pos_y < ball_pos.pos_y:
                    return True
                if not is_orange and pl_pos.pos_y > ball_pos.pos_y:
                    return True
        else:
            return False

    @staticmethod
    def get_def_positioning(shot):
        ball_x, ball_y, ball_z = shot.ball_pos.pos_x, shot.ball_pos.pos_y, shot.ball_pos.pos_z
        behind, chal, to_net, in_net, rot = 0, 0, 0, 0, 0
        for i in range(len(shot.defenders)):
            is_goalside = False
            pl = shot.defenders[i]
            if shot.is_orange and pl.pos.pos_y < (ball_y):
                is_goalside = True
            if not shot.is_orange and pl.pos.pos_y > (ball_y):
                is_goalside = True

            goal_x, goal_y, goal_z = 0, -MAP_Y / 2 if shot.is_orange else MAP_Y / 2, GOAL_Z / 2
            pl_vel = [pl.vel.pos_x, pl.vel.pos_y, pl.vel.pos_z]
            pl_spd = np.linalg.norm(pl_vel)
            to_ball = [ball_x - pl.pos.pos_x, ball_y - pl.pos.pos_y, ball_z - pl.pos.pos_z]
            to_goal = [goal_x - pl.pos.pos_x, goal_y - pl.pos.pos_y, goal_z - pl.pos.pos_z]
            ball_proj = np.dot(pl_vel, to_ball) / np.linalg.norm(to_ball)
            ball_pct = ball_proj / np.linalg.norm(pl_vel)
            goal_proj = np.dot(pl_vel, to_goal) / np.linalg.norm(to_goal)
            goal_pct = goal_proj / np.linalg.norm(pl_vel)

            goal_dist = ShotDetailStats.get_dist_to_goal(pl.pos, shot.is_orange)
            ball_dist = np.sqrt((ball_x - pl.pos.pos_x)**2 + (ball_y - pl.pos.pos_y)**2 + (ball_z - pl.pos.pos_z)**2)
            
            if not is_goalside and goal_pct > 0.5:
                rot += 1
            elif ShotDetailStats.is_behind_ball(shot.ball_pos, pl.pos, ball_dist, shot.is_orange):
                behind += 1
            elif is_goalside and ball_pct > 0.5 and ball_pct > goal_pct:
                chal += 1
            elif is_goalside and goal_pct > 0.5 and goal_pct > ball_pct:
                if ((abs(pl.pos.pos_y) > 4900 and goal_dist < 1100) or goal_dist < (GOAL_X / 2)) and pl_spd < 1000:
                    in_net += 1
                else:
                    to_net += 1
            else:
                continue
            
        return behind, chal, to_net, in_net, rot

    @staticmethod
    def add_shooter(shot_data, frame):
        shot_data.shooter.pos.pos_x = -1 if np.isnan(frame["pos_x"]) else frame["pos_x"]
        shot_data.shooter.pos.pos_y = -1 if np.isnan(frame["pos_y"]) else frame["pos_y"]
        shot_data.shooter.pos.pos_z = -1 if np.isnan(frame["pos_z"]) else frame["pos_z"]
        shot_data.shooter.vel.pos_x = -1 if np.isnan(frame["vel_x"]) else frame["vel_x"]
        shot_data.shooter.vel.pos_y = -1 if np.isnan(frame["vel_y"]) else frame["vel_y"]
        shot_data.shooter.vel.pos_z = -1 if np.isnan(frame["vel_z"]) else frame["vel_z"]
        shot_data.shooter.boost = 0 if np.isnan(frame["boost"]) else int(frame["boost"])
        shot_data.shooter.jump_active = 0 if np.isnan(frame["jump_active"]) or type(frame["jump_active"]) == bool else int(frame["jump_active"])
        shot_data.shooter.dodge_active = 0 if np.isnan(frame["dodge_active"]) or type(frame["dodge_active"]) == bool else int(frame["dodge_active"])
        shot_data.shooter.double_jump_active = 0 if np.isnan(frame["double_jump_active"]) or type(frame["double_jump_active"]) == bool else int(frame["double_jump_active"])

    @staticmethod
    def add_teammate(shot_data, frame):
        mate = shot_data.teammates.add(
            boost = 0 if np.isnan(frame["boost"]) else int(frame["boost"]),
            jump_active = 0 if np.isnan(frame["jump_active"]) or type(frame["jump_active"]) == bool else int(frame["jump_active"]),
            dodge_active = 0 if np.isnan(frame["dodge_active"]) or type(frame["dodge_active"]) == bool else int(frame["dodge_active"]),
            double_jump_active = 0 if np.isnan(frame["double_jump_active"]) or type(frame["double_jump_active"]) == bool else int(frame["double_jump_active"]),
        )
        mate.pos.pos_x = -1 if np.isnan(frame["pos_x"]) else frame["pos_x"]
        mate.pos.pos_y = -1 if np.isnan(frame["pos_y"]) else frame["pos_y"]
        mate.pos.pos_z = -1 if np.isnan(frame["pos_z"]) else frame["pos_z"]
        mate.vel.pos_x = -1 if np.isnan(frame["vel_x"]) else frame["vel_x"]
        mate.vel.pos_y = -1 if np.isnan(frame["vel_y"]) else frame["vel_y"]
        mate.vel.pos_z = -1 if np.isnan(frame["vel_z"]) else frame["vel_z"]

    @staticmethod
    def add_defender(shot_data, frame):
        opp = shot_data.defenders.add(
            boost = 0 if np.isnan(frame["boost"]) else int(frame["boost"]),
            jump_active = 0 if np.isnan(frame["jump_active"]) or type(frame["jump_active"]) == bool else int(frame["jump_active"]),
            dodge_active = 0 if np.isnan(frame["dodge_active"]) or type(frame["dodge_active"]) == bool else int(frame["dodge_active"]),
            double_jump_active = 0 if np.isnan(frame["double_jump_active"]) or type(frame["double_jump_active"]) == bool else int(frame["double_jump_active"]),
        )
        opp.pos.pos_x = -1 if np.isnan(frame["pos_x"]) else frame["pos_x"]
        opp.pos.pos_y = -1 if np.isnan(frame["pos_y"]) else frame["pos_y"]
        opp.pos.pos_z = -1 if np.isnan(frame["pos_z"]) else frame["pos_z"]
        opp.vel.pos_x = -1 if np.isnan(frame["vel_x"]) else frame["vel_x"]
        opp.vel.pos_y = -1 if np.isnan(frame["vel_y"]) else frame["vel_y"]
        opp.vel.pos_z = -1 if np.isnan(frame["vel_z"]) else frame["vel_z"]
    
    @staticmethod
    def get_dist_to_goal(pos_data, shot_is_orange):
        if pos_data.pos_x < (-GOAL_X / 2):
            goal_x = -GOAL_X / 2
        elif pos_data.pos_x > (GOAL_X / 2):
            goal_x = GOAL_X / 2
        else:
            goal_x = pos_data.pos_x
        goal_y = -MAP_Y / 2 if shot_is_orange else MAP_Y / 2
        goal_z = GOAL_Z if pos_data.pos_z > GOAL_Z else pos_data.pos_z
        return round(np.sqrt((pos_data.pos_x - goal_x)**2 + (pos_data.pos_y - goal_y)**2 + (pos_data.pos_z - goal_z)**2), 3)

    @staticmethod
    def get_angle(hit_data, shot_is_orange):
        post0 = np.array([-GOAL_X / 2, -MAP_Y / 2]) if shot_is_orange else np.array([-GOAL_X / 2, MAP_Y / 2])
        post1 = np.array([GOAL_X / 2, -MAP_Y / 2]) if shot_is_orange else np.array([GOAL_X / 2, MAP_Y / 2])
        ball = np.array([hit_data.ball_data.pos_x, hit_data.ball_data.pos_y])

        v0, v1 = post0 - ball, post1 - ball
        angle = math.atan2(np.linalg.det([v0, v1]), np.dot(v0, v1))
        return round(abs(np.degrees(angle)), 3)

    @staticmethod
    def get_z_angle(hit_data, shot_is_orange):
        ground = np.array([0, -MAP_Y / 2]) if shot_is_orange else np.array([0, MAP_Y / 2])
        crossbar = np.array([GOAL_Z, -MAP_Y / 2]) if shot_is_orange else np.array([GOAL_Z, MAP_Y / 2])
        ball = np.array([hit_data.ball_data.pos_z, hit_data.ball_data.pos_y])
        
        v0, v1 = ground - ball, crossbar - ball
        angle = math.atan2(np.linalg.det([v0, v1]), np.dot(v0, v1))
        return round(abs(np.degrees(angle)), 3)

    @staticmethod
    def get_goalward_speed(df, hit_data, player, offset):
        y_vel = df[player.name]["vel_y"].loc[hit_data.frame_number - offset]
        y_vel = -1 * y_vel if player.is_orange else y_vel
        return round(y_vel, 3)

    @staticmethod
    def get_ball_speed(hit_data):
        ball_x, ball_y, ball_z = hit_data.ball_data.pos_x, hit_data.ball_data.pos_y, hit_data.ball_data.pos_z
        return round(np.sqrt(ball_x**2 + ball_y**2 + ball_z**2), 3)

    @staticmethod
    def get_defender_metrics(pb, df, hit_data, player_map, offset):
        shot_is_orange = player_map[hit_data.player_id.id].is_orange
        opp_players = [player.name for player in pb.players if player.is_orange != shot_is_orange]
        player_count, total_dist, min_dist, defender_count = 0, 0, np.inf, 0
        #clarity = 1
        
        for player in opp_players:
            #is_goalside = False
            player_pos = df[[(player, "pos_x"), (player, "pos_y"), (player, "pos_z")]].loc[hit_data.frame_number - offset]
            if np.isnan(player_pos[player]).any():
                continue
                
            # avg def dist to goal
            defender_count += 1
            total_dist += ShotDetailStats.get_dist_to_goal(player_pos[player], shot_is_orange)
            
            # min def dist to ball
            pl_x, pl_y, pl_z = player_pos[player]["pos_x"], player_pos[player]["pos_y"], player_pos[player]["pos_z"]
            ball_x, ball_y, ball_z = hit_data.ball_data.pos_x, hit_data.ball_data.pos_y, hit_data.ball_data.pos_z
            dist = np.sqrt((ball_x - pl_x)**2 + (ball_y - pl_y)**2 + (ball_z - pl_z)**2)
            if dist < min_dist:
                min_dist = dist
            
            # goalside defenders
            if shot_is_orange and pl_y < (hit_data.ball_data.pos_y + BALL_SIZE):
                player_count += 1
                #is_goalside = True
            if not shot_is_orange and pl_y > (hit_data.ball_data.pos_y - BALL_SIZE):
                player_count += 1
                #is_goalside = True
                
        avg_dist = 10000 if  defender_count == 0 else round(total_dist / defender_count, 3)
        return player_count, avg_dist, round(min_dist, 3)

    @staticmethod
    def get_prev_touch_type(pb, hit_data, player_map):
        if hit_data.previous_hit_frame_number == 0:
            return 0
        else:
            prev_hit = [hit for hit in pb.game_stats.hits if hit.frame_number == hit_data.previous_hit_frame_number][0]
            if prev_hit.player_id.id == hit_data.player_id.id:
                # prev touch was self
                return 1
            elif player_map[prev_hit.player_id.id].is_orange == player_map[hit_data.player_id.id].is_orange:
                # prev touch was teammate
                return 2
            else:
                # prev touch was opponent
                return 3