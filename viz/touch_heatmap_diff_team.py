from viz import constants, utils

import numpy as np
import os
from PIL import Image, ImageDraw, ImageFont

IMAGE_X, IMAGE_Y = 2400, 2250
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
    hit_locs, hit_locs_vert = {}, {}
    id_map = {}
    for game in game_list:
        if len(id_map.keys()) == 0:
            for player in game.players:
                id_map[player.id.id] = player.is_orange
                if player.is_orange not in hit_locs:
                    hit_locs[player.is_orange] = [
                        [0,0,0,0],
                        [0,0,0,0],
                        [0,0,0,0],
                    ]
                    hit_locs_vert[player.is_orange] = [
                        [0,0,0,0],
                        [0,0,0,0],
                        [0,0,0,0],
                    ]
        for hit in game.game_stats.hits:
            is_orange = id_map[hit.player_id.id]
            ball_x, ball_y, ball_z = hit.ball_data.pos_x, hit.ball_data.pos_y, hit.ball_data.pos_z

            for i in range(len(bounds_y)):
                if bounds_y[i][0] <= ball_y and ball_y < bounds_y[i][1]:
                    for j in range(len(bounds_x)):
                        if bounds_x[j][0] <= ball_x and ball_x < bounds_x[j][1]:
                            hit_locs[is_orange][j][i] += 1
                            break
                    for k in range(len(bounds_z)):
                        if bounds_z[k][0] <= ball_z and ball_z < bounds_z[k][1]:
                            hit_locs_vert[is_orange][k][i] += 1
                            break
                    break

    return hit_locs, hit_locs_vert

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
            draw.text((text_x[j] - (text_map[i][j]["len"] / 2), text_y[i]), text_map[i][j]["text"], fill=BLACK, font=constants.BOUR_40)

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

def draw_field(base_draw, game_list):
    hit_locs, hit_locs_vert = calculate_hit_maps(game_list)

    diffs = (np.array(hit_locs[False]) - np.array(hit_locs[True]), np.array(hit_locs_vert[False]) - np.array(hit_locs_vert[True]))
    max_diffs = (np.max(np.abs(diffs[0])) + 5, np.max(np.abs(diffs[1])) + 5)
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
                if val < 0:
                    color_str = f"hsl(19, 82%, {100 - (50 * ((-1 * val) / max_diffs[idx]))}%)"
                else:
                    color_str = f"hsl(205, 64%, {100 - (50 * (val / max_diffs[idx]))}%)"
                color_list.append(color_str)

                hit_map = hit_locs if idx == 0 else hit_locs_vert
                text = f"{hit_map[False][i][j]}:{hit_map[True][i][j]}"
                text_len = base_draw.textlength(text, font=constants.BOUR_40)
                text_list.append({"text": text, "len": text_len})
            color_maps[idx].append(color_list)
            text_maps[idx].append(text_list)

    img_main = draw_main(color_maps[0], text_maps[0])
    img_vert = draw_vert(color_maps[1], text_maps[1])

    return img_main, img_vert

def create_image(team_names, game_list, config):
    img = Image.new(mode = "RGBA", size = (IMAGE_X, IMAGE_Y), color = WHITE)
    draw = ImageDraw.Draw(img)
    
    # Logo in top left
    logo_width, _ = utils.draw_team_logo(img, MARGIN, config["logo"])

    # Title text
    utils.draw_title_text(draw, logo_width, MARGIN, config, constants.BOUR_80, constants.BOUR_40)

    # Main field image
    img_main, img_vert = draw_field(draw, game_list)
    field_left = round((IMAGE_X / 2) - (img_main.width / 2))
    field_right = round((IMAGE_X / 2) + (img_main.width / 2))
    img.paste(img_vert, (field_left, get_y(img_vert.height + (2 * MARGIN), IMAGE_Y)))
    img.paste(img_main, (field_left, get_y(img_vert.height + img_main.height + (2 * MARGIN), IMAGE_Y)))

    # Team names
    for i in range(len(team_names)):
        name_len = round(draw.textlength(team_names[i], font=constants.BOUR_100))
        name_img = Image.new(mode="RGB", size=(name_len, 80), color=WHITE)
        name_draw = ImageDraw.Draw(name_img)
        name_key = "c1" if i == 0 else "c2"
        name_rot = 90 if i == 0 else -90
        x_pos = field_left - 60 if i == 0 else field_right - 20
        name_draw.text((0,0), team_names[i], fill=constants.TEAM_INFO["RL ESPORTS"][name_key], font=constants.BOUR_100)
        rot_img = name_img.rotate(name_rot, expand=True)
        img.paste(rot_img, (x_pos, get_y(round(((img_main.height + (4 * MARGIN)) / 2) + (name_len / 2)) + img_vert.height, IMAGE_Y)))

    # Dotted circle logo
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    
    img.save(os.path.join("viz", "images", config["img_name"]))


def main():
    team_names = ("DANIEL", "WAHVEY")
    key = "SALT MINE 3"
    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": f"{team_names[0]} 2 - 3 {team_names[1]}",
        "t2": "SALT MINE 3 - NA | STAGE 2 | GROUP B",
        "t3": "TOUCH DIFFERENTIALS",
        "c1": constants.TEAM_INFO[key]["c1"],
        "c2": constants.TEAM_INFO[key]["c2"],
        "img_name": os.path.join("Salt Mine 3", "touches", "daniel_vs_wahvey_touch_heatmap.png")
    }

    data_path = os.path.join("replays", "Salt Mine 3", "Stage 2", "Region - NA", "Groups", "Group B", f"{team_names[0]} VS {team_names[1]}")
    game_list = utils.read_series_data(data_path)
    create_image(team_names, game_list, config)
    
    return 1
  
if __name__ == "__main__":
    main()