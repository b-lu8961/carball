from carball.decompile_replays import decompile_replay
from carball.json_parser.game import Game
from carball.analysis.analysis_manager import AnalysisManager
from carball.analysis.utils.proto_manager import ProtobufManager

import itertools
import os
from PIL import Image, ImageFont

import viz.constants as constants


import matplotlib.pyplot as plt
import matplotlib.collections as mc
import matplotlib.markers as mmarkers


def names_equal(one: str, two: str):
    return one.lower().replace('.', '') == two.lower().replace('.', '')

def get_team_names(pb_game):
    team_names = {}
    for team in pb_game.teams:
        if team.is_orange:
            team_names['orange'] = team.name
        else:
            team_names['blue'] = team.name
    return team_names

def read_replay_data(proto_name: str):
    with open(proto_name, "rb") as proto_file:
        return ProtobufManager.read_proto_out_from_file(proto_file)

def write_replay_data(replay_name: str, write_df: bool = False):
    json_obj = decompile_replay(replay_name)
    game = Game()
    game.initialize(loaded_json=json_obj)

    # TODO: add folder tags
    manager = AnalysisManager(game)
    manager.create_analysis()

    proto_game = manager.get_protobuf_data()
    file_base = replay_name.removesuffix(".replay")
    with open(file_base + ".bin", "wb") as proto_file:
        manager.write_proto_out_to_file(proto_file)

    if write_df:
        with open(file_base + ".gz", "wb") as df_file:
            manager.write_pandas_out_to_file(df_file)

    return proto_game

def read_series_data(folder_path: str):
    game_list = []
    proto_list = [data_file for data_file in os.listdir(folder_path) if data_file.endswith(".bin")]
    for pb_file in proto_list:
        pb_game = read_replay_data(os.path.join(folder_path, pb_file))
        game_list.append(pb_game)
    return game_list

def write_series_data(folder_path: str, write_df: bool = False):
   # Aggregate games for all replays in a single folder
    game_list = []
    replay_list = [data_file for data_file in os.listdir(folder_path) if data_file.endswith(".replay")]
    for i in range(len(replay_list)):
        replay_name = replay_list[i]
        pb_game = write_replay_data(os.path.join(folder_path, replay_name), write_df)
        game_list.append(pb_game)
        print(pb_game.game_metadata.name)
    return game_list

def read_group_data(base_path: str):
    game_list = []
    folder_list = os.listdir(base_path)
    for name in folder_list:
        folder_path = os.path.join(base_path, name)
        if os.path.isdir(folder_path):
            folder_files = os.listdir(folder_path)
            if len(folder_files) == 0:
                continue
            elif folder_files[0].endswith(".bin") or folder_files[0].endswith(".gz") or folder_files[0].endswith(".replay"):
                pb_games = read_series_data(folder_path)
                game_list.append(pb_games)
            else:
                next_games = read_group_data(folder_path)
                game_list.append(next_games)

    return itertools.chain.from_iterable(game_list)

def write_group_data(base_path: str, write_df: bool = False):
    # Aggregate games for all replays in all folders contained by [folder_path]
    game_list = []
    folder_list = os.listdir(base_path)
    for i in range(len(folder_list)):
        folder_path = os.path.join(base_path, folder_list[i])
        if os.path.isdir(folder_path):
            folder_files = os.listdir(folder_path)
            if len(folder_files) == 0:
                continue
            elif folder_files[0].endswith(".bin") or folder_files[0].endswith(".gz") or folder_files[0].endswith(".replay"):
                pb_games = write_series_data(folder_path, write_df)
                game_list.append(pb_games)
                print(folder_path)
            else:
                pb_games = write_group_data(folder_path, write_df) 
                game_list.append(pb_games)
                
    return itertools.chain.from_iterable(game_list)

def get_y(val, img_height):
    return img_height - val

def draw_team_logo(img, margin, file_name):
    with Image.open(os.path.join("viz", "images", "logos", file_name)) as logo:
        divisor = logo.width / 200
        logo_width, logo_height = round(logo.width / divisor), round(logo.height / divisor)
        logo_small = logo.resize((logo_width, logo_height))
        img.paste(logo_small, (margin, margin), mask = logo_small)
        return logo_width, logo_height
    
def draw_dotted_circle(draw, img_width, margin, color_one, color_two):
    segoe = ImageFont.truetype("segoeuil.ttf", 150)
    circle_length = draw.textlength("\u25cc", segoe)
    draw.text((img_width - circle_length - (2 * margin), 0), "\u25cc", fill=color_one, font=segoe)
    draw.text((img_width - (2 * margin), 13), "\u031a", fill=color_two, font=segoe)

def draw_goal_lines(draw, margin, height):
    draw.line([
        ((2 * margin), get_y(0 + margin, height)), 
        ((2 * margin), get_y(constants.GOAL_Z + margin, height)), 
        ((2 * margin) + constants.GOAL_X, get_y(constants.GOAL_Z + margin, height)), 
        ((2 * margin) + constants.GOAL_X, get_y(0 + margin, height))
    ], fill=(70,70,70), width=6, joint="curve")
    draw.line([(margin, get_y(0 + margin, height)), ((3 * margin) + constants.GOAL_X, get_y(0 + margin, height))], fill=(140,140,140), width=2)

def draw_field_lines(draw, margin, height):
    mid_x, mid_y = (constants.MAP_Y + (margin * 4)) / 2, (constants.MAP_X + (margin * 2)) / 2
    half_goal_y = constants.GOAL_X / (2 * constants.SCALE)
    box_width = constants.GOAL_Z / constants.SCALE
    field_left, field_right = 2 * margin, (2 * margin) + constants.MAP_Y
    field_bottom, field_top = margin, constants.MAP_X + margin

    draw.line([
        (field_left, get_y(mid_y + half_goal_y + 20, height)),
        (field_left + box_width, get_y(mid_y + half_goal_y + 20, height)),
        (field_left + box_width, get_y(mid_y - half_goal_y - 20, height)),
        (field_left, get_y(mid_y - half_goal_y - 20, height))
    ], fill=constants.TEAM_INFO["RL ESPORTS"]["c1"], width=4)
    draw.line([
        (field_right, get_y(mid_y + half_goal_y + 20, height)),
        (field_right - box_width, get_y(mid_y + half_goal_y + 20, height)),
        (field_right - box_width, get_y(mid_y - half_goal_y - 20, height)),
        (field_right, get_y(mid_y - half_goal_y - 20, height))
    ], fill=constants.TEAM_INFO["RL ESPORTS"]["c2"], width=4)
    draw.line([
        (field_left + (constants.MAP_Y / 2), get_y(field_bottom, height)), 
        (field_left + (constants.MAP_Y / 2), get_y(field_top, height))
    ], fill=(140,140,140), width=4)
    draw.ellipse([
        (mid_x - half_goal_y + 5, get_y(mid_y + half_goal_y - 5, height)),
        (mid_x + half_goal_y - 5, get_y(mid_y - half_goal_y + 5, height))
    ], outline=(140,140,140), width=4)
    draw.line([
        (field_left, get_y(constants.CORNER_SIDE + field_bottom, height)),
        (field_left, get_y(mid_y - half_goal_y, height)),
        (field_left - 20, get_y(mid_y - half_goal_y, height)), 
        (field_left - 20, get_y(mid_y + half_goal_y, height)), 
        (field_left, get_y(mid_y + half_goal_y, height)), 
        (field_left, get_y(field_top - constants.CORNER_SIDE, height)), 
        (field_left + constants.CORNER_SIDE, get_y(field_top, height)), 
        (field_right - constants.CORNER_SIDE, get_y(field_top, height)),
        (field_right, get_y(field_top - constants.CORNER_SIDE, height)),
        (field_right, get_y(mid_y + half_goal_y, height)),
        (field_right + 20, get_y(mid_y + half_goal_y, height)),
        (field_right + 20, get_y(mid_y - half_goal_y, height)),
        (field_right, get_y(mid_y - half_goal_y, height)),
        (field_right, get_y(constants.CORNER_SIDE + field_bottom, height)),
        (field_right - constants.CORNER_SIDE, get_y(field_bottom, height)),
        (field_left + constants.CORNER_SIDE, get_y(field_bottom, height)),
        (field_left, get_y(constants.CORNER_SIDE + field_bottom, height)),
    ], fill=(70,70,70), width=6, joint="curve")


def draw_height_legend(draw, text_bottom, margin, image_width, marker_size, font):
    goal_right = round(constants.MAP_Y) + (4 * margin)
    draw.line([(goal_right + (3 * margin), text_bottom + (3 * margin)), (image_width - (4.5 * margin), text_bottom + (3 * margin))], 
        fill=(140,140,140), width=4)
    
    circle_base_x = goal_right + (4.33 * margin)
    circle_base_y = text_bottom + (6 * margin)

    draw.ellipse([
            (circle_base_x - marker_size, circle_base_y - marker_size), 
            (circle_base_x + marker_size, circle_base_y + marker_size)], 
        outline=(140,140,140), width=4)
    draw.ellipse([
            (circle_base_x + (3 * margin) - (1.33 * marker_size), circle_base_y - (1.33 * marker_size)), 
            (circle_base_x + (3 * margin) + (1.33 * marker_size), circle_base_y + (1.33 * marker_size))], 
        outline=(140,140,140), width=4)
    draw.ellipse([
            (circle_base_x + (6 * margin) - (1.66 * marker_size), circle_base_y - (1.66 * marker_size)), 
            (circle_base_x + (6 * margin) + (1.66 * marker_size), circle_base_y + (1.66 * marker_size))], 
        outline=(140,140,140), width=4)
    draw.ellipse([
            (circle_base_x + (9 * margin) - (2 * marker_size), circle_base_y - (2 * marker_size)), 
            (circle_base_x + (9 * margin) + (2 * marker_size), circle_base_y + (2 * marker_size))], 
        outline=(140,140,140), width=4)
    
    draw.multiline_text((circle_base_x - (1.33 * margin), circle_base_y + (1.5 * margin)), 
        "On\nground", fill=(70,70,70), font=font, align="center")
    draw.multiline_text((circle_base_x + (7.66 * margin), circle_base_y + (1.5 * margin)), 
        "On\nceiling", fill=(70,70,70), font=font, align="center")

def draw_goal(ax, y_mult=1.5):
    lc = mc.LineCollection(constants.GOAL_BOUNDS, color='black', linewidths=2)
    ax.add_collection(lc)
    ax.set_xbound((constants.GOAL_X_LIMS[0] * 1.5), (constants.GOAL_X_LIMS[1] * 1.5))
    ax.set_ybound(0, (constants.GOAL_Z * y_mult))
    ax.set_aspect(1)
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)

def draw_field_xy(ax):
    lc = mc.LineCollection(constants.MAP_BOUNDS_TOP_HORIZ, color=constants.TOP_COLORS, linewidths=2)
    ax.add_collection(lc)
    ax.set_xbound((constants.MAP_Y_LIMS[0] * 1.3), (constants.MAP_Y_LIMS[1] * 1.3))
    ax.set_ybound(constants.MAP_X_LIMS[0] * 1.3, (constants.MAP_X_LIMS[1] * 1.3))
    ax.set_aspect(1)
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)
    
def draw_field_yz(ax):
    lc = mc.LineCollection(constants.MAP_BOUNDS_SIDE, color=constants.SIDE_COLORS, linewidths=2)
    ax.add_collection(lc)
    ax.set_xbound((constants.MAP_Y_LIMS[0] * 1.3), (constants.MAP_Y_LIMS[1] * 1.3))
    ax.set_ybound(0, (constants.MAP_Z * 1.5))
    ax.set_aspect(1)
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)

# https://github.com/matplotlib/matplotlib/issues/11155
def mscatter(x,y,ax=None, m=None, **kw):
    if not ax: ax=plt.gca()
    sc = ax.scatter(x,y,**kw)
    if (m is not None) and (len(m)==len(x)):
        paths = []
        for marker in m:
            if isinstance(marker, mmarkers.MarkerStyle):
                marker_obj = marker
            else:
                marker_obj = mmarkers.MarkerStyle(marker)
            path = marker_obj.get_path().transformed(
                        marker_obj.get_transform())
            paths.append(path)
        sc.set_paths(paths)
    return sc