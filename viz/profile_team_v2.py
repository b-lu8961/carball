from viz import constants, utils

import json
import numpy as np
import os
from PIL import Image, ImageDraw

MARGIN = 40

MARKER_SIZE = 10

WHITE, BLACK = (255,255,255), (0,0,0)
LIGHT_GREY, DARK_GREY = (180,180,180), (70,70,70)

HEADER_HEIGHT = 325
LAYER_1_HEIGHT = 1200 + MARGIN
LAYER_2_HEIGHT = 1950 + MARGIN
PL_LAYER_HEIGHT = 1800 + MARGIN

def get_y(val, img_height):
    return img_height - val
    
def calculate_hit_maps(data_path, config):
    map_x, map_y = constants.MAP_X * constants.SCALE, constants.MAP_Y * constants.SCALE
    bounds_x = [(map_x / 6, map_x / 2), (-(map_x / 6), map_x / 6), (-(map_x / 2), -(map_x / 6))]
    bounds_y = [(-np.inf, -(map_y / 4)), (-(map_y / 4), 0), (0, map_y / 4), (map_y / 4, np.inf)]
    for_totals = {"goals": [[0,0,0,0],[0,0,0,0],[0,0,0,0]], "shots": [[0,0,0,0],[0,0,0,0],[0,0,0,0]]}
    against_totals = {"goals": [[0,0,0,0],[0,0,0,0],[0,0,0,0]], "shots": [[0,0,0,0],[0,0,0,0],[0,0,0,0]]}
    
    game_list = utils.read_group_data(data_path)
    for game in game_list:
        t0, t1 = utils.get_team_label(game.teams[0].name, config["region"]), utils.get_team_label(game.teams[1].name, config["region"])
        if config["key"] not in [t0, t1]:
            continue

        if t0 == config["key"]:
            for_team, against_team = game.teams[0], game.teams[1]
        else:
            for_team, against_team = game.teams[1], game.teams[0]
        
        for shot in game.game_metadata.shot_details:
            if shot.is_orange == for_team.is_orange:
                shot_map = for_totals
                ball_x = -1 * shot.ball_pos.pos_x if for_team.is_orange else shot.ball_pos.pos_x
                ball_y = -1 * shot.ball_pos.pos_y if for_team.is_orange else shot.ball_pos.pos_y
            else:
                shot_map = against_totals
                ball_x = -1 * shot.ball_pos.pos_x if not against_team.is_orange else shot.ball_pos.pos_x
                ball_y = -1 * shot.ball_pos.pos_y if not against_team.is_orange else shot.ball_pos.pos_y
            
            for i in range(len(bounds_y)):
                if bounds_y[i][0] <= ball_y and ball_y < bounds_y[i][1]:
                    for j in range(len(bounds_x)):
                        if bounds_x[j][0] <= ball_x and ball_x < bounds_x[j][1]:
                            shot_map["shots"][j][i] += 1
                            if shot.is_goal:
                                shot_map["goals"][j][i] += 1
                            break
                    break
    
    return (for_totals, against_totals)
        
def draw_heat_map(img, draw, color_map, text_map):
    MID_X, MID_Y = (constants.MAP_Y + (MARGIN * 4)) / 2, (constants.MAP_X + (MARGIN * 2)) / 2
    coords_x = [
        (MID_X - (2 * constants.MAP_Y_QUARTER) + 5, MID_X - constants.MAP_Y_QUARTER - 5),
        (MID_X - constants.MAP_Y_QUARTER + 5, MID_X - 5),
        (MID_X + 5, MID_X + constants.MAP_Y_QUARTER - 5),
        (MID_X + constants.MAP_Y_QUARTER + 5, MID_X + (2 * constants.MAP_Y_QUARTER) - 5)
    ]
    coords_y = [
        (get_y(MID_Y + (constants.MAP_X / 2) - 5, img.height), get_y(MID_Y + (constants.MAP_X / 6) + 5, img.height)), 
        (get_y(MID_Y + (constants.MAP_X / 6) - 5, img.height), get_y(MID_Y - (constants.MAP_X / 6) + 5, img.height)), 
        (get_y(MID_Y - (constants.MAP_X / 6) - 5, img.height), get_y(MID_Y - (constants.MAP_X / 2) + 5, img.height))
    ]
    text_x = [
        MID_X - (1.5 * constants.MAP_Y_QUARTER), MID_X - (0.5 * constants.MAP_Y_QUARTER),
        MID_X + (0.5 * constants.MAP_Y_QUARTER), MID_X + (1.5 * constants.MAP_Y_QUARTER) - 10
    ]
    text_y = [get_y(MID_Y + constants.MAP_X_THIRD + 20, img.height), get_y(MID_Y + 20, img.height), get_y(MID_Y - constants.MAP_X_THIRD + 20, img.height)]

    for i in range(len(coords_y)):
        for j in range(len(coords_x)):
            if i == 0 and j == 0:
                draw.polygon([
                    (MID_X - (constants.MAP_Y / 2) + constants.CORNER_SIDE + 2.2, get_y(MID_Y + (constants.MAP_X / 2) - 5, img.height)), 
                    (MID_X - constants.MAP_Y_QUARTER - 5, get_y(MID_Y + (constants.MAP_X / 2) - 5, img.height)),
                    (MID_X - constants.MAP_Y_QUARTER - 5, get_y(MID_Y + (constants.MAP_X / 6) + 5, img.height)),
                    (MID_X - (constants.MAP_Y / 2) + 5, get_y(MID_Y + (constants.MAP_X / 6) + 5, img.height)),
                    (MID_X - (constants.MAP_Y / 2) + 5, get_y(MID_Y + (constants.MAP_X / 2) - constants.CORNER_SIDE - 2.2, img.height))
                ], fill=color_map[i][j])
            elif i == 0 and j == 3:
                draw.polygon([
                    (MID_X + (constants.MAP_Y / 2) - constants.CORNER_SIDE - 2.2, get_y(MID_Y + (constants.MAP_X / 2) - 5, img.height)), 
                    (MID_X + constants.MAP_Y_QUARTER + 5, get_y(MID_Y + (constants.MAP_X / 2) - 5, img.height)),
                    (MID_X + constants.MAP_Y_QUARTER + 5, get_y(MID_Y + (constants.MAP_X / 6) + 5, img.height)),
                    (MID_X + (constants.MAP_Y / 2) - 5, get_y(MID_Y + (constants.MAP_X / 6) + 5, img.height)),
                    (MID_X + (constants.MAP_Y / 2) - 5, get_y(MID_Y + (constants.MAP_X / 2) - constants.CORNER_SIDE - 2.2, img.height))
                ], fill=color_map[i][j])
            elif i == 2 and j == 0:
                draw.polygon([
                    (MID_X - (constants.MAP_Y / 2) + constants.CORNER_SIDE + 2.2, get_y(MID_Y - (constants.MAP_X / 2) + 5, img.height)), 
                    (MID_X - constants.MAP_Y_QUARTER - 5, get_y(MID_Y - (constants.MAP_X / 2) + 5, img.height)),
                    (MID_X - constants.MAP_Y_QUARTER - 5, get_y(MID_Y - (constants.MAP_X / 6) - 5, img.height)),
                    (MID_X - (constants.MAP_Y / 2) + 5, get_y(MID_Y - (constants.MAP_X / 6) - 5, img.height)),
                    (MID_X - (constants.MAP_Y / 2) + 5, get_y(MID_Y - (constants.MAP_X / 2) + constants.CORNER_SIDE + 2, img.height))
                ], fill=color_map[i][j])
            elif i == 2 and j == 3:
                draw.polygon([
                    (MID_X + (constants.MAP_Y / 2) - constants.CORNER_SIDE - 2.2, get_y(MID_Y - (constants.MAP_X / 2) + 5, img.height)), 
                    (MID_X + constants.MAP_Y_QUARTER + 5, get_y(MID_Y - (constants.MAP_X / 2) + 5, img.height)),
                    (MID_X + constants.MAP_Y_QUARTER + 5, get_y(MID_Y - (constants.MAP_X / 6) - 5, img.height)),
                    (MID_X + (constants.MAP_Y / 2) - 5, get_y(MID_Y - (constants.MAP_X / 6) - 5, img.height)),
                    (MID_X + (constants.MAP_Y / 2) - 5, get_y(MID_Y - (constants.MAP_X / 2) + constants.CORNER_SIDE + 2, img.height))
                ], fill=color_map[i][j])
            else:
                draw.rectangle([(coords_x[j][0], coords_y[i][0]), (coords_x[j][1], coords_y[i][1])], fill=color_map[i][j])

    for i in range(len(coords_y)):
       for j in range(len(coords_x)):
            lbl_img = Image.new(mode="RGBA", size=(round(text_map[i][j]["len"]), 90), color=(0,0,0,0))
            lbl_draw = ImageDraw.Draw(lbl_img)
            lbl_draw.multiline_text((0, 0), text_map[i][j]["text"], fill=BLACK, font=constants.BOUR_50, align="center")
            lbl_rot = lbl_img.rotate(-90, expand=True)
            x_pad = -40 if len(text_map[i][j]["text"].split('\n')) > 1 else -60
            img.paste(lbl_rot, (round(text_x[j] + x_pad), round(text_y[i] - (lbl_img.width / 2) + 20)), mask=lbl_rot)

def draw_fields(totals):
    width, height = round(constants.MAP_Y) + (MARGIN * 4), round(constants.MAP_X) + (MARGIN * 2)
    for_img = Image.new(mode="RGBA", size = (width, height), color=WHITE)
    for_draw = ImageDraw.Draw(for_img)
    
    against_img = Image.new(mode="RGBA", size = (width, height), color=WHITE)
    against_draw = ImageDraw.Draw(against_img)

    total_pcts = (
        np.array(totals[0]['goals']) / np.array(totals[0]['shots']),
        np.array(totals[1]['goals']) / np.array(totals[1]['shots'])
    )
    max_pcts = [np.nanmax(total_pcts[0]), np.nanmax(total_pcts[1])]
    color_maps = ([], [])
    text_maps = ([], [])
    for idx in range(len(total_pcts)):
        diff = total_pcts[idx]
        for i in range(len(diff)):
            row = diff[i]
            color_list = []
            text_list = []
            for j in range(len(row)):
                val = row[j]
                if np.isnan(val):
                    color_str = (200, 200, 200)
                else:
                    color_str = "hsl(19, 82%, {}%)" if idx == 1 else "hsl(205, 64%, {}%)"
                    color_str = color_str.format(100 - (45 * (val / max_pcts[idx])))
                color_list.append(color_str)

                pct_map = total_pcts[idx]
                if idx == 0:
                    text = "N/A" if np.isnan(pct_map[i][j]) else "{:.1f}%\n({:d}/{:d})"\
                        .format(100 * pct_map[i][j], totals[idx]["goals"][i][j], totals[idx]["shots"][i][j])
                else:    
                    text = "N/A" if np.isnan(pct_map[i][j]) else "{:.1f}%\n({:d}/{:d})"\
                        .format(100 * pct_map[i][j], totals[idx]["goals"][i][j], totals[idx]["shots"][i][j])
                text_len = max(for_draw.textlength(lbl_part, font=constants.BOUR_50) for lbl_part in text.split('\n'))
                text_list.append({"text": text, "len": text_len})
            color_maps[idx].append(color_list)
            text_maps[idx].append(text_list)
    
    draw_heat_map(for_img, for_draw, color_maps[0], text_maps[0])
    draw_heat_map(against_img, against_draw, color_maps[1], text_maps[1])

    utils.draw_field_lines(for_draw, MARGIN, height, sections=True)
    utils.draw_field_lines(against_draw, MARGIN, height, sections=True)

    return for_img, against_img

def draw_header(img: Image.Image, draw: ImageDraw.ImageDraw, stat_data, config):
    # Logo in top left
    pos = (MARGIN, MARGIN + 25)
    logo_width = None
    with Image.open(os.path.join("viz", "images", "logos", config["logo"])) as logo:
        divisor = max(logo.width / 300, logo.height / 300)
        logo_width, logo_height = round(logo.width / divisor), round(logo.height / divisor)
        logo_small = logo.resize((logo_width, logo_height))
        try:
            img.paste(logo_small, pos, mask = logo_small)
        except ValueError:
            img.paste(logo_small, pos)

    # Title text
    font_one, font_two = constants.BOUR_100, constants.BOUR_60
    draw.text((logo_width + 50 + MARGIN, MARGIN), config["t1"], fill=(0,0,0), font=font_one)
    draw.text((logo_width + 50 + MARGIN, 100 + MARGIN), config["t2"], fill=(70,70,70), font=font_two)
    draw.text((logo_width + 50 + MARGIN, 170 + MARGIN), config["t3"], fill=(70,70,70), font=font_two)

    # Dotted circle logo
    utils.draw_dotted_circle(draw, img.width, MARGIN, config["c1"], config["c2"])

def draw_layer_1(img: Image.Image, draw: ImageDraw.ImageDraw, stat_data, config):
    LAYER_1_TOP = HEADER_HEIGHT
    img_14 = img.width / 4

    # Overview
    ovw_left, ovw_right = (3 * MARGIN), img_14
    ovw_base_y, ovw_step = LAYER_1_TOP + 140, 250
    draw.text(((ovw_left + ovw_right) / 2, LAYER_1_TOP), "Overview", fill=BLACK, font=constants.BOUR_90, anchor="ma")

    labels = ["Seed:", "Record:", "Placements:", "Points:"]
    record_str = "{} - {}  ".format(stat_data[config["key"]]["record"][0], stat_data[config["key"]]["record"][1])
    pct_str = "({:.1f}%)".format(100 * stat_data[config["key"]]["record"][0] / sum(stat_data[config["key"]]["record"]))
    vals = [
        "{} {}".format(config["region"], config["seed"]),
        record_str + pct_str,
        config["placements"],
        str(config["points"])
    ]
    for i in range(len(labels)):
        draw.text((ovw_left + MARGIN, ovw_base_y + (i * ovw_step)), labels[i], fill=DARK_GREY, font=constants.BOUR_70)
        draw.text((ovw_left + (3 * MARGIN), ovw_base_y + (i * ovw_step) + 110), vals[i], fill=BLACK, font=constants.BOUR_80)

    draw.rounded_rectangle([(ovw_left - 30, ovw_base_y - 20), (ovw_right, LAYER_1_TOP + LAYER_1_HEIGHT - 108)], 75,
        outline=constants.REGION_COLORS[config["region"]][0], width=5)

    # Stats per 5:00
    stt_left, stt_right = img_14 + (3 * MARGIN), img.width - (2 * MARGIN)
    stt_sixth = ((stt_right - stt_left) / 6)
    stt_16, stt_36, stt_56 = stt_left + stt_sixth, (stt_left + stt_right) / 2, stt_right - stt_sixth
    draw.text((stt_36, LAYER_1_TOP), "Stats per 5:00", fill=BLACK, font=constants.BOUR_90, anchor="ma")

    stat_base_x = [stt_16, stt_36, stt_56]
    stat_base_y, stat_step = LAYER_1_TOP + 120, 350
    cols = [
        [("Goals", "goals"), ("xG", "xG_for"), ("Shots", "shots")],
        [("Goals Against", "goals_against"), ("xG Against", "xG_against"), ("Shots Against", "shots_against")],
        [("Touches", "touches"), ("Demos", "demos"), ("Boost Steals", "big_steals")]
    ]
    for i in range(len(cols)):
        col = cols[i]
        base_x = stat_base_x[i]
        col_left, col_right = base_x - stt_sixth, base_x + stt_sixth
        for j in range(len(col)):
            base_y = stat_base_y + (j * stat_step)
            rect_color = config["c1"] if (i + j) % 2 == 0 else config["c2"]
            draw.rounded_rectangle([(col_left + 20, base_y), (col_right - 20, base_y + stat_step - 40)], 75, outline=rect_color, width=5)
            draw.line([(base_x, base_y + 100), (base_x, base_y + 270)], fill=LIGHT_GREY, width=5)
            
            keys = col[j]
            draw.text((base_x, base_y + 20), keys[0], fill=DARK_GREY, font=constants.BOUR_70, anchor="ma")

            # Stat value
            stat_val = stat_data[config["key"]][keys[1]] / (stat_data[config["key"]]["secs"] / 300)
            draw.text((10 +(col_left + base_x) / 2, base_y + 140), str(round(stat_val, 2)), fill=BLACK, font=constants.BOUR_90, anchor="ma")

            # Rank data
            sign = 1 if i == 1 else -1
            sort_data = dict(sorted(stat_data.items(), key=lambda item: (sign * item[1][keys[1]] / (item[1]["secs"] / 300))))
            world_index = list(sort_data.keys()).index(config["key"]) + 1
            region_data = {key: val for key, val in stat_data.items() if val["region"] == config["region"]}
            region_sort = dict(sorted(region_data.items(), key=lambda item: (sign * item[1][keys[1]] / (item[1]["secs"] / 300))))
            region_index = list(region_sort.keys()).index(config["key"]) + 1
            draw.text((base_x + 110, base_y + 130), str(region_index), fill=BLACK, font=constants.BOUR_80, anchor="ma")
            draw.text((base_x + 110, base_y + 210), "in {}".format(config["region"]), fill=DARK_GREY, font=constants.BOUR_50, anchor="ma")
            draw.text((base_x + 320, base_y + 130), str(world_index), fill=BLACK, font=constants.BOUR_80, anchor="ma")
            draw.text((base_x + 320, base_y + 210), f"in World", fill=DARK_GREY, font=constants.BOUR_50, anchor="ma")

def get_rot_text(draw, text, font=constants.BOUR_60, height=50, fill=BLACK, rot=90):
    img_len = round(draw.textlength(text, font=font))
    img = Image.new(mode="RGB", size=(img_len, height), color=WHITE)
    img_draw = ImageDraw.Draw(img)
    img_draw.text((0, 0), text, fill=fill, font=font)
    return img.rotate(rot, expand=True), img_len

def draw_layer_2(img: Image.Image, draw: ImageDraw.ImageDraw, stat_data, config, shot_data):
    LAYER_2_TOP = HEADER_HEIGHT + LAYER_1_HEIGHT
    img_24 = img.width / 2
    
    for_img, against_img = draw_fields(shot_data)
    # Left field: shots taken
    for_rot = for_img.rotate(90, expand=True)
    for_left = int(1.5 * MARGIN)
    img.paste(for_rot, (for_left, LAYER_2_TOP + 60))
    draw.text((for_left + (for_img.height / 2), LAYER_2_TOP), "Shots", fill=constants.TEAM_INFO["RLCS"]["c1"], font=constants.BOUR_90, anchor="ma")
    att_img, att_len = get_rot_text(draw, "<< Attacking Direction", font=constants.BOUR_50, height=60, fill=DARK_GREY, rot=-90)
    img.paste(att_img, (round(for_left + for_img.height - 35), round(LAYER_2_TOP + 60 - (att_len / 2) + (constants.MAP_Y + (MARGIN * 4)) / 2)))
    
    # Right field: shots allowed
    against_rot = against_img.rotate(90, expand=True)
    against_left = img.width - against_img.height - int(1.5 * MARGIN)
    img.paste(against_rot, (against_left, LAYER_2_TOP + 60))
    draw.text((against_left + (against_img.height / 2), LAYER_2_TOP), "Shots Against", fill=constants.TEAM_INFO["RLCS"]["c2"], font=constants.BOUR_90, anchor="ma")
    def_img, def_len = get_rot_text(draw, "<< Defending Direction", font=constants.BOUR_50, height=60, fill=DARK_GREY, rot=90)
    img.paste(def_img, (round(against_left - 25), round(LAYER_2_TOP + 60 - (def_len / 2) + (constants.MAP_Y + (MARGIN * 4)) / 2)))

    # Middle space: goal duos
    draw.text((img_24, LAYER_2_TOP), "Goal Combos", fill=BLACK, font=constants.BOUR_90, anchor="ma")
    players = sorted(list(stat_data[config["key"]]["players"].keys()), key=str.casefold)

    pairs = [(0, 1), (0, 2), (1, 2)]
    combo_data = stat_data[config["key"]]["goal_stats"]["combos"]
    name_base, step = LAYER_2_TOP + 150, 525
    left_base, right_base = img_24 - 50, img_24 + 50
    colors = [config["c2"], config["c1"]]
    for i in range(len(pairs)):
        pair = pairs[i]
        p1, p2 = players[pair[0]], players[pair[1]]
        name_y = name_base + (step * i)
        line_top, line_bot = name_y + 100, name_y + 330

        draw.multiline_text((img_24, name_y), f"{utils.get_player_label(p1)}\n\n\n\n\n{utils.get_player_label(p2)}", 
            fill=DARK_GREY, font=constants.BOUR_80, anchor="ma", align="center")
        for combo in combo_data:
            assister, scorer = combo.split("->")
            if p1 == assister and p2 == scorer:
                utils.linear_gradient(img, 
                    [(left_base - 3, line_top), (left_base - 3, line_bot), (left_base + 3, line_bot), (left_base + 3, line_top)], 
                    (left_base, line_top), (left_base, line_bot), colors[0], colors[1]
                )
                draw.ellipse([(left_base - 10, line_bot - 10), (left_base + 10, line_bot + 10)], fill=colors[1])
                draw.text((left_base - 30, (line_top + line_bot) / 2), str(combo_data[combo]), font=constants.BOUR_60, fill=DARK_GREY, anchor="rm")
                continue
            if p2 == assister and p1 == scorer:
                utils.linear_gradient(img, 
                    [(right_base - 3, line_top), (right_base - 3, line_bot), (right_base + 3, line_bot), (right_base + 3, line_top)], 
                    (right_base, line_bot), (right_base, line_top), colors[0], colors[1]
                )
                draw.ellipse([(right_base - 10, line_top - 10), (right_base + 10, line_top + 10)], fill=colors[1])
                draw.text((right_base + 30, (line_top + line_bot) / 2), str(combo_data[combo]), font=constants.BOUR_60, fill=DARK_GREY, anchor="lm")
                continue
    
    # Duo legend
    draw.line([(img_24 - 200, line_bot + 150), (img_24 + 200, line_bot + 150)],
        fill=LIGHT_GREY, width=5          
    )
    utils.linear_gradient(img, 
        [(img_24 - 100, line_bot + 237), (img_24 - 100, line_bot + 243), (img_24 + 100, line_bot + 243), (img_24 + 100, line_bot + 237)], 
        (img_24 - 100, line_bot + 240), (img_24 + 100, line_bot + 240), colors[0], colors[1]
    )
    draw.ellipse([(img_24 + 100 - 10, line_bot + 240 - 10), (img_24 + 100 + 10, line_bot + 240 + 10)], fill=colors[1])
    draw.text((img_24 - 120, line_bot + 240), "Assister", fill=DARK_GREY, font=constants.BOUR_50, anchor="rm")
    draw.text((img_24 + 130, line_bot + 240), "Scorer", fill=DARK_GREY, font=constants.BOUR_50, anchor="lm")

def flip_boost_label(label, big):
    if big:
        return 350 - label
    else:
        return 35 - label

def get_team_data(data_path, config):
    map_x, map_y = constants.MAP_X * constants.SCALE, constants.MAP_Y * constants.SCALE
    bounds_x = [(map_x / 6, map_x / 2), (-(map_x / 6), map_x / 6), (-(map_x / 2), -(map_x / 6))]
    bounds_y = [(-np.inf, -(map_y / 4)), (-(map_y / 4), 0), (0, map_y / 4), (map_y / 4, np.inf)]
    
    player_map = {}
    for_totals = {"goals": [[0,0,0,0],[0,0,0,0],[0,0,0,0]], "shots": [[0,0,0,0],[0,0,0,0],[0,0,0,0]]}
    against_totals = {"goals": [[0,0,0,0],[0,0,0,0],[0,0,0,0]], "shots": [[0,0,0,0],[0,0,0,0],[0,0,0,0]]}
    goal_data = {}
    touch_data = {}
    demo_data = {}
    pickups = {}
    locations = {}
    
    game_list = utils.read_group_data(data_path)
    for game in game_list:
        t0, t1 = utils.get_team_label(game.teams[0].name, config["region"]), utils.get_team_label(game.teams[1].name, config["region"])
        if config["key"] not in [t0, t1]:
            continue

        if t0 == config["key"]:
            for_team, against_team = game.teams[0], game.teams[1]
        else:
            for_team, against_team = game.teams[1], game.teams[0]
        
        for player in game.players:
            if player.team_name == for_team.name:
                pn = utils.get_player_label(player.name)
                player_map[player.id.id] = (pn, player.is_orange)
                if pn not in goal_data:
                    goal_data[pn] = []
                    demo_data[pn] = 0
                    pickups[pn] = {}
                    touch_data[pn] = [0, 0, 0]
                touch_data[pn][0] += player.stats.hit_counts.self_next
                touch_data[pn][1] += player.stats.hit_counts.team_next
                touch_data[pn][2] += player.stats.hit_counts.oppo_next
        
        for shot in game.game_metadata.shot_details:
            if shot.is_orange == for_team.is_orange:
                shot_map = for_totals
                ball_x = -1 * shot.ball_pos.pos_x if for_team.is_orange else shot.ball_pos.pos_x
                ball_y = -1 * shot.ball_pos.pos_y if for_team.is_orange else shot.ball_pos.pos_y
            else:
                shot_map = against_totals
                ball_x = -1 * shot.ball_pos.pos_x if not against_team.is_orange else shot.ball_pos.pos_x
                ball_y = -1 * shot.ball_pos.pos_y if not against_team.is_orange else shot.ball_pos.pos_y
            
            for i in range(len(bounds_y)):
                if bounds_y[i][0] <= ball_y and ball_y < bounds_y[i][1]:
                    for j in range(len(bounds_x)):
                        if bounds_x[j][0] <= ball_x and ball_x < bounds_x[j][1]:
                            shot_map["shots"][j][i] += 1
                            if shot.is_goal:
                                shot_map["goals"][j][i] += 1
                            break
                    break

        for goal in game.game_metadata.goals:
            scorer = utils.get_player_label(goal.scorer)
            if scorer in goal_data:
                goal_data[scorer].append((goal.ball_pos, goal.seconds_remaining < 0))

        for demo in game.game_metadata.demos:
            an = utils.get_player_label(demo.attacker_name)
            if an not in demo_data or not demo.is_valid:
                continue
            
            attacker = [player for player in game.players if player.id.id == demo.attacker_id.id][0]
            next_goal = [goal for goal in game.game_metadata.goals if goal.is_orange == attacker.is_orange and goal.frame_number > demo.frame_number]
            if len(next_goal) > 0 and demo.frame_number > (next_goal[0].frame_number - (30 * 5)):
                demo_data[an] += 1
                #print(game.game_metadata.tag, an, next_goal[0].scorer, next_goal[0].seconds_remaining)

        for pad in game.game_stats.boost_pads:
            if pad.label not in locations:
                locations[pad.label] = {
                    "pos_x": pad.pos_x,
                    "pos_y": pad.pos_y,
                    "big": pad.big
                }
            for pickup in pad.pickups:
                if pickup.player_id.id in player_map:
                    pn, is_orange = player_map[pickup.player_id.id]
                    pad_label = pad.label if not is_orange else flip_boost_label(pad.label, pad.big)
                    if pad_label not in pickups[pn]:
                        pickups[pn][pad_label] = 0
                    pickups[pn][pad_label] += 1

    return (for_totals, against_totals), goal_data, touch_data, demo_data, (pickups, locations)

def draw_marker(draw, pos, mark_type, img_height, size=MARKER_SIZE, outline=None, fill=None, width=2):
    MID_X = (constants.GOAL_X + (MARGIN * 4)) / 2
    base_x = MID_X + pos.pos_x
    base_y = pos.pos_z
    if mark_type == "C":
        draw.ellipse([(base_x - size, get_y(base_y + size, img_height)), (base_x + size, get_y(base_y - size, img_height))], 
            outline=outline, fill=fill, width=width)
    elif mark_type == "S":
        draw.regular_polygon((base_x, get_y(base_y, img_height), size), 4, 
            outline=outline, fill=fill, width=width, rotation=45)
    else:
        draw.regular_polygon((base_x, get_y(base_y, img_height), size + 5), 3, 
            outline=outline, fill=fill, width=width, rotation=60)

def draw_player_layers(img: Image.Image, draw: ImageDraw.ImageDraw, config, goal_data, touch_data, demo_data, boost_data):
    MID_X, MID_Y = (constants.MAP_Y + (MARGIN * 4)) / 2, (constants.MAP_X + (MARGIN * 2)) / 2
    
    sec_top = HEADER_HEIGHT + LAYER_1_HEIGHT + LAYER_2_HEIGHT
    names = sorted(goal_data.keys(), key=str.casefold)
    for name in names:
        draw.text((img.width / 2, sec_top), name, fill=BLACK, font=constants.BOUR_100, anchor="ma")

        # Goal placements
        goal_width, goal_height = constants.GOAL_X + (MARGIN * 4), round(constants.GOAL_Z - 80) + (MARGIN * 2)
        goal_img = Image.new(mode="RGBA", size = (goal_width, goal_height), color=WHITE)
        
        goal_draw = ImageDraw.Draw(goal_img)
        utils.draw_goal_lines(goal_draw, MARGIN, goal_height)
        num_ot = 0
        for goal in goal_data[name]:
            if goal[1]:
                mark = "S"
                color = config["c2"]
                size = MARKER_SIZE + 10
                num_ot += 1
            else:
                mark = "C"
                color = config["c1"]
                size = MARKER_SIZE
            draw_marker(goal_draw, goal[0], mark, goal_height, size=size, fill=color)
        goal_draw.text((goal_img.width / 2, 8), f"{len(goal_data[name])} total | {num_ot} in OT", 
            fill=DARK_GREY, font=constants.BOUR_60, anchor="ma")
        img.paste(goal_img, (2 * MARGIN, sec_top + 200))
        draw.text(((2 * MARGIN) + (goal_img.width / 2), sec_top + 110), "Goal Placements", fill=BLACK, font=constants.BOUR_80, anchor="ma")

        # Boost pickup map
        boost_width, boost_height = round(constants.MAP_Y) + (MARGIN * 4), round(constants.MAP_X) + (MARGIN * 2)
        boost_img = Image.new(mode="RGBA", size = (boost_width, boost_height), color=WHITE)
        boost_draw = ImageDraw.Draw(boost_img)
        utils.draw_field_lines(boost_draw, MARGIN, boost_height)
        pickup_map, locations = boost_data
        num_small, num_big = 0, 0
        max_pickups = max(pickup_map[name].values())
        for label in locations.keys():
            loc = locations[label]
            loc_x, loc_y = MID_X + loc['pos_y'] / constants.SCALE, MID_Y + loc['pos_x'] / constants.SCALE
            radius = 35 if loc['big'] else 20
            lower = 40 if loc['big'] else 25
            if loc['big']:
                num_big += pickup_map[name][label]
            else:
                num_small += pickup_map[name][label]
            color_str = f"hsl(205, 64%, {100 - (50 * (pickup_map[name][label] / max_pickups))}%)"

            boost_draw.ellipse([
                (loc_x - radius, get_y(loc_y + radius, boost_height)), (loc_x + radius, get_y(loc_y - radius, boost_height))
            ], fill=color_str, outline=DARK_GREY, width=2)
            boost_draw.text((loc_x, get_y(loc_y - lower, boost_height)), str(pickup_map[name][label]), fill=BLACK, font=constants.BOUR_50, anchor="ma")

        boost_left = img.width - boost_img.width - (2 * MARGIN)
        img.paste(boost_img, (boost_left, sec_top + 230))
        draw.text((boost_left + (boost_img.width / 2), sec_top + 110), "Boost Pickups", fill=BLACK, font=constants.BOUR_80, anchor="ma")
        att_len = draw.textlength("Attacking Direction", font=constants.BOUR_60)
        draw.text((boost_left + (boost_img.width / 2) - (att_len / 2), sec_top + 200), "Attacking Direction >>", 
            fill=DARK_GREY, font=constants.BOUR_60)
        draw.text((boost_left + (boost_img.width / 2), sec_top + 230 + boost_img.height - 20), 
            f"{num_big} big pads | {num_small} small pads", fill=DARK_GREY, font=constants.BOUR_60, anchor="ma")

        # Touch results
        touch_center, touch_top = (img.width / 6), sec_top + goal_img.height + 250
        draw.text((touch_center, touch_top), "Touch Results", fill=BLACK, font=constants.BOUR_80, anchor="ma")
        pie_colors = [(50,250,50), (50,50,250), (250,50,50)]
        total = sum(touch_data[name])
        curr_ang = -90
        x_orig, y_orig, radius = touch_center, touch_top + 350, 200
        bbox = [(x_orig - radius, y_orig - radius), (x_orig + radius, y_orig + radius)]
        for j in range(len(touch_data[name])):
            # Pie slice
            pl_val = touch_data[name][j]
            frac = pl_val / total
            deg = (frac * 360)
            draw.pieslice(bbox, curr_ang, curr_ang + deg, fill=pie_colors[j])

            # Slice label
            rad = ((curr_ang + deg + curr_ang) / 2 / 360) * 2 * np.pi 
            if -(np.pi / 2) < rad and rad <= 0:
                x_pad, y_pad = 5, -5
                anc = "ld"
            elif 0 < rad and rad <= (np.pi / 2):
                x_pad, y_pad = 5, 5
                anc = "la"
            elif (np.pi / 2) < rad and rad < np.pi:
                x_pad, y_pad = -5, 5
                anc = "ra"
            else:
                x_pad, y_pad = -5, -5
                anc = "rd"
            point = (x_orig + (radius * np.cos(rad)) + x_pad, y_orig + (radius * np.sin(rad)) + y_pad)
            cat_pct = round(frac * 100, 1)
            if j == 0:
                pie_label = f"{cat_pct}% to Self"
            elif j == 1:
                pie_label = f"{cat_pct}% to Team"
            else:
                pie_label = f"{cat_pct}%\nto Opp."
            draw.text(point, pie_label, fill=DARK_GREY, font=constants.BOUR_60, anchor=anc)
            draw.text((touch_center, y_orig + radius + 30), f"{total} touches", fill=DARK_GREY, font=constants.BOUR_70, anchor="ma")

            curr_ang += deg

        # Goal-preceding demos
        demo_center, demo_top =  (img.width / 2) - 300, touch_top
        draw.text((demo_center, demo_top), "Goal-Preceding\nDemos", fill=BLACK, font=constants.BOUR_80, anchor="ma", align="center")
        draw.text((demo_center, demo_top + 200), str(demo_data[name]), fill=DARK_GREY, font=constants.BOUR_100, anchor="ma")

        sec_top += PL_LAYER_HEIGHT

def create_image(config, team_name, data_path):
    img_width = (2 * round(constants.MAP_X)) + 1200 + (MARGIN * 4)
    img_height = HEADER_HEIGHT + LAYER_1_HEIGHT + LAYER_2_HEIGHT + (3 * PL_LAYER_HEIGHT) + (2 * MARGIN)
    img = Image.new(mode = "RGBA", size = (img_width, img_height), color = WHITE)
    draw = ImageDraw.Draw(img)
    
    stat_data = json.load(open("stats.json", "r"))
    shot_data, goal_data, touch_data, demo_data, boost_data = get_team_data(data_path, config)
    
    draw_header(img, draw, stat_data, config)
    draw_layer_1(img, draw, stat_data, config)
    draw_layer_2(img, draw, stat_data, config, shot_data)
    draw_player_layers(img, draw, config, goal_data, touch_data, demo_data, boost_data)
    
    os.makedirs(config['img_path'], exist_ok=True)
    img.save(os.path.join(config["img_path"], f"{team_name.replace(' ', '_').replace('.', '_')}_v2.png"))

def main():
    key, team_name = "TRUE NEUTRAL", "TRUE NEUTRAL"
    region = "South America"
    base_path = os.path.join("RLCS 24", "Major 1")
    data_path = os.path.join("replays", base_path, region)
    
    config = {
        "logo": constants.TEAM_INFO[team_name]["logo"],
        "t1": team_name,
        "t2": "RMNN | SECK | SHAD | C: CRS",
        "t3": "RLCS 24 MAJOR 1 | TEAM PROFILE",
        "key": key,
        "region": utils.get_region_label(region),
        "seed": 10,
        "points": 15,
        "placements": "12-14th | 5-8th | 9-11th",
        "c1": constants.TEAM_INFO[team_name]["c1"],
        "c2": constants.TEAM_INFO[team_name]["c2"],
        "img_path": os.path.join("viz", "images", base_path, "Profiles", utils.get_region_label(region))
    }
    create_image(config, team_name, data_path)
    
    return 0
  
if __name__ == "__main__":
    main()