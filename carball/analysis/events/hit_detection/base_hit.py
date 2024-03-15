import logging
import time
from typing import List, Dict, Callable

import numpy as np
import pandas as pd

from carball.analysis.constants.basic_math import position_columns, get_player_ball_displacements, \
    pos_rot_columns
from .hitbox.hitbox import Hitbox
from ....generated.api import game_pb2
from ....generated.api.stats.events_pb2 import Hit
from carball.json_parser.game import Game

logger = logging.getLogger(__name__)

MIN_DRIBBLE_FRAME_DISTANCE = 10


class BaseHit:

    @staticmethod
    def get_hits_from_game(game: Game, proto_game: game_pb2, id_creation: Callable,
                           data_frame: pd.DataFrame, first_touch_frames: pd.Series) -> Dict[int, Hit]:

        start_time = time.time()

        team_dict = {}

        for team in game.teams:
            team_dict[team.is_orange] = team

        #print([goal.frame_number for goal in proto_game.game_metadata.goals])
        hit_frame_numbers = BaseHit.get_hit_frame_numbers_by_ball_ang_vel(data_frame)
        #hit_frame_numbers += [num for num in range(7303, 7333)]
        #hit_frame_numbers.append(3290)
        #hit_frame_numbers.remove(668)
        if len(hit_frame_numbers) == 0:
            return {}

        # add kickoff hits
        for hit_frame in first_touch_frames:
            if hit_frame not in hit_frame_numbers:
                hit_frame_numbers.append(hit_frame)

        hit_frame_numbers.sort()

        hit_creation_time = time.time()
        logger.info('time to get get frame_numbers: %s', (hit_creation_time - start_time) * 1000)

        # Shift pos of ball slightly toward previous frame's location
        hit_frames = data_frame.loc[hit_frame_numbers, (slice(None), pos_rot_columns)]
        shift_idx = hit_frames.index - 1
        one = (4 * hit_frames['ball'][position_columns])
        two = data_frame['ball'][position_columns].loc[shift_idx].set_index(hit_frames.index)
        hit_frames.loc[hit_frames.index, ('ball', position_columns)] = ((one + two) / 5).values
        player_displacements = {player.name: get_player_ball_displacements(hit_frames, player.name)
                                for player in game.players}

        # player_distances = {player_name: get_distance_from_displacements(data_frame).rename(player_name)
        #                     for player_name, data_frame in player_displacements.items()}

        # player_distances_data_frame = pd.concat(player_distances, axis=1)

        rotation_matrices = {player.name: get_rotation_matrices(hit_frames, player.name) for player in game.players}

        local_displacements: Dict[str, pd.DataFrame] = {
            player.name: get_local_displacement(player_displacements[player.name],
                                                rotation_matrices[player.name])
            for player in game.players
        }

        player_hitboxes = get_player_hitboxes(game)
        collision_distances = [
            get_collision_distances(local_displacements[player.name], player_hitboxes[player.name]).rename(player.name)
            for player in game.players
        ]
        collision_distances_data_frame = pd.concat(collision_distances, axis=1)
        # TODO: Fix when no players detected. See issue #115

        player_name_to_team: Dict[str, int] = {player.name: int(player.team.is_orange) for player in game.players}
        columns = [(player_name_to_team[player_name], player_name)
                   for player_name in collision_distances_data_frame.columns]
        collision_distances_data_frame.columns = pd.MultiIndex.from_tuples(columns)

        collision_distances_data_frame['closest_player', 'name'] = None
        collision_distances_data_frame['closest_player', 'distance'] = None
        for hit_team_no in [0, 1]:
            try:
                collision_distances_for_team = collision_distances_data_frame[
                    hit_team_no].loc[data_frame.ball['hit_team_no'] == hit_team_no]

                close_collision_distances_for_team = collision_distances_for_team[
                    (collision_distances_for_team < 300).any(axis=1)
                ]

                collision_distances_data_frame['closest_player', 'distance'].fillna(
                    close_collision_distances_for_team.min(axis=1),
                    inplace=True
                )
                collision_distances_data_frame['closest_player', 'name'].fillna(
                    close_collision_distances_for_team.idxmin(axis=1),
                    inplace=True
                )
            except KeyError as e:
                if e.args[0] == hit_team_no:
                    logger.warning("Team %s did not hit the ball", str(hit_team_no))
                else:
                    raise e

        all_hits = {}
        norm_df = data_frame['ball'][['ang_vel_x', 'ang_vel_y', 'ang_vel_z']].diff().loc[hit_frame_numbers]
        norm_df['norm'] = np.linalg.norm(norm_df, axis=1)
        big_idx = norm_df[norm_df['norm'] > 10000].index
        for idx in big_idx:
            ball_pos = list(data_frame['ball'][['pos_x', 'pos_y', 'pos_z']].loc[idx])
            if ball_pos[0] < (-4096 + (1.5*92.75)) or ball_pos[0] > (4096 - (1.5*92.75)):
                continue
            if ball_pos[1] < (-5120 + (1.5*92.75)) or ball_pos[1] > (5120 - (1.5*92.75)):
                continue
            if ball_pos[2] < (0 + (1.5*92.75)) or ball_pos[2] > (2044 - (1.5*92.75)):
                continue
            hit_found = False
            closest_val = collision_distances_data_frame['closest_player']['name'].at[idx]
            
            if type(closest_val) != str and type(one) != str and type(two) != str and np.isnan(closest_val):
                for i in [idx - 2, idx - 1, idx + 1, idx + 2]:
                    if i in collision_distances_data_frame:
                        if type(collision_distances_data_frame['closest_player']['name']) == str:
                            hit_found = True
                            break
                if not hit_found:
                    for team_no in [0, 1]:
                        min_dist = (collision_distances_data_frame.loc[idx])[team_no].min()
                        if min_dist < 325:
                            close_name = (collision_distances_data_frame.loc[idx])[team_no].idxmin()
                            collision_distances_data_frame.loc[idx, ('closest_player', 'name')] = close_name
                            collision_distances_data_frame.loc[idx, ('closest_player', 'distance')] = min_dist
                            break
                    
        #print(collision_distances_data_frame.loc[3280:3300])
        #collision_distances_data_frame.loc[3292, ('closest_player', 'name')] = 'Lunar'
        #collision_distances_data_frame.loc[3292, ('closest_player', 'distance')] = 122.500
        #collision_distances_data_frame.loc[8500, ('closest_player', 'name')] = 'Rw9'
        #collision_distances_data_frame.loc[8500, ('closest_player', 'distance')] = 208.481

        hits_data = collision_distances_data_frame['closest_player'].dropna()
        if len(hits_data) > 1:
            hit_frames_to_keep = BaseHit.filter_out_duplicate_hits(hits_data)
            hits_data = hits_data.loc[hit_frames_to_keep]

        for row in hits_data.itertuples():
            frame_number, player_name, collision_distance = row.Index, row.name, row.distance
            while frame_number not in data_frame.index:
                frame_number -= 1
            hit = proto_game.game_stats.hits.add()
            hit.frame_number = frame_number
            game_info = data_frame.loc[frame_number, 'game']
            game_secs = game_info['seconds_remaining']
            if "is_overtime" in game_info.keys() and game_info['is_overtime']:
                hit.seconds_remaining = -1 if np.isnan(game_secs) else -1 * int(game_secs)
            else:
                hit.seconds_remaining = 0 if np.isnan(game_secs) else int(game_info['seconds_remaining'])
            goal_number = data_frame.at[frame_number, ('game', 'goal_number')]
            if not np.isnan(goal_number):
                hit.goal_number = int(goal_number)
            id_creation(hit.player_id, player_name)
            hit.collision_distance = collision_distance
            ball_position = data_frame.ball.loc[frame_number, position_columns]
            hit.ball_data.pos_x = float(ball_position['pos_x'])
            hit.ball_data.pos_y = float(ball_position['pos_y'])
            hit.ball_data.pos_z = float(ball_position['pos_z'])
            hit.is_kickoff = hit.frame_number in first_touch_frames
            all_hits[frame_number] = hit

        time_diff = time.time() - hit_creation_time
        logger.info('ball hit creation time: %s', time_diff * 1000)
        return all_hits, collision_distances_data_frame

    @staticmethod
    def filter_out_duplicate_hits(hits_data):
        """
        Filters out duplicate hits by finding the min distance in a set of frames by the same person
        That is less time than the MIN_DRIBBLE_FRAME_DISTANCE
        :param hits_data: Suspected hits
        :return: A reduced list that has removed duplicate hits.
        """
        hit_frames_to_keep = []
        shifted_hits = hits_data.shift(1)
        different_hits = list(hits_data[hits_data['name'] != shifted_hits['name']].index)
        if different_hits[-1] != int(hits_data.index[-1]):
            different_hits += [int(hits_data.index[-1])]

        if different_hits[0] != int(hits_data.index[0]):
            different_hits = [int(hits_data.index[0])] + different_hits

        for index in range(len(different_hits) - 1):
            start_row_num = different_hits[index]
            end_row_num = different_hits[index + 1]
            hit_rows = hits_data.loc[start_row_num:end_row_num]

            # ignore last frame in hit row for all but very last group
            if index + 1 < len(different_hits) - 1:
                hit_rows = hit_rows[:-1]

            if len(hit_rows) == 1:
                hit_frames_to_keep.append(start_row_num)
            else:
                min_distance = None
                min_frame_value = None
                starting_frame_number = 0
                last_added_frame_number = 0
                old_name = None
                # go through a single person hit
                for row in hit_rows.itertuples():
                    frame_number, player_name, collision_distance = row.Index, row.name, row.distance

                    if min_frame_value is None:
                        # Add first frame as hit, then init checks
                        hit_frames_to_keep.append(frame_number)
                        last_added_frame_number = frame_number
                        min_frame_value = frame_number
                        min_distance = collision_distance
                        starting_frame_number = frame_number
                        old_name = row.name
                        continue

                    if frame_number - starting_frame_number > MIN_DRIBBLE_FRAME_DISTANCE or row.name != old_name:
                        # Same person but a new hit reset distance checks
                        if last_added_frame_number == min_frame_value:
                            min_frame_value = frame_number
                        hit_frames_to_keep.append(min_frame_value)
                        last_added_frame_number = min_frame_value

                        # reset for next shot
                        min_frame_value = frame_number
                        min_distance = collision_distance
                        starting_frame_number = frame_number
                        old_name = row.name
                        continue

                    if collision_distance < min_distance:
                        min_frame_value = frame_number
                        min_distance = collision_distance

                if (last_added_frame_number != min_frame_value) \
                        and (min_frame_value - last_added_frame_number) > MIN_DRIBBLE_FRAME_DISTANCE:
                    hit_frames_to_keep.append(min_frame_value)

            start_row_num += 1
        return sorted(hit_frames_to_keep)

    @staticmethod
    def get_hit_frame_numbers_by_ball_ang_vel(data_frame: pd.DataFrame) -> List[int]:
        if 'ang_vel_x' not in data_frame.ball:
            return []
        ball_ang_vels_pre = data_frame.ball.loc[:, ['ang_vel_x', 'ang_vel_y', 'ang_vel_z']]
        ball_ang_vels = ball_ang_vels_pre.sort_index()
        diff_series = (np.abs(ball_ang_vels.diff()) > 50).any(axis=1)
        diff_list = diff_series.index[diff_series].tolist()
        ball_vel_y_pre = data_frame.ball.loc[:, 'vel_y']
        ball_vel_y = ball_vel_y = ball_vel_y_pre.sort_index()
        diff_2 = (np.abs(ball_vel_y.diff()) > 15000)
        diff_list_2 = diff_2.index[diff_2].tolist()
        zeros = (ball_ang_vels == 0).all(axis=1)
        zero_list = zeros.index[zeros].tolist()
        indices = [idx for idx in diff_list if idx not in zero_list]
        hit_team_nos = data_frame['ball']['hit_team_no']
        hit_changes = hit_team_nos[hit_team_nos.diff().abs() > 0].index.tolist()
        for idx in hit_changes:
            if idx not in indices:
                indices.append(idx)
        for idx in diff_list_2:
            if idx not in indices and abs(data_frame['ball']['vel_x'].at[idx]) > 0.01:
                indices.append(idx)
        return indices

    @staticmethod
    def get_ball_data(data_frame: pd.DataFrame, hit: Hit):
        return data_frame.ball.loc[hit.frame_number, :]


def get_rotation_matrices(data_frame: pd.DataFrame, player_name: str) -> pd.Series:
    pitch = data_frame[player_name, 'rot_x']
    yaw = data_frame[player_name, 'rot_y']
    roll = data_frame[player_name, 'rot_z']

    cos_roll = np.cos(roll).rename('cos_roll')
    sin_roll = np.sin(roll).rename('sin_roll')
    cos_pitch = np.cos(pitch).rename('cos_pitch')
    sin_pitch = np.sin(pitch).rename('sin_pitch')
    cos_yaw = np.cos(yaw).rename('cos_yaw')
    sin_yaw = np.sin(yaw).rename('sin_yaw')

    components: pd.DataFrame = pd.concat([cos_roll, sin_roll, cos_pitch, sin_pitch, cos_yaw, sin_yaw], axis=1)

    rotation_matrix = components.apply(get_rotation_matrix_from_row, axis=1, result_type='reduce')
    return rotation_matrix


def get_rotation_matrix_from_row(components: pd.Series) -> np.array:
    cos_roll, sin_roll, cos_pitch, sin_pitch, cos_yaw, sin_yaw = components.values
    rotation_matrix = np.array(
        [[cos_pitch * cos_yaw, cos_yaw * sin_pitch * sin_roll - cos_roll * sin_yaw,
          -cos_roll * cos_yaw * sin_pitch - sin_roll * sin_yaw],
         [cos_pitch * sin_yaw, sin_yaw * sin_pitch * sin_roll + cos_roll * cos_yaw,
          -cos_roll * sin_yaw * sin_pitch + sin_roll * cos_yaw],
         [sin_pitch, -cos_pitch * sin_roll, cos_pitch * cos_roll]])
    return rotation_matrix


def get_local_displacement(displacement: pd.DataFrame, rotation_matrices: pd.Series) -> pd.DataFrame:
    displacement_vectors = np.expand_dims(displacement[position_columns].values, 2)
    inverse_rotation_matrices: pd.Series = np.transpose(rotation_matrices)
    inverse_rotation_array = np.stack(inverse_rotation_matrices.values)
    local_displacement = np.matmul(inverse_rotation_array, displacement_vectors)
    displacement_data_frame = pd.DataFrame(data=np.squeeze(local_displacement, 2),
                                           index=displacement.index,
                                           columns=position_columns)
    return displacement_data_frame


def get_player_hitboxes(game: Game) -> Dict[str, Hitbox]:
    player_hitboxes = {}
    for player in game.players:
        car_item_id = player.loadout[0]['car'] if len(player.loadout) == 1 else player.loadout[player.is_orange]['car']
        player_hitboxes[player.name] = Hitbox(car_item_id)
    return player_hitboxes


def get_collision_distances(local_ball_displacement: pd.DataFrame, player_hitbox: Hitbox) -> pd.Series:
    def get_distance_function_for_player(displacement: pd.Series):
        return player_hitbox.get_collision_distance(displacement.values)

    collision_distances = local_ball_displacement.apply(get_distance_function_for_player, axis=1, result_type='reduce')
    return collision_distances
