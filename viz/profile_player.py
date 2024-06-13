from viz import constants, utils

import json
import numpy as np
import os
from PIL import Image, ImageDraw
from pilmoji import Pilmoji
from scipy.stats import percentileofscore

MARGIN = 40

MARKER_SIZE = 10

WHITE, BLACK = (255,255,255), (0,0,0)
LIGHT_GREY, DARK_GREY = (180,180,180), (70,70,70)

COL_1_WIDTH = constants.GOAL_X + (4 * MARGIN)
COL_2_WIDTH = 2100
COL_3_WIDTH = 1750

HEADER_HEIGHT = 350
SCOREBOARD_HEIGHT = 500

def get_y(val, img_height):
    return img_height - val

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
    draw.text((logo_width + 50 + MARGIN, MARGIN), config["t1"].upper(), fill=(0,0,0), font=font_one)
    draw.text((logo_width + 50 + MARGIN, 100 + MARGIN), config["t2"], fill=(70,70,70), font=font_two)
    draw.text((logo_width + 50 + MARGIN, 170 + MARGIN), config["t3"], fill=(70,70,70), font=font_two)

    # Dotted circle logo
    utils.draw_dotted_circle(draw, img.width, MARGIN, config["c1"], config["c2"])

def calculate_hit_data(data_path, player_name):
    map_x, map_y, map_z = constants.MAP_X * constants.SCALE, constants.MAP_Y * constants.SCALE, constants.MAP_Z * constants.SCALE
    ball_height, goal_z = (2 * constants.BALL_RAD), constants.GOAL_Z
    bounds_x = [(map_x / 6, map_x / 2), (-(map_x / 6), map_x / 6), (-(map_x / 2), -(map_x / 6))]
    bounds_y = [(-np.inf, -(map_y / 4)), (-(map_y / 4), 0), (0, map_y / 4), (map_y / 4, np.inf)]
    bounds_z = [(0, ball_height), (ball_height, goal_z), (goal_z, map_z)]
    
    totals = [[0,0,0,0],[0,0,0,0],[0,0,0,0]]
    totals_vert = [[0,0,0,0],[0,0,0,0],[0,0,0,0]]
    goal_data = []

    game_list = utils.read_group_data(data_path)
    for game in game_list:
        player_id = ""
        for player in game.players:
            if utils.get_player_label(player.name) == player_name:
                player_id = player.id.id
                break
            
        for hit in [hit for hit in game.game_stats.hits if hit.player_id.id == player_id]:
            ball_x = -1 * hit.ball_data.pos_x if player.is_orange else hit.ball_data.pos_x
            ball_y = -1 * hit.ball_data.pos_y if player.is_orange else hit.ball_data.pos_y
            ball_z = hit.ball_data.pos_z
            for i in range(len(bounds_y)):
                if bounds_y[i][0] <= ball_y and ball_y < bounds_y[i][1]:
                    for j in range(len(bounds_x)):
                        if bounds_x[j][0] <= ball_x and ball_x < bounds_x[j][1]:
                            totals[j][i] += 1
                            break
                    for k in range(len(bounds_z)):
                        if bounds_z[k][0] <= ball_z and ball_z < bounds_z[k][1]:
                            totals_vert[k][i] += 1
                            break
                    break
        
        for goal in [goal for goal in game.game_metadata.goals if goal.player_id.id == player_id]:
            goal_data.append((goal.ball_pos, goal.seconds_remaining < 0))
    
    return (totals, totals_vert), goal_data

def draw_main(color_map, text_map):
    width, height = round(constants.MAP_Y) + (MARGIN * 4), round(constants.MAP_X) + (MARGIN * 2)
    img = Image.new(mode="RGBA", size = (width, height), color=WHITE)
    draw = ImageDraw.Draw(img)

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
            draw.multiline_text((text_x[j] - (text_map[i][j]["len"] / 2), text_y[i] - 15), text_map[i][j]["text"], 
                fill=BLACK, font=constants.BOUR_50, align="center")

    utils.draw_field_lines(draw, MARGIN, height, sections=True)
    return img

def draw_vert(color_map, text_map):
    width, height = round(constants.MAP_Y) + (MARGIN * 4), round(constants.MAP_Z) + (MARGIN * 2) + 15
    img = Image.new(mode="RGBA", size = (width, height), color=WHITE)
    draw = ImageDraw.Draw(img)

    MID_X  = (constants.MAP_Y + (MARGIN * 4)) / 2
    margin_y = MARGIN + 15
    field_height = constants.MAP_Z + margin_y
    goal_height = (constants.GOAL_Z / constants.SCALE) + margin_y
    ball_height = (2 * (constants.BALL_RAD / constants.SCALE)) + margin_y
    coords_x = [
        (MID_X - (constants.MAP_Y / 2) + 5, MID_X - constants.MAP_Y_QUARTER - 5),
        (MID_X - constants.MAP_Y_QUARTER + 5, MID_X - 5),
        (MID_X + 5, MID_X + constants.MAP_Y_QUARTER - 5),
        (MID_X + constants.MAP_Y_QUARTER + 5, MID_X + (constants.MAP_Y / 2) - 5)
    ]
    coords_y = [
        (get_y(ball_height - 5, height), get_y(margin_y + 5, height)), 
        (get_y(goal_height - 5, height), get_y(ball_height + 5, height)), 
        (get_y(field_height - 5, height), get_y(goal_height + 5, height))
    ]
    text_x = [
        MID_X - (1.5 * constants.MAP_Y_QUARTER), MID_X - (0.5 * constants.MAP_Y_QUARTER), 
        MID_X + (0.5 * constants.MAP_Y_QUARTER), MID_X + (1.5 * constants.MAP_Y_QUARTER)
    ]
    text_y = [get_y(45, height), get_y(((goal_height + ball_height) / 2) + 23, height), get_y(((field_height + goal_height) / 2) + 20, height)]

    for i in range(len(coords_y)):
        for j in range(len(coords_x)):
            draw.rectangle([(coords_x[j][0], coords_y[i][0]), (coords_x[j][1], coords_y[i][1])], fill=color_map[i][j])
            draw.text((text_x[j] - (text_map[i][j]["len"] / 2), text_y[i]), text_map[i][j]["text"], fill=BLACK, font=constants.BOUR_50)

    utils.draw_field_lines_vert(draw, MARGIN, height, sections=True)
    return img

def draw_fields(base_draw, hit_data):
    total_pcts = (
        np.array(hit_data[0]) / np.sum(hit_data[0]),
        np.array(hit_data[1]) / np.sum(hit_data[1])
    )
    max_pcts = [np.nanmax(total_pcts[0]), np.nanmax(total_pcts[1])]
    min_pcts = [np.nanmin(total_pcts[0]), np.nanmin(total_pcts[1])]
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
                    color_str = color_str.format(25 + (70 * (min_pcts[idx] / val)))
                color_list.append(color_str)

                pct_map = total_pcts[idx]
                if idx == 0:
                    text = "N/A" if np.isnan(pct_map[i][j]) else "{:.1f}%\n({:d})"\
                        .format(100 * pct_map[i][j], hit_data[idx][i][j])
                else:    
                    text = "N/A" if np.isnan(pct_map[i][j]) else "{:.1f}% ({:d})"\
                        .format(100 * pct_map[i][j], hit_data[idx][i][j])
                text_len = max(base_draw.textlength(lbl_part, font=constants.BOUR_50) for lbl_part in text.split('\n'))
                text_list.append({"text": text, "len": text_len})
            color_maps[idx].append(color_list)
            text_maps[idx].append(text_list)

    return draw_main(color_maps[0], text_maps[0]), draw_vert(color_maps[1], text_maps[1])

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

def draw_goal(goal_data, config):
    width, height = constants.GOAL_X + (MARGIN * 4), round(constants.GOAL_Z - 80) + (MARGIN * 2)
    img = Image.new(mode="RGBA", size = (width, height), color=WHITE)
    draw = ImageDraw.Draw(img)
    
    for goal in goal_data:
        if goal[1]:
            mark = "S"
            color = config["c2"]
            size = MARKER_SIZE + 10
        else:
            mark = "C"
            color = config["c1"]
            size = MARKER_SIZE
        draw_marker(draw, goal[0], mark, height, size=size, fill=color)

    utils.draw_goal_lines(draw, MARGIN, height)
    return img

def get_p5_val(stat_data, name, category, stat):
    return stat_data[name][category][stat] / (stat_data[name]["secs"] / 300)

def get_rot_text(draw, text, font=constants.BOUR_60, height=50, fill=BLACK, rot=90):
    img_len = round(draw.textlength(text, font=font))
    img = Image.new(mode="RGB", size=(img_len, height), color=WHITE)
    img_draw = ImageDraw.Draw(img)
    img_draw.text((0, 0), text, fill=fill, font=font)
    return img.rotate(rot, expand=True), img_len

def draw_column_1(img: Image.Image, draw: ImageDraw.ImageDraw, stat_data, config, data_path):
    col_left, col_mid = 2 * MARGIN, ((2 * MARGIN) + (COL_1_WIDTH + MARGIN)) / 2
    col_top = HEADER_HEIGHT

    # IRL player info
    draw.text((col_mid, col_top), "Player Info", fill=BLACK, font=constants.BOUR_90, anchor="ma")
    info_top, info_step = col_top + 140, 225
    with Image.open(os.path.join("viz", "images", "Players", config["t1"] + ".jpg")) as pl_img:
        prof_img = pl_img.resize((650, 650))
        img.paste(prof_img, (col_left + (4 * MARGIN), info_top + 15))

    info_headers = ["Name", "Country", "Age"]
    info_vals = [config["name"], config["nation"], config["age"]]
    text_left = col_left + (5 * MARGIN) + 750
    for i in range(len(info_headers)):
        sec_top = info_top + (i * info_step) + 15
        draw.text((text_left, sec_top), info_headers[i], fill=DARK_GREY, font=constants.BOUR_70, anchor="la")
        if i == 1:
            with Pilmoji(img) as pmj:
               w, h = pmj.getsize(info_vals[i], font=constants.BOUR_80)
               pmj.text((text_left, sec_top + 80), info_vals[i], fill=BLACK, font=constants.BOUR_80)
        else:
            draw.text((text_left, sec_top + 80), str(info_vals[i]), fill=BLACK, font=constants.BOUR_80, anchor="la")

    draw.rounded_rectangle([(col_left + (2 * MARGIN), info_top - 10), (col_left + COL_1_WIDTH - (3 * MARGIN), sec_top + info_step + 10)], 
        75, outline=constants.REGION_COLORS[config["region"]][0], width=5)

    # Touch map
    map_top = sec_top + info_step + (2 * MARGIN)
    draw.text((col_mid, map_top), "Touch Map", fill=BLACK, font=constants.BOUR_90, anchor="ma")

    hit_totals, goal_data = calculate_hit_data(data_path, config["t1"])
    img_main, img_vert = draw_fields(draw, hit_totals)
    field_left = round(col_mid - (img_main.width / 2))
    main_top, vert_top = map_top + 140, map_top + 150 + img_main.height + (2 * MARGIN)
    img.paste(img_main, (field_left, main_top))
    img.paste(img_vert, (field_left, vert_top))

    dir_len = draw.textlength("Attacking Direction", font=constants.BOUR_50)
    draw.text((col_mid - (dir_len / 2), map_top + 120), "Attacking Direction >>", fill=DARK_GREY, font=constants.BOUR_50)
    touch_data = stat_data[config["t1"]]["touch"]
    draw.text((col_mid, main_top + img_main.height + 12),
        "{} total | {} to self | {} to teammate | {} to opponent".format(touch_data["total"], touch_data["self"], touch_data["team"], touch_data["oppo"]),
        fill=DARK_GREY, font=constants.BOUR_60, anchor="ma"
    )

    # Goal placements
    placement_top = vert_top + img_vert.height + (3 * MARGIN)
    img_goal = draw_goal(goal_data, config)
    goal_left = round(col_mid - (img_goal.width / 2))
    img.paste(img_goal, (goal_left, placement_top + 150))

    num_total, num_ot = len(goal_data), len([goal for goal in goal_data if goal[1]])
    draw.text((col_mid, placement_top), "Goal Placement", fill=BLACK, font=constants.BOUR_90, anchor="ma")
    draw.text((col_mid, placement_top + 130), f"{num_total} total | {num_ot} in OT", fill=DARK_GREY, font=constants.BOUR_70, anchor="ma")

def draw_column_2(img: Image.Image, draw: ImageDraw.ImageDraw, stat_data, config):
    col_mid = (COL_1_WIDTH + (COL_1_WIDTH + COL_2_WIDTH)) / 2
    col_top = HEADER_HEIGHT
    
    # Scoreboard stats
    sb_left, sb_right = COL_1_WIDTH + (2 * MARGIN), COL_1_WIDTH + COL_2_WIDTH + (3 * MARGIN)
    sb_height = 1100
    header_top = col_top + 140
    val_top, pct_top = header_top + 120, header_top + 300
    draw.text((col_mid, col_top), "Scoreboard", fill=BLACK, font=constants.BOUR_90, anchor="ma")

    sb_headers = [
        "score", "goals", "assists", "saves", "shots",
        "touches", "xG", "passes", "demos", "steals"    
    ]
    for i in range(len(sb_headers)):
        stat_col = i + 1 if i < 5  else i - 4
        y_offset = 0 if i < 5 else 490
        stat_x = stat_col * ((sb_right - sb_left) / 6)
        draw.text((sb_left + stat_x, header_top + y_offset), sb_headers[i].upper(), fill=DARK_GREY, font=constants.BOUR_60, anchor="ma")
        
        stat_val = get_p5_val(stat_data, config["t1"], "sb", sb_headers[i])
        if stat_val > 100:
            stat_str = "{:.1f}"
        elif stat_val > 10:
            stat_str = "{:.2f}"
        else:
            stat_str = "{:.3f}"
        dataset = [get_p5_val(stat_data, pl_name, "sb", sb_headers[i]) for pl_name in stat_data]
        pctile = round(percentileofscore(dataset, stat_val), 1)
        draw.text((sb_left + stat_x, val_top + y_offset), stat_str.format(stat_val), fill=BLACK, font=constants.BOUR_90, anchor="ma")
        draw.text((sb_left + stat_x, pct_top + y_offset), "{}".format(pctile), fill=BLACK, font=constants.BOUR_90, anchor="ma")

        if i == 0 or i == 5:
            rect_color = constants.TEAM_INFO["RLCS"]["c1"] if i == 0 else constants.TEAM_INFO["RLCS"]["c2"]
            draw.rectangle([(sb_left, val_top - 20 + y_offset), (sb_right - (4 * MARGIN), val_top + 110 + y_offset)], 
                outline=rect_color, width=5)
            draw.rectangle([(sb_left, pct_top - 20 + y_offset), (sb_right - (4 * MARGIN), pct_top + 110 + y_offset)], 
                outline=rect_color, width=5)

            draw.multiline_text((sb_left + (4 * MARGIN), val_top - 3 + y_offset), "Per\n5:00", fill=DARK_GREY, font=constants.BOUR_50, anchor="ra", align="right")
            draw.text((sb_left + (4 * MARGIN), pct_top + 23 + y_offset), "%-ile", fill=DARK_GREY, font=constants.BOUR_50, anchor="ra")
    
    # Game State
    goal_data, save_data = stat_data[config["t1"]]["goal_state"], stat_data[config["t1"]]["save_state"]
    state_top = col_top + sb_height + (2 * MARGIN)
    chart_mid = col_mid
    if max(save_data.values()) > 70:
        chart_mid -= 30 * int((max(save_data.values()) - 70) / 2)

    draw.text((col_mid, state_top), "Game State", fill=BLACK, font=constants.BOUR_90, anchor="ma")
    draw.text((chart_mid - 310, state_top + 120), "Goals", fill=DARK_GREY, font=constants.BOUR_80, anchor="ma")
    draw.text((chart_mid + 310, state_top + 120), "Saves", fill=DARK_GREY, font=constants.BOUR_80, anchor="ma")

    chart_top, chart_step = state_top + 350, 240
    item_width, item_step = 18, 28
    for i in range(4, -5, -1):
        bar_mid = chart_top + ((4 - i) * chart_step)
        if i <= 0:
            bar_mid += 150
        if i < 0:
            bar_mid += 150
        if i == -4:
            lbl = "-4+"
        elif i == 4:
            lbl = "4+"
        else:
            lbl = str(i)
        draw.text((chart_mid, bar_mid), lbl, fill=BLACK, font=constants.BOUR_70, anchor="mm")

        goal_right, save_left = chart_mid - 70, chart_mid + 70
        bar_offset, bar_half = 45, 40
        for j in range(goal_data[str(i)]):
            bar_right = goal_right - (item_step * (j // 2))
            bar_y = bar_mid - bar_offset if j % 2 == 1 else bar_mid + bar_offset
            draw.rectangle([(bar_right - item_width, bar_y - bar_half), (bar_right, bar_y + bar_half)],
                fill=config["c1"])
            if j > 0 and (j + 1) % 10 == 0:
                draw.line([(bar_right - item_width - 5, bar_y - 70), (bar_right - item_width - 5, bar_y - 50)], 
                    fill=LIGHT_GREY, width=5)
        
        for j in range(save_data[str(i)]):
            bar_left = save_left + (item_step * (j // 2))
            bar_y = bar_mid - bar_offset if j % 2 == 1 else bar_mid + bar_offset
            draw.rectangle([(bar_left, bar_y - bar_half), (bar_left + item_width, bar_y + bar_half)],
                fill=config["c2"])
            if j > 0 and (j + 1) % 10 == 0:
                draw.line([(bar_left + item_width + 5, bar_y - 70), (bar_left + item_width + 5, bar_y - 50)], 
                    fill=LIGHT_GREY, width=5)

        if i == 0:
            win_y = bar_mid - bar_offset - (2 * bar_half) - MARGIN
            draw.line([(chart_mid - 200, win_y), (chart_mid + 200, win_y)], fill=LIGHT_GREY, width=5)
            draw.text((chart_mid, win_y - 10), "Winning", fill=DARK_GREY, font=constants.BOUR_70, anchor="md")
            lose_y = bar_mid + bar_offset + (2 * bar_half) + MARGIN
            draw.line([(chart_mid - 200, lose_y), (chart_mid + 200, lose_y)], fill=LIGHT_GREY, width=5)
            draw.text((chart_mid, lose_y + 10), "Losing", fill=DARK_GREY, font=constants.BOUR_70, anchor="ma")
        
def draw_tend_sect(draw, top, left, right, step, headers, vals, colors, boost=False):
    mid = (left + right) / 2
    width = right - left
    for i in range(len(headers)):
        tend_top = top + (i * step)
        draw.text((mid, tend_top), headers[i][0], fill=DARK_GREY, font=constants.BOUR_80, anchor="ma")
        
        bar_mid, bar_half = tend_top + 205 if boost and i == 2 else tend_top + 215, 40
        curr_left = left
        tend_data = vals[i]
        for j in range(len(tend_data)):
            sect_pct = (tend_data[j] / 100) if boost and i == 2 else tend_data[j] / sum(tend_data) 
            sect_width = sect_pct * width
            draw.rectangle([(curr_left, bar_mid - bar_half), (curr_left + sect_width, bar_mid + bar_half)], fill=colors[j])
            if boost and i == 2:
                draw.text((curr_left + sect_width + 20, bar_mid), "{:.1f}".format(sect_pct * 100), fill=BLACK, font=constants.BOUR_60, anchor="lm")
            else:
                draw.text((curr_left + (sect_width / 2), bar_mid - bar_half - 5), headers[i][1][j], fill=BLACK, font=constants.BOUR_60, anchor="md", align="center")
                draw.text((curr_left + (sect_width / 2), bar_mid + bar_half + 5), " {:.1f}%".format(sect_pct * 100), fill=BLACK, font=constants.BOUR_60, anchor="ma")
            curr_left += sect_width

def draw_column_3(img: Image.Image, draw: ImageDraw.ImageDraw, stat_data, config):
    col_left, col_mid = COL_1_WIDTH + COL_2_WIDTH + (2 * MARGIN), COL_1_WIDTH + COL_2_WIDTH + (COL_3_WIDTH / 2) + MARGIN
    col_top, step, sect_height = HEADER_HEIGHT, 400, (3 * 425)
    bar_left, bar_right = col_left + (2 * MARGIN), col_left + COL_3_WIDTH - (3 * MARGIN)
    tend_colors = [(50,250,50), (50,50,250), (250,50,50)]
    
    draw.text((col_mid, col_top), "Tendencies", fill=BLACK, font=constants.BOUR_90, anchor="ma")

    boost_data = stat_data[config["t1"]]["boost"]
    boost_headers = [
        ("Pad Collection", ["Small Pads", "Big Pads"]), 
        ("Boost Level", ["0-33", "34-66", "67-100"]), 
        ("First Touch Average Boost", [])
        ]
    boost_vals = [
        [boost_data["small_pads"], boost_data["big_pads"]],
        [boost_data["time_low"], boost_data["time_mid"], boost_data["time_high"]],
        [boost_data["first_touch_boost"]]
    ]
    boost_top = col_top + 150
    rect_top, rect_bot = boost_top - 20, boost_top + sect_height - (3 * MARGIN)
    draw_tend_sect(draw, boost_top, bar_left, bar_right, step, boost_headers, boost_vals, tend_colors, boost=True)
    draw.rounded_rectangle([(bar_left - MARGIN, rect_top), (bar_right + MARGIN, rect_bot)], 
        75, outline=config["c1"], width=5)
    boost_img, boost_height = get_rot_text(draw, "Boost", font=constants.BOUR_90, height=70, fill=BLACK)
    img.paste(boost_img, (round(col_left - (1.5 * MARGIN)), round(((rect_top + rect_bot) / 2) - (boost_height / 2))))

    mvmt_data = stat_data[config["t1"]]["mvmt"]
    mvmt_headers = [
        ("Speed", ["Slow", "Boost", "Supersonic"]), 
        ("Demos", ["Inflicted", "Taken"]), 
        ("Height", ["Ground", "Low Air", "Above\nCrossbar"])
        ]
    mvmt_vals = [
        [mvmt_data["time_slow"], mvmt_data["time_boost"], mvmt_data["time_supersonic"]],
        [mvmt_data["demos_inflicted"], mvmt_data["demos_taken"]],
        [mvmt_data["time_ground"], mvmt_data["time_low_air"], mvmt_data["time_high_air"]]
    ]
    mvmt_top = boost_top + sect_height
    rect_top, rect_bot = mvmt_top - 20, mvmt_top + sect_height - (3 * MARGIN)
    draw_tend_sect(draw, mvmt_top, bar_left, bar_right, step, mvmt_headers, mvmt_vals, tend_colors)
    draw.rounded_rectangle([(bar_left - MARGIN, mvmt_top - 20), (bar_right + MARGIN, mvmt_top + sect_height - (3 * MARGIN))], 
        75, outline=config["c2"], width=5)
    mvmt_img, mvmt_height = get_rot_text(draw, "Movement", font=constants.BOUR_90, height=70, fill=BLACK)
    img.paste(mvmt_img, (round(col_left - (1.5 * MARGIN)), round(((rect_top + rect_bot) / 2) - (mvmt_height / 2))))

    pos_data = stat_data[config["t1"]]["pos"]
    pos_headers = [
        ("Team", ["Most Back", "Middle Player", "Most Forward"]), 
        ("Ball", ["Behind", "Ahead"]), 
        ("Field", ["Def. Third", "Mid. Third", "Att. Third"])
        ]
    pos_vals = [
        [pos_data["time_most_back"], pos_data["time_middle"], pos_data["time_most_forward"]],
        [pos_data["time_behind_ball"], pos_data["time_ahead_ball"]],
        [pos_data["time_def"], pos_data["time_neutral"], pos_data["time_att"]]
    ]
    pos_top = mvmt_top + sect_height
    rect_top, rect_bot = pos_top - 20, pos_top + sect_height - (3 * MARGIN)
    draw_tend_sect(draw, pos_top, bar_left, bar_right, step, pos_headers, pos_vals, tend_colors)
    draw.rounded_rectangle([(bar_left - MARGIN, pos_top - 20), (bar_right + MARGIN, pos_top + sect_height - (3 * MARGIN))], 
        75, outline=config["c1"], width=5)
    pos_img, pos_height = get_rot_text(draw, "Positioning", font=constants.BOUR_90, height=90, fill=BLACK)
    img.paste(pos_img, (round(col_left - (1.5 * MARGIN)), round(((rect_top + rect_bot) / 2) - (pos_height / 2))))

def create_image(config, player_name, data_path):
    img_width = COL_1_WIDTH + COL_2_WIDTH + COL_3_WIDTH + (2 * MARGIN)
    img_height = HEADER_HEIGHT + 100 + 3 * ((3 * 425)) + (2 * MARGIN)
    img = Image.new(mode = "RGBA", size = (round(img_width), img_height), color = WHITE)
    draw = ImageDraw.Draw(img)

    stat_data = json.load(open("player_stats.json", "r"))
    draw_header(img, draw, stat_data, config)
    draw_column_1(img, draw, stat_data, config, data_path)
    draw_column_2(img, draw, stat_data, config)
    draw_column_3(img, draw, stat_data, config)

    os.makedirs(config['img_path'], exist_ok=True)
    img.save(os.path.join(config["img_path"], f"{player_name.replace('.', '')}.png"))


def main():
    team_name = "TEAM BDS"
    player_name = "M0nkey M00n"
    region = "Europe"
    base_path = os.path.join("RLCS 24", "Major 2")
    data_path = os.path.join("replays", base_path, region)
    
    config = {
        "logo": constants.TEAM_INFO[team_name]["logo"],
        "t1": player_name,
        "t2": team_name,
        "t3": "RLCS 24 MAJOR 2 | PLAYER PROFILE",
        "region": utils.get_region_label(region),
        "name": "Evan Rogez",
        "nation": "🇫🇷 France",
        "age": 21,
        "c1": constants.TEAM_INFO[team_name]["c1"],
        "c2": constants.TEAM_INFO[team_name]["c2"],
        "img_path": os.path.join("viz", "images", base_path, "Profiles", utils.get_region_label(region), team_name)
    }
    create_image(config, player_name, data_path)
    
    return 0
  
if __name__ == "__main__":
    main()