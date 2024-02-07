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

def draw_scatter_label(draw, name, pos_x, pos_y, radius, pos):
    if pos == "l":
        draw.text((pos_x - (1.5 * radius), pos_y), name, fill=(0,0,0), font=constants.BOUR_30, anchor='rm')
    elif pos == 'r':
        draw.text((pos_x + (1.5 * radius), pos_y), name, fill=(0,0,0), font=constants.BOUR_30, anchor='lm')
    elif pos == "u":
        draw.text((pos_x, pos_y - (1.25 * radius)), name, fill=(0,0,0), font=constants.BOUR_30, anchor='md')
    else:
        draw.text((pos_x, pos_y + (1.25 * radius)), name, fill=(0,0,0), font=constants.BOUR_30, anchor='ma')

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

def draw_field_lines(draw, margin, height, sections=False):
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
        linedashed(draw, (0,0,0), 3,
            field_left + constants.MAP_Y_QUARTER, field_left + constants.MAP_Y_QUARTER, 
            get_y(field_top, height), get_y(field_bottom, height)
        )
        #linedashed(draw, (0,0,0), 3,
        #    field_left + (constants.MAP_Y / 2), field_left + (constants.MAP_Y / 2), 
        #    get_y(field_top, height), get_y(field_bottom, height)
        #)
        linedashed(draw, (0,0,0), 3,
            field_right - constants.MAP_Y_QUARTER, field_right - constants.MAP_Y_QUARTER, 
            get_y(field_top, height), get_y(field_bottom, height)
        )
        linedashed(draw, (0,0,0), 3,
            field_left + 12, field_right + 12, 
            get_y(field_bottom + constants.MAP_X_THIRD, height), get_y(field_bottom + constants.MAP_X_THIRD, height)
        )
        linedashed(draw, (0,0,0), 3,
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
    
def draw_title_text(draw, logo_width, margin, config, font_one, font_two):
    draw.text((logo_width + 50 + margin, margin), config["t1"], fill=(0,0,0), font=font_one)
    draw.text((logo_width + 50 + margin, 80 + margin), config["t2"], fill=(70,70,70), font=font_two)
    draw.text((logo_width + 50 + margin, 130 + margin), config["t3"], fill=(70,70,70), font=font_two)

## Analysis utils
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

def get_team_label(name: str):
    if name in ["0545REV", "0545 REV"]:
        return "0545 REVELLIE"
    elif name == "LASTOPTIONS":
        return "LAST OPTIONS"
    elif name == "KRü ESPORTS" or name == "KRU ESPORTS":
        return "KRÜ ESPORTS"
    elif name == "BBS":
        return "BODYBUILDERS"
    elif name == "TEAM FALCONS":
        return "FALCONS" 
    elif name == "COLD":
        return "COLDDDD"
    elif name == "RED CORDIAL":
        return "LONG RED CORDIAL"
    elif name == "SKRIMZ":
        return "SKRIMZWORLD"
    elif name == "TAKA":
        return "TIKI TAKA"
    elif name == "THATS CRAZY":
        return "THAT'S CRAZY"
    elif name == "THE MINIONS":
        return "KAKA'S MINIONS"
    elif name == "C VENT":
        return "CVENT"
    elif name == "F MARINOS" or name == "F. MARINOS" or name == "F.MARINOS":
        return "Y.F.MARINOS"
    elif name == "SAILING ES" or name == "SAILING ESPORTS":
        return "SAILINGESPORTS"
    elif name == "RE ESPORTS":
        return "RESEDA"
    elif name == "ASTR":
        return "ASTRONIC"
    elif name == "DQ":
        return "DRIFTQUEENS"
    elif name == "FH":
        return "FIRE HAWKS"
    elif name == "FLOP":
        return "FLOEPPA"
    elif name == "LAS":
        return "LA SIGNAL"
    elif name == "NXTA":
        return "NXT AQUA"
    elif name == "TE":
        return "ELITES"
    elif name == "YOUNG MONEY CLAN" or name == "YOUNG MONEY":
        return "YMC"
    elif name == "PNJ":
        return "LES PONEYS"
    elif name == "PBUN":
        return "BUNZ"
    elif name == "OBLIVIONE":
        return "EX OBLIVIONE"
    elif name == "CPT DREAM":
        return "CHAPATI DREAM"
    else:
        return name

def get_player_label(name: str):
    if name == "anita max wynn":
        return "Maxeew"
    elif name == "buny":
        return "BunnyDummy"
    elif name == 'Creamz,':
        return 'creamZ'
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
    elif name == "Rebøuças":
        return "Rebouças"
    elif name == 'Squigly^-^':
        return "Squigly"
    elif name == "WALLAH":
        return "machi"
    elif name == "Yasar":
        return "Fades"
    else:
        return name