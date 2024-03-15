from viz import constants, utils

import numpy as np
import os
from PIL import Image, ImageDraw

IMAGE_X, IMAGE_Y = 2400, 2400
MARGIN = 40

MARKER_SIZE = 20
MID_X, MID_Y = (constants.MAP_Y + (MARGIN * 4)) / 2, (constants.MAP_X + (MARGIN * 2)) / 2

WHITE, BLACK = (255,255,255), (0,0,0)
LIGHT_GREY, DARK_GREY = (140,140,140), (70,70,70)

def get_y(val, img_height):
    return img_height - val

def calculate_hit_maps(game_list):
    map_x, map_y, map_z = constants.MAP_X * constants.SCALE, constants.MAP_Y * constants.SCALE, constants.MAP_Z * constants.SCALE
    ball_height, goal_z = (2 * constants.BALL_RAD), constants.GOAL_Z
    bounds_x = [(map_x / 6, map_x / 2), (-(map_x / 6), map_x / 6), (-(map_x / 2), -(map_x / 6))]
    bounds_y = [(-np.inf, -(map_y / 4)), (-(map_y / 4), 0), (0, map_y / 4), (map_y / 4, np.inf)]
    bounds_z = [(0, ball_height), (ball_height, goal_z), (goal_z, map_z)]
    hit_locs = {"goals": {}, "shots": {}}
    hit_locs_vert = {"goals": {}, "shots": {}}
    totals = {"goals": [[0,0,0,0],[0,0,0,0],[0,0,0,0]], "shots": [[0,0,0,0],[0,0,0,0],[0,0,0,0]]}
    totals_vert = {"goals": [[0,0,0,0],[0,0,0,0],[0,0,0,0]], "shots": [[0,0,0,0],[0,0,0,0],[0,0,0,0]]}
    id_map = {}
    for game in game_list:
        for player in game.players:
            #print(player.name)
            id_map[player.id.id] = player
            name_key = player.name if not player.name.startswith("G2 Stride ") else player.name.replace("G2 Stride ", "")
            if name_key == "BMO":
                name_key = "BeastMode"
            if name_key not in hit_locs['goals']:
                for key in hit_locs.keys():
                    hit_locs[key][name_key] = [
                        [0,0,0,0],
                        [0,0,0,0],
                        [0,0,0,0],
                    ]
                    hit_locs_vert[key][name_key] = [
                        [0,0,0,0],
                        [0,0,0,0],
                        [0,0,0,0]
                    ]
        for hit in [hit for hit in game.game_stats.hits if hit.match_shot or hit.match_goal]:
            player = id_map[hit.player_id.id]
            ball_x = -1 * hit.ball_data.pos_x if player.is_orange else hit.ball_data.pos_x
            ball_y = -1 * hit.ball_data.pos_y if player.is_orange else hit.ball_data.pos_y
            ball_z = hit.ball_data.pos_z
            name_key = player.name if not player.name.startswith("G2 Stride ") else player.name.replace("G2 Stride ", "")
            if name_key == "BMO":
                name_key = "BeastMode"

            for i in range(len(bounds_y)):
                if bounds_y[i][0] <= ball_y and ball_y < bounds_y[i][1]:
                    for j in range(len(bounds_x)):
                        if bounds_x[j][0] <= ball_x and ball_x < bounds_x[j][1]:
                            
                            if hit.match_shot:
                                hit_locs["shots"][name_key][j][i] += 1
                                totals["shots"][j][i] += 1
                            if hit.match_goal:
                                hit_locs["goals"][name_key][j][i] += 1
                                totals["goals"][j][i] += 1
                            break
                    for k in range(len(bounds_z)):
                        if bounds_z[k][0] <= ball_z and ball_z < bounds_z[k][1]:
                            if hit.match_shot:
                                hit_locs_vert["shots"][name_key][k][i] += 1
                                totals_vert["shots"][k][i] += 1
                            if hit.match_goal:
                                hit_locs_vert["goals"][name_key][k][i] += 1
                                totals_vert["goals"][k][i] += 1
                            break
                    break
    
    #print(list(hit_locs["goals"].keys()))
    #print(totals)
    return (hit_locs, hit_locs_vert), (totals, totals_vert)


def draw_main(color_map, text_map):
    width, height = round(constants.MAP_Y) + (MARGIN * 4), round(constants.MAP_X) + (MARGIN * 2)
    img = Image.new(mode="RGBA", size = (width, height), color=WHITE)
    draw = ImageDraw.Draw(img)

    coords_x = [
        (MID_X - (2 * constants.MAP_Y_QUARTER) + 5, MID_X - constants.MAP_Y_QUARTER - 5),
        (MID_X - constants.MAP_Y_QUARTER + 5, MID_X - 5),
        (MID_X + 5, MID_X + constants.MAP_Y_QUARTER - 5),
        (MID_X + constants.MAP_Y_QUARTER + 5, MID_X + (2 * constants.MAP_Y_QUARTER) - 5)
    ]
    coords_y = [
        (get_y(MID_Y + (constants.MAP_X / 2) - 5, height), get_y(MID_Y + (constants.MAP_X / 6) + 5, height)), 
        (get_y(MID_Y + (constants.MAP_X / 6) - 5, height), get_y(MID_Y - (constants.MAP_X / 6) + 5, height)), 
        (get_y(MID_Y - (constants.MAP_X / 6) - 5, height), get_y(MID_Y - (constants.MAP_X / 2) + 5, height))
    ]
    text_x = [
        MID_X - (1.5 * constants.MAP_Y_QUARTER), MID_X - (0.5 * constants.MAP_Y_QUARTER),
        MID_X + (0.5 * constants.MAP_Y_QUARTER), MID_X + (1.5 * constants.MAP_Y_QUARTER)
    ]
    text_y = [get_y(MID_Y + constants.MAP_X_THIRD + 20, height), get_y(MID_Y + 20, height), get_y(MID_Y - constants.MAP_X_THIRD + 20, height)]

    for i in range(len(coords_y)):
        for j in range(len(coords_x)):
            if i == 0 and j == 0:
                draw.polygon([
                    (MID_X - (constants.MAP_Y / 2) + constants.CORNER_SIDE + 2.2, get_y(MID_Y + (constants.MAP_X / 2) - 5, height)), 
                    (MID_X - constants.MAP_Y_QUARTER - 5, get_y(MID_Y + (constants.MAP_X / 2) - 5, height)),
                    (MID_X - constants.MAP_Y_QUARTER - 5, get_y(MID_Y + (constants.MAP_X / 6) + 5, height)),
                    (MID_X - (constants.MAP_Y / 2) + 5, get_y(MID_Y + (constants.MAP_X / 6) + 5, height)),
                    (MID_X - (constants.MAP_Y / 2) + 5, get_y(MID_Y + (constants.MAP_X / 2) - constants.CORNER_SIDE - 2.2, height))
                ], fill=color_map[i][j])
            elif i == 0 and j == 3:
                draw.polygon([
                    (MID_X + (constants.MAP_Y / 2) - constants.CORNER_SIDE - 2.2, get_y(MID_Y + (constants.MAP_X / 2) - 5, height)), 
                    (MID_X + constants.MAP_Y_QUARTER + 5, get_y(MID_Y + (constants.MAP_X / 2) - 5, height)),
                    (MID_X + constants.MAP_Y_QUARTER + 5, get_y(MID_Y + (constants.MAP_X / 6) + 5, height)),
                    (MID_X + (constants.MAP_Y / 2) - 5, get_y(MID_Y + (constants.MAP_X / 6) + 5, height)),
                    (MID_X + (constants.MAP_Y / 2) - 5, get_y(MID_Y + (constants.MAP_X / 2) - constants.CORNER_SIDE - 2.2, height))
                ], fill=color_map[i][j])
            elif i == 2 and j == 0:
                draw.polygon([
                    (MID_X - (constants.MAP_Y / 2) + constants.CORNER_SIDE + 2.2, get_y(MID_Y - (constants.MAP_X / 2) + 5, height)), 
                    (MID_X - constants.MAP_Y_QUARTER - 5, get_y(MID_Y - (constants.MAP_X / 2) + 5, height)),
                    (MID_X - constants.MAP_Y_QUARTER - 5, get_y(MID_Y - (constants.MAP_X / 6) - 5, height)),
                    (MID_X - (constants.MAP_Y / 2) + 5, get_y(MID_Y - (constants.MAP_X / 6) - 5, height)),
                    (MID_X - (constants.MAP_Y / 2) + 5, get_y(MID_Y - (constants.MAP_X / 2) + constants.CORNER_SIDE + 2, height))
                ], fill=color_map[i][j])
            elif i == 2 and j == 3:
                draw.polygon([
                    (MID_X + (constants.MAP_Y / 2) - constants.CORNER_SIDE - 2.2, get_y(MID_Y - (constants.MAP_X / 2) + 5, height)), 
                    (MID_X + constants.MAP_Y_QUARTER + 5, get_y(MID_Y - (constants.MAP_X / 2) + 5, height)),
                    (MID_X + constants.MAP_Y_QUARTER + 5, get_y(MID_Y - (constants.MAP_X / 6) - 5, height)),
                    (MID_X + (constants.MAP_Y / 2) - 5, get_y(MID_Y - (constants.MAP_X / 6) - 5, height)),
                    (MID_X + (constants.MAP_Y / 2) - 5, get_y(MID_Y - (constants.MAP_X / 2) + constants.CORNER_SIDE + 2, height))
                ], fill=color_map[2][3])
            else:
                draw.rectangle([(coords_x[j][0], coords_y[i][0]), (coords_x[j][1], coords_y[i][1])], fill=color_map[i][j])
            draw.multiline_text((text_x[j] - (text_map[i][j]["len"] / 2), text_y[i] - 15), text_map[i][j]["text"], 
                fill=BLACK, font=constants.BOUR_40, align="center")

    utils.draw_field_lines(draw, MARGIN, height, sections=True)
    return img

def draw_vert(color_map, text_map):
    width, height = round(constants.MAP_Y) + (MARGIN * 4), round(constants.MAP_Z) + (MARGIN * 2) + 15
    img = Image.new(mode="RGBA", size = (width, height), color=WHITE)
    draw = ImageDraw.Draw(img)

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
    text_y = [get_y(45, height), get_y(((goal_height + ball_height) / 2) + 20, height), get_y(((field_height + goal_height) / 2) + 20, height)]

    for i in range(len(coords_y)):
        for j in range(len(coords_x)):
            draw.rectangle([(coords_x[j][0], coords_y[i][0]), (coords_x[j][1], coords_y[i][1])], fill=color_map[i][j])
            draw.text((text_x[j] - (text_map[i][j]["len"] / 2), text_y[i]), text_map[i][j]["text"], fill=BLACK, font=constants.BOUR_40)
    
    utils.draw_field_lines_vert(draw, MARGIN, height, sections=True)
    return img

def draw_field(base_draw, game_list, player_name):
    hit_locs, totals = calculate_hit_maps(game_list)
    player_pcts = (
        np.array(hit_locs[0]['goals'][player_name]) / np.array(hit_locs[0]['shots'][player_name]), 
        np.array(hit_locs[1]['goals'][player_name]) / np.array(hit_locs[1]['shots'][player_name])
    )
    total_pcts = (
        np.array(totals[0]['goals']) / np.array(totals[0]['shots']),
        np.array(totals[1]['goals']) / np.array(totals[1]['shots'])
    )
    diffs = (100 * (player_pcts[0] - total_pcts[0]), 100 * (player_pcts[1] - total_pcts[1]))

    color_maps = ([], [])
    text_maps = ([], [])
    for idx in range(len(diffs)):
        diff = diffs[idx]
        for i in range(len(diff)):
            row = diff[i]
            color_list = []
            text_list = []
            for j in range(len(row)):
                val = row[j]
                if np.isnan(val):
                    color_str = (200,200,200)
                elif val == 0:
                    color_str = "hsl(0, 0%, 100%)"
                elif abs(val) < 5:
                    if val > 0:
                        color_str = "hsl(115, 100%, 95%)"
                    else:
                        color_str = "hsl(10, 100%, 95%)"
                elif abs(val) < 15:
                    if val > 0:
                        color_str = "hsl(115, 100%, 72%)"
                    else:
                        color_str = "hsl(10, 100%, 72%)"
                else:
                    if val > 0:
                        color_str = "hsl(115, 100%, 50%)"
                    else:
                        color_str = "hsl(10, 100%, 50%)"
                color_list.append(color_str)

                pct_map = player_pcts[idx]
                if idx == 0:
                    text = "N/A" if np.isnan(pct_map[i][j]) else "{:.1f}%\n({:d}/{:d})"\
                        .format(100 * pct_map[i][j], hit_locs[idx]["goals"][player_name][i][j], hit_locs[idx]["shots"][player_name][i][j])
                else:    
                    text = "N/A" if np.isnan(pct_map[i][j]) else "{:.1f}% ({:d}/{:d})"\
                        .format(100 * pct_map[i][j], hit_locs[idx]["goals"][player_name][i][j], hit_locs[idx]["shots"][player_name][i][j])
                text_len = base_draw.textlength(text.split('\n')[0], font=constants.BOUR_40)
                text_list.append({"text": text, "len": text_len})
            color_maps[idx].append(color_list)
            text_maps[idx].append(text_list)

    img_main = draw_main(color_maps[0], text_maps[0])
    img_vert = draw_vert(color_maps[1], text_maps[1])

    return img_main, img_vert


def create_image(player_name, game_list, config):
    img = Image.new(mode = "RGBA", size = (IMAGE_X, IMAGE_Y), color = WHITE)
    draw = ImageDraw.Draw(img)
    
    # Logo in top left
    logo_width, _ = utils.draw_team_logo(img, MARGIN, config["logo"])

    # Title text
    utils.draw_title_text(draw, logo_width, MARGIN, config, constants.BOUR_80, constants.BOUR_40)

    # Main field image
    img_main, img_vert = draw_field(draw, game_list, player_name)
    field_left = round((IMAGE_X / 2) - (img_main.width / 2))
    field_right = round((IMAGE_X / 2) + (img_main.width / 2))
    img.paste(img_vert, (field_left, get_y(img_vert.height + (2 * MARGIN), IMAGE_Y)))
    img.paste(img_main, (field_left, get_y(img_vert.height + img_main.height + 150 + (2 * MARGIN), IMAGE_Y)))

    # Direction text
    attack_text = "Attacking Direction"
    attack_len = draw.textlength(attack_text, font=constants.BOUR_50)
    draw.text(((IMAGE_X - attack_len) / 2, get_y(img_vert.height + img_main.height + 150 + (2.5 * MARGIN), IMAGE_Y)), 
        f"{attack_text} >>", fill=DARK_GREY, font=constants.BOUR_50)
    
    # Comparison legend
    comp_text = "SH% vs Event Average"
    comp_len = draw.textlength(comp_text, font=constants.BOUR_50)
    draw.text(((IMAGE_X - comp_len) / 2, get_y(img_vert.height + (6 * MARGIN), IMAGE_Y)), 
        comp_text, fill=DARK_GREY, font=constants.BOUR_50)
    pct_text = ["-15", " -5", "0", "+5", "+15",""]
    for i in range(len(pct_text)):
        pct_len = draw.textlength(pct_text[i], font=constants.BOUR_40)
        draw.text((((IMAGE_X - pct_len) / 2) + ((i - 2) * 150), get_y(img_vert.height + (3.5 * MARGIN), IMAGE_Y)), 
            pct_text[i], fill=BLACK, font=constants.BOUR_40)
    draw.rectangle([
        (((IMAGE_X - pct_len) / 2) + ((0 - 2) * 150) - (2.5 * MARGIN), get_y(img_vert.height + (4 * MARGIN), IMAGE_Y)), 
        (((IMAGE_X - pct_len) / 2) + ((0 - 2) * 150) - (1 * MARGIN), get_y(img_vert.height + (2 * MARGIN), IMAGE_Y))
    ], fill="hsl(10, 100%, 50%)")
    draw.rectangle([
        (((IMAGE_X - pct_len) / 2) + ((1 - 2) * 150) - (2.5 * MARGIN), get_y(img_vert.height + (4 * MARGIN), IMAGE_Y)), 
        (((IMAGE_X - pct_len) / 2) + ((1 - 2) * 150) - (1 * MARGIN), get_y(img_vert.height + (2 * MARGIN), IMAGE_Y))
    ], fill="hsl(10, 100%, 72%)")
    draw.rectangle([
        (((IMAGE_X - pct_len) / 2) + ((2 - 2) * 150) - (2.5 * MARGIN), get_y(img_vert.height + (4 * MARGIN), IMAGE_Y)), 
        (((IMAGE_X - pct_len) / 2) + ((2 - 2) * 150) - (1 * MARGIN), get_y(img_vert.height + (2 * MARGIN), IMAGE_Y))
    ], fill="hsl(10, 100%, 95%)")
    draw.rectangle([
        (((IMAGE_X - pct_len) / 2) + ((3 - 2) * 150) - (2.75 * MARGIN), get_y(img_vert.height + (4 * MARGIN), IMAGE_Y)), 
        (((IMAGE_X - pct_len) / 2) + ((3 - 2) * 150) - (1.25 * MARGIN), get_y(img_vert.height + (2 * MARGIN), IMAGE_Y))
    ], fill="hsl(115, 100%, 95%)")
    draw.rectangle([
        (((IMAGE_X - pct_len) / 2) + ((4 - 2) * 150) - (2.75 * MARGIN), get_y(img_vert.height + (4 * MARGIN), IMAGE_Y)), 
        (((IMAGE_X - pct_len) / 2) + ((4 - 2) * 150) - (1.25 * MARGIN), get_y(img_vert.height + (2 * MARGIN), IMAGE_Y))
    ], fill="hsl(115, 100%, 72%)")
    draw.rectangle([
        (((IMAGE_X - pct_len) / 2) + ((5 - 2) * 150) - (2.75 * MARGIN), get_y(img_vert.height + (4 * MARGIN), IMAGE_Y)), 
        (((IMAGE_X - pct_len) / 2) + ((5 - 2) * 150) - (1.25 * MARGIN), get_y(img_vert.height + (2 * MARGIN), IMAGE_Y))
    ], fill="hsl(115, 100%, 50%)")

    # Dotted circle logo
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    
    img.save(os.path.join("viz", "images", config["img_name"]))

def main():
    player_name = "Daniel"
    key = "SOLO Q"
    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": "DANIEL",
        "t2": "SOLO Q | LAN",
        "t3": "",
        "c1": constants.TEAM_INFO[key]["c1"],
        "c2": constants.TEAM_INFO[key]["c2"],
        "img_name": os.path.join("Solo Q", "shooting_comp", "daniel_shooting_comp_lan.png")
    }

    data_path = os.path.join("replays", "Solo Q", "LAN")
    game_list = utils.read_group_data(data_path)
    create_image(player_name, game_list, config)
    
    return 1
  
if __name__ == "__main__":
    main()