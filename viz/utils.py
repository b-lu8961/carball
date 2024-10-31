from carball.decompile_replays import decompile_replay
from carball.json_parser.game import Game
from carball.analysis.analysis_manager import AnalysisManager
from carball.analysis.stats.shot_details.shot_details import ShotDetailStats
from carball.analysis.utils.proto_manager import ProtobufManager

import itertools
import joblib as jb
import math
import numpy as np
import os
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

import viz.constants as constants

### File utilities

def process_replay(replay_path: str):
    json_obj = decompile_replay(replay_path)
    game = Game()
    game.initialize(loaded_json=json_obj)

    # TODO: add folder tags
    manager = AnalysisManager(game)
    manager.create_analysis()

    proto_game = manager.get_protobuf_data()
    data_frame = manager.get_data_frame()
    return proto_game, data_frame

def read_replay_data(proto_name: str):
    with open(proto_name, "rb") as proto_file:
        return ProtobufManager.read_proto_out_from_file(proto_file)

def write_replay_data(replay_name: str, write_df: bool = False):
    json_obj = decompile_replay(replay_name)
    game = Game()
    game.initialize(loaded_json=json_obj)

    tags = replay_name.split('\\')[1:-1]
    file_name = replay_name.split('\\')[-1]
    game_parts = file_name.split(' vs ')[-1].split(' ')[1:]
    tags.append(game_parts[0])
    if len(game_parts) > 3 and 'Part' in game_parts[1]:
        tags.append('Part ' + game_parts[2][0])
    tag = '/'.join(tags)

    # TODO: add folder tags
    manager = AnalysisManager(game)
    manager.create_analysis(tag=tag)

    proto_game = manager.get_protobuf_data()
    file_base = replay_name.removesuffix(".replay")
    with open(file_base + ".bin", "wb") as proto_file:
        manager.write_proto_out_to_file(proto_file)

    if write_df:
        with open(file_base + ".gz", "wb") as df_file:
            manager.write_pandas_out_to_file(df_file)

    return proto_game

def write_protobuf_data(path: str, proto_game):
    with open(path, "wb") as proto_file:
        ProtobufManager.write_proto_out_to_file(proto_file, proto_game)

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

def iter_proto(base_path):
    for path in os.listdir(base_path):
        new_path = os.path.join(base_path, path)
        if os.path.isdir(new_path):
            iter_proto(new_path)
            if "Open" not in new_path:
                print(new_path)
        else:
            if ".bin" in new_path:
                pass
                # Add function here as necessary

def read_event_stats_file(path):
    event_data = {}
    with open(path, "r", encoding="utf-8") as data_file:
        for line in data_file.readlines():
            if line.startswith("Name"):
                continue
            pl_data = line.split(",")
            event_data[(pl_data[0], pl_data[2])] = {
                "region": pl_data[1],
                "LAN": pl_data[3],
                "gp": int(pl_data[4]),
                "secs": float(pl_data[5]),
                "sb": {
                    "score": float(pl_data[6]),
                    "goals": float(pl_data[7]),
                    "assists": float(pl_data[8]),
                    "saves": float(pl_data[9]),
                    "shots": float(pl_data[10]),
                    "shots_allowed": float(pl_data[11]),
                    "touches": float(pl_data[12]),
                    "passes": float(pl_data[13]),
                    "demos": float(pl_data[14]),
                    "steals": float(pl_data[16]),
                },
                "mvmt": {
                    "demos_taken": float(pl_data[15]),
                },
                "pssn": {
                    "turnovers": float(pl_data[17]),
                    "recoveries": float(pl_data[18]),
                    "blocks": float(pl_data[19]),
                    "prog_passes": float(pl_data[20]),
                    "prog_dribbles": float(pl_data[21]),
                    "rt_ratio": float(pl_data[22])
                }
            }
    return event_data

### Image utilities

def get_y(val, img_height):
    return img_height - val

def draw_team_logo(img, margin, file_name="default.png", pos=None):
    if pos is None:
        pos = (margin, margin)
    with Image.open(os.path.join("viz", "images", "logos", file_name)) as logo:
        divisor = max(logo.width / 200, logo.height / 250)
        logo_width, logo_height = round(logo.width / divisor), round(logo.height / divisor)
        logo_small = logo.resize((logo_width, logo_height))
        try:
            img.paste(logo_small, pos, mask = logo_small)
        except ValueError:
            img.paste(logo_small, pos)
        return logo_width, logo_height
    
def draw_dotted_circle(draw, img_width, margin, color_one, color_two):
    segoe = ImageFont.truetype("segoeuil.ttf", 150)
    circle_length = draw.textlength("\u25cc", segoe)
    draw.text((img_width - circle_length - (2 * margin), 0), "\u25cc", fill=color_one, font=segoe)
    draw.text((img_width - (2 * margin), 13), "\u031a", fill=color_two, font=segoe)

def draw_title_text(draw, logo_width, margin, config, font_one, font_two):
    draw.text((logo_width + 50 + margin, margin), config["t1"], fill=(0,0,0), font=font_one)
    draw.text((logo_width + 50 + margin, 80 + margin), config["t2"], fill=(70,70,70), font=font_two)
    draw.text((logo_width + 50 + margin, 130 + margin), config["t3"], fill=(70,70,70), font=font_two)

def draw_scatter_label(draw, name, pos_x, pos_y, radius, pos):
    if pos == "l":
        draw.text((pos_x - (1.5 * radius), pos_y), name, fill=(0,0,0), font=constants.BOUR_30, anchor='rm')
    elif pos == 'r':
        draw.text((pos_x + (1.5 * radius), pos_y), name, fill=(0,0,0), font=constants.BOUR_30, anchor='lm')
    elif pos == "u":
        draw.text((pos_x, pos_y - (1.25 * radius)), name, fill=(0,0,0), font=constants.BOUR_30, anchor='md')
    else:
        draw.text((pos_x, pos_y + (1 * radius)), name, fill=(0,0,0), font=constants.BOUR_30, anchor='ma')

# Draw polygon with linear gradient from point 1 to point 2 and ranging
# from color 1 to color 2 on given image
def linear_gradient(i, poly, p1, p2, c1, c2):

    # Draw initial polygon, alpha channel only, on an empty canvas of image size
    ii = Image.new('RGBA', i.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(ii)
    draw.polygon(poly, fill=(0, 0, 0, 255), outline=None)

    # Calculate angle between point 1 and 2
    p1 = np.array(p1)
    p2 = np.array(p2)
    angle = np.arctan2(p2[1] - p1[1], p2[0] - p1[0]) / np.pi * 180

    # Rotate and crop shape
    temp = ii.rotate(angle, expand=True)
    temp = temp.crop(temp.getbbox())
    wt, ht = temp.size

    # Create gradient from color 1 to 2 of appropriate size
    gradient = np.linspace(c1, c2, wt, True).astype(np.uint8)
    gradient = np.tile(gradient, [2 * ht, 1, 1])
    gradient = Image.fromarray(gradient)

    # Paste gradient on blank canvas of sufficient size
    temp = Image.new('RGBA', (max(i.size[0], gradient.size[0]),
                              max(i.size[1], gradient.size[1])), (0, 0, 0, 0))
    temp.paste(gradient)
    gradient = temp

    # Rotate and translate gradient appropriately
    x = np.sin(angle * np.pi / 180) * ht
    y = np.cos(angle * np.pi / 180) * ht
    gradient = gradient.rotate(-angle, center=(0, 0),
                               translate=(p1[0] + x, p1[1] - y))

    # Paste gradient on temporary image
    ii.paste(gradient.crop((0, 0, ii.size[0], ii.size[1])), mask=ii)

    # Paste temporary image on actual image
    i.paste(ii, mask=ii)

    return i

def linedashed(draw, fill, width, x0, x1, y0, y1, dashlen=15, ratio=3): 
    dx=x1 - x0 # delta x
    dy=y1 - y0 # delta y
    # check whether we can avoid sqrt
    if dy == 0:
        vlen = dx
    elif dx == 0: 
        vlen = dy
    else: 
        vlen = math.sqrt((dx * dx) + (dy * dy)) # length of line
    xa = dx / vlen # x add for 1px line length
    ya=dy / vlen # y add for 1px line length
    step = dashlen * ratio # step to the next dash
    a0 = 0
    while a0 < vlen:
        a1 = a0 + dashlen
        if a1 > vlen: 
            a1 = vlen
        draw.line((x0 + (xa * a0), y0 + (ya * a0), x0 + (xa * a1), y0 + (ya * a1)), fill=fill, width=width)
        a0 += step 

def draw_goal_lines(draw, margin, height, sections=False):
    ball_pad = 70
    goal_height = constants.GOAL_Z - (2 * ball_pad)
    goal_width = constants.GOAL_X - (2 * ball_pad)
    draw.line([
        ((2 * margin) + ball_pad, get_y(ball_pad, height)), 
        ((2 * margin) + ball_pad, get_y(constants.GOAL_Z - ball_pad, height)), 
        ((2 * margin) + constants.GOAL_X - ball_pad, get_y(constants.GOAL_Z - ball_pad, height)), 
        ((2 * margin) + constants.GOAL_X - ball_pad, get_y(ball_pad, height))
    ], fill=(70,70,70), width=6, joint="curve")
    draw.line([(margin, get_y(ball_pad, height)), ((3 * margin) + constants.GOAL_X, get_y(ball_pad, height))], fill=(140,140,140), width=2)

    if sections:
        linedashed(draw, (0,0,0), 3, 
            (2 * margin + ball_pad), (2 * margin) + constants.GOAL_X - ball_pad,
            get_y(ball_pad + (goal_height / 3), height), get_y(ball_pad + (goal_height / 3), height)
        )
        linedashed(draw, (0,0,0), 3, 
            (2 * margin + ball_pad), (2 * margin) + constants.GOAL_X - ball_pad,
            get_y(ball_pad + ((2 * goal_height) / 3), height), get_y(ball_pad + ((2 * goal_height) / 3), height)
        )
        linedashed(draw, (0,0,0), 3, 
            (2 * margin) + ball_pad + (goal_width / 3), (2 * margin) + ball_pad + (goal_width / 3),
            get_y(ball_pad + goal_height, height), get_y(ball_pad, height)
        )
        linedashed(draw, (0,0,0), 3, 
            (2 * margin) + ball_pad + ((2 * goal_width) / 3), (2 * margin) + ball_pad + ((2 * goal_width) / 3),
            get_y(ball_pad + goal_height, height), get_y(ball_pad, height)
        )

def draw_field_lines(draw, margin, height, sections=False, dash_color=(0,0,0)):
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
    ], fill=(140,140,140), width=4)
    draw.line([
        (field_right, get_y(mid_y + half_goal_y + 20, height)),
        (field_right - box_width, get_y(mid_y + half_goal_y + 20, height)),
        (field_right - box_width, get_y(mid_y - half_goal_y - 20, height)),
        (field_right, get_y(mid_y - half_goal_y - 20, height))
    ], fill=(140,140,140), width=4)
    draw.line([
        (field_left + (constants.MAP_Y / 2), get_y(field_bottom, height)), 
        (field_left + (constants.MAP_Y / 2), get_y(field_top, height))
    ], fill=(140,140,140), width=3)
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

    if sections:
        linedashed(draw, dash_color, 3,
            field_left + constants.MAP_Y_QUARTER, field_left + constants.MAP_Y_QUARTER, 
            get_y(field_top, height), get_y(field_bottom, height)
        )
        #linedashed(draw, (0,0,0), 3,
        #    field_left + (constants.MAP_Y / 2), field_left + (constants.MAP_Y / 2), 
        #    get_y(field_top, height), get_y(field_bottom, height)
        #)
        linedashed(draw, dash_color, 3,
            field_right - constants.MAP_Y_QUARTER, field_right - constants.MAP_Y_QUARTER, 
            get_y(field_top, height), get_y(field_bottom, height)
        )
        linedashed(draw, dash_color, 3,
            field_left + 12, field_right + 12, 
            get_y(field_bottom + constants.MAP_X_THIRD, height), get_y(field_bottom + constants.MAP_X_THIRD, height)
        )
        linedashed(draw, dash_color, 3,
            field_left + 12, field_right + 12, 
            get_y(field_top - constants.MAP_X_THIRD, height), get_y(field_top - constants.MAP_X_THIRD, height)
        )

def draw_field_lines_vert(draw, margin, height, sections=False):
    field_left, field_right = 2 * margin, (2 * margin) + constants.MAP_Y
    goal_height = (constants.GOAL_Z / constants.SCALE) + margin + 15
    ball_height = (2 * (constants.BALL_RAD / constants.SCALE)) + margin + 15
    field_bottom, field_top = margin + 15, constants.MAP_Z + margin + 15

    draw.line([
        (field_left - 20, get_y(field_bottom, height)),
        (field_left - 20, get_y(goal_height, height)),
        (field_left, get_y(goal_height, height)),
        (field_left, get_y(field_top, height)),
        (field_right, get_y(field_top, height)),
        (field_right, get_y(goal_height, height)),
        (field_right + 20, get_y(goal_height, height)),
        (field_right + 20, get_y(field_bottom, height)),
        (field_left - 20, get_y(field_bottom, height)),
    ], fill=(70,70,70,), width=6, joint="curve")
    
    if sections:
        linedashed(draw, (0,0,0), 3,
            field_left + 12, field_right + 12,
            get_y(ball_height, height), get_y(ball_height, height)
        )
        linedashed(draw, (0,0,0), 3,
            field_left + 12, field_right + 12,
            get_y(goal_height, height), get_y(goal_height, height)
        )
        linedashed(draw, (0,0,0), 3,
            field_left + constants.MAP_Y_QUARTER, field_left + constants.MAP_Y_QUARTER,
            get_y(field_top, height), get_y(field_bottom, height)
        )
        linedashed(draw, (0,0,0), 3,
            field_left + (2 * constants.MAP_Y_QUARTER), field_left + (2 * constants.MAP_Y_QUARTER),
            get_y(field_top, height), get_y(field_bottom, height)
        )
        linedashed(draw, (0,0,0), 3,
            field_right - constants.MAP_Y_QUARTER, field_right - constants.MAP_Y_QUARTER,
            get_y(field_top, height), get_y(field_bottom, height)
        )

def draw_circle_legend(draw, text_bottom, margin, right_x, marker_size, font, left_x = None,
        scaling=(1.5, 2, 2.5), labels=(("On\nground", 1.33), ("On\nceiling", 7.66))):
    if left_x is None:
        left_x = round(constants.MAP_Y) + (4 * margin)
    draw.line([(left_x + (3 * margin), text_bottom + (3 * margin)), (right_x - (4.5 * margin), text_bottom + (3 * margin))], 
        fill=(140,140,140), width=4)
    
    circle_base_x = left_x + (4.33 * margin)
    circle_base_y = text_bottom + (6 * margin)

    draw.ellipse([
            (circle_base_x - marker_size, circle_base_y - marker_size), 
            (circle_base_x + marker_size, circle_base_y + marker_size)], 
        outline=(140,140,140), width=4)
    draw.ellipse([
            (circle_base_x + (3 * margin) - (scaling[0] * marker_size), circle_base_y - (scaling[0] * marker_size)), 
            (circle_base_x + (3 * margin) + (scaling[0] * marker_size), circle_base_y + (scaling[0] * marker_size))], 
        outline=(140,140,140), width=4)
    draw.ellipse([
            (circle_base_x + (6 * margin) - (scaling[1] * marker_size), circle_base_y - (scaling[1] * marker_size)), 
            (circle_base_x + (6 * margin) + (scaling[1] * marker_size), circle_base_y + (scaling[1] * marker_size))], 
        outline=(140,140,140), width=4)
    draw.ellipse([
            (circle_base_x + (9 * margin) - (scaling[2] * marker_size), circle_base_y - (scaling[2] * marker_size)), 
            (circle_base_x + (9 * margin) + (scaling[2] * marker_size), circle_base_y + (scaling[2] * marker_size))], 
        outline=(140,140,140), width=4)
    
    draw.multiline_text((circle_base_x - (labels[0][1] * margin), circle_base_y + (1.75 * margin)), 
        labels[0][0], fill=(70,70,70), font=font, align="center")
    draw.multiline_text((circle_base_x + (labels[1][1] * margin), circle_base_y + (1.75 * margin)), 
        labels[1][0], fill=(70,70,70), font=font, align="center")
    
### Analysis utilities

def get_xG_val(game, shot):
    clf = jb.load(os.path.join("clf", "xgb.joblib"))
    col_names = [
        "distance", "angle", "z_angle", "goalward_speed", "ball_speed", "goalside_defs", "num_behind_ball", 
        "num_challenging", "num_towards_net", "num_in_net", "num_rotating", "prev_touch_type", "prev_touch_frames", 
        "recent_demos", "boost", "avg_def_boost", "goal", "frame_number", "is_orange"
    ]
    train_cols = [
        "distance", "angle", "z_angle", "goalside_defs", "prev_touch_type_2", "prev_touch_type_3", 
        "recent_demos", "avg_def_boost", "num_behind_ball",
        "num_rotating", "num_challenging", "num_towards_net", "num_in_net"
    ]

    features = ShotDetailStats.get_shot_features(game, shot)
    shot_df = pd.DataFrame(np.array([features]), columns=col_names)
    shot_df['prev_touch_type'] = shot_df['prev_touch_type'].astype(np.int64)
    shot_df = pd.get_dummies(shot_df, columns=["prev_touch_type"])
    cat_cols = ["prev_touch_type_1", "prev_touch_type_2", "prev_touch_type_3"]
    for col_name in cat_cols:
        if col_name not in shot_df:
            shot_df[col_name] = False
    xG_val = clf.predict_proba(shot_df[train_cols])[:, 1][0]
    return xG_val 

def get_region_label(region: str):
    if region == "Asia-Pacific":
        return "APAC"
    elif region == "Europe":
        return "EU"
    elif region == "Middle East & North Africa":
        return "MENA"
    elif region == "North America":
        return "NA"
    elif region == "Oceania":
        return "OCE"
    elif region == "South America":
        return "SAM"
    elif region == "Sub-Saharan Africa":
        return "SSA"
    else:
        return "N/A"
    
def get_label_from_team(game, team, reg=""):
    team_ids = [player_id.id for player_id in team.player_ids]
    team_players = [player.name for player in game.players if player.id.id in team_ids]
    return get_team_label(team.name, reg, team_players)

def get_region_from_team(team: str):
    if team in ["ELEVATE", "GLADIATORS"]:
        return "APAC"
    elif team in ["TEAM BDS", "TEAM VITALITY", "GENTLE MATES", "KARMINE CORP", "OXYGEN ESPORTS"]:
        return "EU"
    elif team in ["RULE ONE", "FALCONS", "TWISTED MINDS"]:
        return "MENA"
    elif team in ["G2 STRIDE", "OG ESPORTS", "LUMINOSITY", "GENG MOBIL1", "SPACESTATION"]:
        return "NA"
    elif team in ["PWR", "PIONEERS", "CHIEFS ESC"]:
         return "OCE"
    elif team in ["FURIA", "COMPLEXITY", "TEAM SECRET"]:
        return "SAM"
    elif team in ["LIMITLESS", "TEAM MOBULA"]:
        return "SSA"
    else:
        return "N/A"

def get_team_label(name: str, region=None, players=[]):
    if name in ["0545REV", "0545 REV", "REV", "REVELLIE", "REVIELLE", "REVIELLIE"]:
        return "0545 REVELLIE"
    elif name == "LASTOPTIONS":
        return "LAST OPTIONS"
    elif name == "RL":
        return "RANDOMLINE"
    elif name in ["KRü ESPORTS", "KRU ESPORTS", "KRü"]:
        return "KRÜ ESPORTS"
    elif name == "ASE":
        return "ATLANTIC"
    elif name == "RULE ONE":
        return "ANYTHING"
    elif name in ["AWAWA", "RANGER"]:
        return "RANGER ESPORTS"
    elif name == "TEAM ESPADA":
        return "ESPADA"
    elif name == "BBS":
        return "BODYBUILDERS"
    elif name in ["TEAM FALCONS", "TBD"]:
        return "FALCONS" 
    elif name in ["COLDDDD", "COLD"] and region == "NA":
        return "COLD"
    elif name == "SHOPIFYREBELLION":
        return "REBELLION"
    elif name in ["COLD", "COLDDDD"]:
        return "COLDDDD"
    elif name in ["EXO", "WARM"]:
        return "EXO CLAN"
    elif name == "RED CORDIAL":
        return "LONG RED CORDIAL"
    elif name == "SKRIMZ":
        return "SKRIMZWORLD"
    elif name in ["TAKA", "TIKI TAKA", "FIZ6"]:
        return "FIZ6 GAMING"
    elif name in ["KIBB", "KIBB GANG"]:
        return "KIBBGANG"
    elif name == "RPS SCYTHE":
        return "REAPERS SCYTHE"
    elif name == "TONKATRUCKS":
        return "TONKA TRUCKS"
    elif name == "THATS CRAZY":
        return "THAT'S CRAZY"
    elif name == "NIGHTMARE":
        return "G3 ESPORTS"
    elif name == "C VENT":
        return "CVENT"
    elif name in ["OE", "OVERLOOKED ENT"]:
        return "OVERLOOKED"
    elif name in ["PERMITTA A S", "TVYG&CA"]:
        return "PERMITTA AS"
    elif name in ["GYU", "GYUTAN"]:
        return "GYUTAN GAMING"
    elif name in ["F MARINOS", "F. MARINOS", "F.MARINOS", "YFM"]:
        return "Y.F.MARINOS"
    elif name in ["SAILING ES", "SAILING ESPORTS", "SAILINGESPORTS"] and "kroado" in players:
        return "Ex-SAILINGESPORTS"
    elif name in ["SAILING ES", "SAILING ESPORTS", "CHAPATI DREAM", "CPT DREAM", "SE", "SAILING ESPORT", "SAILING"]:
        return "SAILINGESPORTS"
    elif name == "RE ESPORTS":
        return "RESEDA"
    elif name == "TC":
        return "THE COURT"
    elif name in ["SUSHIBIRYANI", "SUSHI BRIYANI", "SUSHBIRYANI", "SUSHIBRIYANI", "SEN", "SENSATION", "BIRYANI SUSHI"]:
        return "SENSATIONALS"
    elif name in ["ASTR", "ASTRONIC", "ASTRONIC SQ"] and "Ram" in players:
        return "Ex-ASTRONIC SQ"
    elif name in ["ASTR", "ASTRONIC", "FH", "FIRE HAWKS"]:
        return "ASTRONIC SQ"
    elif name in ["DQ", "DRIFTQUEENS", "DRIFT QUEENS"] and ("DQ fusion77" in players or "Fusion77" in players):
        return "Ex-DRIFT QUEENS"
    elif name in ["DQ", "DRIFTQUEENS"]:
        return "DRIFT QUEENS"
    elif name == "104":
        return "104(ANNI)"
    elif name == "FLOP":
        return "FLOEPPA"
    elif name in ["LAS", "LA SIGNAL"] and region == "APAC":
        return "LA SIGNAL (APAC)"
    elif name in ["LAS", "LA SIGNAL"] and region == "SSA":
        return "GENESIX"
    elif name == "ONLY PHANS":
        return "ONLYPHANS"
    elif name == "NXTA":
        return "NXT AQUA"
    elif name in ["TE", "ELITES"]:
        return "THE ELITES"
    elif name in ["YMC", "YOUNG MONEY CLAN", "YOUNG MONEY"] and region == "SSA":
        return "YMC (SSA)*"
    elif name == "PNJ":
        return "LES PONEYS"
    elif name == "LMT":
        return "LIMITLESS"
    elif name == "WRG" and ("JRS" in players or "Friction" in players):
        return "Ex-WRG"
    elif name == "PBUN":
        return "BUNZ"
    elif name in ["EX OBLIVIONE", "OBLIVIONE", "DRAGONS ESPORTS"]:
        return "DRAGONS"
    elif name in ["END CEX", "END", "ENDPOINT CEX"]:
        return "ENDPOINT"
    elif name in ["MOIST", "MOIST ESPORTS"] and region == "EU":
        return "JOBLESS"
    elif name in ["PIRATES", "MOIST"] and region == "NA":
        return "MOIST ESPORTS"
    elif name in ["OXYGEN", "OXG"]:
        return "OXYGEN ESPORTS"
    elif name == "VITALITY":
        return "TEAM VITALITY"
    elif name == "M8 ALPINE":
        return "GENTLE MATES"
    elif name in ["KC", "KARMINE KORP"]:
        return "KARMINE CORP"
    elif name == "VILLIANS":
        return "VILLAINS"
    elif name in ["TWIS MINDS", "TWISTEDMINDS"]:
        return "TWISTED MINDS"
    elif name in ["GENG MOBIL 1", "GEN.G MOBIL1", "GEN.G MOBIL1 "]:
        return "GENG MOBIL1"
    elif name in ["TN", "TRUE NEUTRAL"] and "shad" in players:
        return "Ex-TRUE NEUTRAL"
    elif name == "THEY COOK":
        return "THEY WHOMST COOK"
    elif name in ["NOOKLE POOK", "NOOKLES"]:
        return "NOOKLES POOKLES"
    elif name == "SOUJA BOYS":
        return "SOULJA BOYS"
    elif name == "NOVO": 
        return "NOVO ESPORTS"
    elif name in ["77 BLOCKS", "77B", "77BLOCK"]:
        return "77BLOCKS"
    elif name == "BNJR":
        return "BONJOUR"
    elif name == "DRAN GNG":
        return "DRAIN GNG"
    elif (name == "ORG" and region == "SSA") or name in ["ORGLESS", "GENESIX ESPORTS"]:
        return "GENESIX"
    elif name in ["OWD", "OWNED", "OWNED ESPORT"]:
        return "OWNED ESPORTS"
    elif name in ["SHMO", "SCHMONGOLIA", "SHMONGOLIA", "9 LIES"]:
        return "9LIES"
    elif name in ["SSB", "BALLERS", "SESAME STREET"]:
        return "SES ST BALLERS"
    elif name in ["WOT", "WOT PLAYERS"]:
        return "WORLD OF TANKS"
    elif name in ["SKIB", "STRASKBIDI"]:
        return "STRASKIBIDI"
    elif name in ["ALBINO", "ALBINO MONK", "ALB MONK"]:
        return "ALBINO MONKEYS"
    elif name in ["DETONATORS", "DE", "DTN"]:
        return "DETONATOR"
    elif name in ["GO BLOCKS", "GO BLOCKS!"]:
        return "DTL"
    elif name == "TRIPLE JAWS":
        return "TRIPLE JAWA"
    elif name == "FISH":
        return "LE FISHE"
    elif name == "BOKETACHI":
        return "KOSHIHIKARI"
    elif name == "KC":
        return "KARMINE CORP"
    elif name == "SUHH":
        return "SUHHH"
    elif name == "CLB":
        return "CALABRESOS"
    elif name in ["SHAMAN", "SHAMAN ESPORTS", "D4OS", "DIED 4 OUR SINS"]:
        return "TRUE NEUTRAL"
    elif name == "LUK":
        return "LUK ESPORTS"
    elif name in ["NICKNACK'S", "NICKNACKS"]:
        return "NICKNACK"
    elif name in ["YMC", "YOUNG MONEY CLAN"] and region == "OCE":
        return "YMC (OCE)"
    elif name == "NTV" and region == "OCE":
        return "NTR"
    elif name == "ROC":
        return "TEAM ROC"
    elif name in ["5HEAD", "VISION"]:
        return "VISION ESPORTS"
    elif name == "FEARLESS":
        return "R8 ESPORTS"
    elif name in ["BRAVADO", "INFINITY", "INIFITY"]:
        return "BRAVADO GAMING"
    elif name == "ROCKSIDE":
        return "CEW"
    elif name == "NAMELESS":
        return "FOG ESPORTS"
    elif name in ["GOAT", "GOATS", "UG", "THE GOATS"]:
        return "UNKNOWN GOATS"
    elif name == "QSA" and region == "SSA":
        return "QUASAR"
    elif name == "KICKERS" and region == "APAC":
        return "ROCKET KICKERS"
    elif name == "QT PIONEERS":
        return "PIONEERS"
    elif name == "LTC":
        return "LET THEM COOK"
    elif name == "OMELETTE":
        return "CLOUD9"
    elif name == "PLOT TWIST":
        return "CHEERS"
    elif name in ["BARÇA", "BARCA"]:
        return "BARCELONA"
    elif name == "HERO":
        return "HERO BASE"
    elif name == "NEX":
        return "NOT EXPOSED"
    elif name == "GAMERLEGION" and "ianpinheiro" in players:
        return "Ex-GAMERLEGION"
    elif name == "MALADOS":
        return "GAMERLEGION"
    elif name == "W7M" and "wisty" in players:
        return "Ex-W7M"
    elif name == "W7M ESPORTS":
        return "W7M"
    elif name == "TIMELESS" and "Luk" in players:
        return "ERASED"
    elif name in ["OREO", "REVERSE OREO"] and region == "SSA":
        return "PUNISHERS"
    elif name == "GEEKS" or (name == "OREO" and region == "MENA"):
        return "OREO"
    elif name == "GG" and region == "APAC":
        return "GLADIATORS"
    elif name in ["GENE SIX", "GG"]:
        return "GENESIX"
    elif name in ["TRI", "TRIFECTA"]:
        return "TRI-FECTA"
    elif name in ["DIG", "DIGNITY"]:
        return "DIGNITY ESPORTS"
    elif name in ["GRSV", "GRIDSERVE RSV", "RSV", "GS RESOLVE"] and "LuiisP" in players:
        return "Ex-GS RESOLVE"
    elif name in ["GRSV", "GRIDSERVE RSV", "RSV", "REDEMPTION", "GRIDRESRVE RSV"]:
        return "GS RESOLVE"
    elif name == "JOB":
        return "JOBLESS"
    elif name == "BABYDRIVERS":
        return "BABY DRIVERS"
    elif name in ["CHIEFS", "CHIEFS ESC"] and ("gus" in players or "CHF gus" in players):
        return "Ex-CHIEFS ESC"
    elif name in ["CHIEFS", "KAKA'S MINIONS", "THE MINIONS", "MINIONS"] and region == "OCE":
        return "CHIEFS ESC"
    elif name == "GAMERS":
        return "GAMING GAMERS"
    elif name in ["GRACES BLAZE", "GB"]:
        return "GRACESBLAZE"
    elif name == "N55":
        return "NIMMT55"
    elif name == "CRIANCAS":
        return "CRIANÇAS"
    elif name in ["YWS", "SPATE"]:
        return "SPATE ESPORTS"
    elif name == "NXH":
        return "NIXUH"
    elif name == "LOW BLOCKS":
        return "LOW BLOCK"
    elif name == "MAGNIFICO":
        return "LUNA GALAXY"
    elif name == "SDG":
        return "SNAKES DEN"
    else:
        return name

def get_player_label(name: str, region=None):
    if name == "anita max wynn":
        return "Maxeew"
    elif name == "delivery.":
        return "Delivery."
    elif name == "JOREUZ":
        return "Joreuz"
    elif name == "arceon.":
        return "arceon"
    elif name in ["buny", "bny"]:
        return "BunnyDummy"
    elif name == "EXO Creedeny":
        return "Creedeny"
    elif name in ["jímmo", "EXO Jimmo"]:
        return "jimmo"
    elif name in ["SW matthew"]:
        return "matthew"
    elif name == "EXO Inspire":
        return "Inspire"
    elif name in ['Ka7. "]', "Kal. !"]:
        return "Kal."
    elif name == "NK Chub":
        return "Chub"
    elif name == "NK Tkay":
        return "tkay"
    elif name == "N.":
        return "Net"
    elif name in ["a.", "ash"]:
        return "asher"
    elif name in ["n3ptxne!☆", "n3ptxne!", "nptn. ☆"]:
        return "n3ptune!"
    elif name in [".ZPS™", "ELV ZPS"]:
        return ".ZPS"
    elif name == "sweaty":
        return "Sweaty"
    elif name in ["vFBiت", "vFBi"]:
        return "vFbi"
    elif name in ["TROOKُث", "TROOKي"]:
        return "TROOK"
    elif name in ['Creamz,', "creamz"]:
        return 'creamZ'
    elif name == "skip✰":
        return "skippy ✰"
    elif name == "gim":
        return "gimmick"
    elif name in ['gunzinho', 'Gunzzee']:
        return "gunz"
    elif name == "Mass":
        return "mass"
    elif name == "mfn":
        return "fortymula7"
    elif name == "Nemr":
        return "Negative"
    elif name == "Oaly":
        return "oaly."
    elif name == "Rebøuças":
        return "Rebouças"
    elif name in ['Squigly^-^', "Squig"]:
        return "Squigly"
    elif name in ["WALLAH", "gg"]:
        return "machi"
    elif name == "Lba":
        return "AbuLba"
    elif name == "Leoro.":
        return "Leoro"
    elif name == "Kaizennn17":
        return "Kaizen"
    elif name in ["Akai.", "akai", "akai."]:
        return "Akai"
    elif name == "wylew+<3":
        return "wylew"
    elif name in ["Yasar", "green fn"]:
        return "Fades"
    elif name == "oVa":
        return "oVaMPiERz"
    elif name == "Smw":
        return "Smw."
    elif name == "Evh.":
        return "Evh"
    elif name == "GarrettG.":
        return "GarrettG"
    elif name == "Aqua.":
        return "Aqua"
    elif name in ["916edu", "77edu", "edu.", "edu76"]:
        return "edu"
    elif name in ["yANXNZ^^", "yANXNZRL^^"]:
        return "yANXNZ"
    elif name in ["sAD", "Sadness", "sad"]:
        return "Sad"
    elif name == "bmendes.":
        return "bmendes"
    elif name in ["alpe^^", "Alpe"]:
        return "alpe"
    elif name == "CAI0TG1":
        return "caiotg1"
    elif name in ["nxghtt~", "nxghtt:/"]:
        return "nxghtt"
    elif name == "Aztromick":
        return "Aztrø"
    elif name in ["leo", "leodkN", "leodknN", "LeodKn", "leodkn."]:
        return "leodkn"
    elif name == "snip":
        return "snipjz"
    elif name in ["pan. ♢", "pan."]:
        return "pan"
    elif name == "strayy.":
        return "strayy"
    elif name in ["secret brad", "bradk1ng"]:
        return "brad"
    elif name == "D@pplutox":
        return "dappluto"
    elif name in ["secret kv1", "kv1.exe"]:
        return "kv1"
    elif name in ["secret motta", 'møtta.']:
        return "Motta"
    elif name in ["GZ Lax", "GZ Laxinnnnnnnnnnnn", "GZ Laxin"]:
        return "Laxin"
    elif name in ["CHF Superlachie", "Superlachieeeee", "KCP Superlachie"]:
        return "Superlachie"
    elif name == "CHF gus":
        return "gus"
    elif name in ["AKAME !", "LA MENAAACE", "akamé."]:
        return "akame."
    elif name == "!JRS":
        return "JRS"
    elif name == "DQ fusion77":
        return "Fusion77"
    elif name in ["DQ lazybear", "lazybear."]:
        return "lazybear"
    elif name in ["DQ twnzr", "twnzr."]:
        return "twnzr"
    elif name in ["YMC reeho!", "reeho!"]:
        return "reeho!*"
    elif name in ["?davi", "davi"]:
        return "davinsano"
    elif name == "CHF Hntr":
        return "hntr"
    elif name in ["wt", "wt♡"]:
        return "wolftic"
    elif name in ["peach", "peach #:>"]:
        return "peachy"
    elif name == "ReaLize.":
        return "ReaLize"
    elif name == "Realize ;)":
        return "Realize"
    elif name in ["nai.", "NAI", "KUMANAI", "NAI."]:
        return "nai"
    elif name == "k":
        return "kroado"
    elif name in ["Dralii", "dralii897"]:
        return "dralii"
    elif name == "noahsak1":
        return "noahsaki"
    elif name == "CatalysmRL":
        return "Catalysm"
    elif name in ["Radosinho", "rAdosin"]:
        return "Radosin"
    elif name in ["atomik", "LTK_AtomiK", "ltk_atomik"]:
        return "AtomiK"
    elif name in ["AcroniK. ☆", "acro"]:
        return "AcroniK."
    elif name == "-TehQoz-":
        return "TehQoz"
    elif name == "majicbear":
        return "MaJicBear"
    elif name == "caiotg1.":
        return "caiotg1"
    elif name == "Starwindss.":
        return "Starwindss"
    elif name == "lagly.":
        return "lagly"
    elif name == "Lostt.":
        return "Lostt"
    elif name == "klaus.":
        return "klaus"
    elif name == "Bemmz.":
        return "Bemmz"
    elif name == "ajg.":
        return "ajg"
    elif name == "Rmn'":
        return "Rmnn"
    elif name == "FirefoxD #prayforRS":
        return "FirefoxD"
    elif name in ["Haberkamper #prayforRS", "Haber"]:
        return "Haberkamper"
    elif name == "lucas06 #prayforRS":
        return "lucas06"
    elif name == "seck.":
        return "seck"
    elif name in ["mzkn'", 'mzkn")']:
        return "mzkn"
    elif name in ["suco'')", "sucoIV"]:
        return "suco."
    elif name in ["KCP Fibérr", "KCP Fiberr", "KCP Fiberr.", "KCP Fiibeerrz"]:
        return "Fibérr"
    elif name == "KCP Amphis":
        return "Amphis"
    elif name == "KCP Scrub":
        return "Scrub"
    elif name == "juck^szn":
        return "juck.^"
    elif name == "net":
        return "Net"
    elif name == "Rez0.":
        return "Rez"
    elif name in ["ramzzyy>", "<ramzyy>", "ramzzy!"]:
        return "ramzzy"
    elif name == "Twstr.21":
        return "Twister."
    elif name in ["cryypto", "Pulse Cryypto"]:
        return "Cryypto"
    elif name == "smoothoperator":
        return "2Die4"
    elif name in ['Little MOTION")', "Little MOTION"]:
        return "Little MOTION*"
    elif name == "risk.":
        return "risk"
    elif name == "Nuqqet":
        return "Nuqqet*"
    elif name in ["vatira.", "vati."]:
        return "Vatira."
    elif name == "dead":
        return "Dead-Monster"
    elif name == "Emilvald":
        return "EmilVald"
    elif name == "retals":
        return "Retals"
    elif name == "comm":
        return "Comm"
    elif name == ".jelly.†":
        return "jelly.♛"
    elif name == "Atow Rikow!":
        return "Atow."
    elif name == "SW ZENULOUS":
        return "ZENULOUS"
    elif name == "Caleb †":
        return "Caleb"
    elif name == "FIZ6 Cx9":
        return "cx9"
    elif name == "FIZ6 tonio":
        return "tonio"
    elif name == "FIZ6 sour":
        return "sour."
    elif name == "GZ Prompt":
        return "prompt."
    elif name == "CHF kaka":
        return "kaka"
    elif name in ["SW lunR", "GZ lunR"]:
        return "lunR"
    elif name == "GZ Bazlenks":
        return "Baz"
    elif name == "big gez":
        return "misty"
    else:
        return name