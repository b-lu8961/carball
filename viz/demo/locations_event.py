from viz import constants, utils

import numpy as np
import os
from PIL import Image, ImageDraw

MARGIN = 40

MARKER_SIZE = 10

WHITE, BLACK = (255,255,255), (0,0,0)
LIGHT_GREY, DARK_GREY = (180,180,180), (70,70,70)

def get_y(val, img_height):
    return img_height - val

def calculate_demo_data(data_path, config):
    map_x, map_y = constants.MAP_X * constants.SCALE, constants.MAP_Y * constants.SCALE
    bounds_x = [(map_x / 6, map_x / 2), (-(map_x / 6), map_x / 6), (-(map_x / 2), -(map_x / 6))]
    bounds_y = [(-np.inf, -(map_y / 4)), (-(map_y / 4), 0), (0, map_y / 4), (map_y / 4, np.inf)]
    #bounds_z = [(0, ball_height), (ball_height, goal_z), (goal_z, map_z)]
    
    team_totals = {}
    player_totals = {}
    #totals_vert = [[0,0,0,0],[0,0,0,0],[0,0,0,0]]

    game_list = utils.read_group_data(data_path)
    for game in game_list:    
        blue_label, orange_label = "", ""
        for team in game.teams:
            tn = utils.get_label_from_team(game, team, config["region"])
            if team.is_orange:
                orange_label = tn
            else:
                blue_label = tn

            if tn not in team_totals:
                team_totals[tn] = [[0,0,0,0],[0,0,0,0],[0,0,0,0]]
        for player in game.players:
            pn = utils.get_player_label(player.name, config["region"])
            if pn not in player_totals:
                player_totals[pn] = [[0,0,0,0],[0,0,0,0],[0,0,0,0]]

        for demo in game.game_metadata.demos:
            if not demo.is_valid:
               continue
            attacker = [player for player in game.players if player.name == demo.attacker_name][0]
            ball_x = -1 * demo.location.pos_x if attacker.is_orange else demo.location.pos_x
            ball_y = -1 * demo.location.pos_y if attacker.is_orange else demo.location.pos_y
            ball_z = demo.location.pos_z
            team_label = orange_label if attacker.is_orange else blue_label
            player_label = utils.get_player_label(demo.attacker_name, config["region"])
            for i in range(len(bounds_y)):
                if bounds_y[i][0] <= ball_y and ball_y < bounds_y[i][1]:
                    for j in range(len(bounds_x)):
                        if bounds_x[j][0] <= ball_x and ball_x < bounds_x[j][1]:
                            team_totals[team_label][j][i] += 1
                            player_totals[player_label][j][i] += 1
                            #xG_val = utils.get_xG_val(game, goal)
                            #team_totals[team_label][j][i] += xG_val
                            #player_totals[player_label][j][i] += xG_val
                            break
                    # for k in range(len(bounds_z)):
                    #     if bounds_z[k][0] <= ball_z and ball_z < bounds_z[k][1]:
                    #         totals_vert[k][i] += 1
                    #         break
                    break
    
    return team_totals, player_totals

def get_top_scorers(team_data, player_data):
    team_map = []
    player_map = []
    for row in range(3):
        team_list = []
        player_list = []
        for col in range(4):
            team_sort = sorted(team_data.items(), key=lambda item: (-item[1][row][col], str.casefold(item[0])))
            team_list.append((team_sort[0][0], team_sort[0][1][row][col]))
            player_sort = sorted(player_data.items(), key=lambda item: (-item[1][row][col], str.casefold(item[0])))
            player_list.append((player_sort[0][0], player_sort[0][1][row][col]))
        team_map.append(team_list)
        player_map.append(player_list)

    #print(team_map)
    #print(player_map)
    return team_map, player_map

def draw_main(team_map, player_map, config):
    width, height = round(constants.MAP_Y) + (MARGIN * 4), round(constants.MAP_X) + (MARGIN * 2)
    img = Image.new(mode="RGBA", size = (width, height), color=WHITE)
    draw = ImageDraw.Draw(img)
    utils.draw_field_lines(draw, MARGIN, height, sections=True, dash_color=constants.REGION_COLORS[config["region"]][0])

    MID_X, MID_Y = (constants.MAP_Y + (MARGIN * 4)) / 2, (constants.MAP_X + (MARGIN * 2)) / 2
    text_x = [
        MID_X - (1.5 * constants.MAP_Y_QUARTER), MID_X - (0.5 * constants.MAP_Y_QUARTER),
        MID_X + (0.5 * constants.MAP_Y_QUARTER), MID_X + (1.5 * constants.MAP_Y_QUARTER)
    ]
    text_y = [
        get_y(MID_Y + constants.MAP_X_THIRD, img.height), 
        get_y(MID_Y, img.height), 
        get_y(MID_Y - constants.MAP_X_THIRD, img.height)
    ]

    for i in range(len(text_y)):
        for j in range(len(text_x)):
            team_text = f"{team_map[i][j][0]}: {team_map[i][j][1]}"
            player_text = f"{player_map[i][j][0]}: {player_map[i][j][1]}"
            draw.text((text_x[j], text_y[i] - 10), team_text, fill=BLACK, font=constants.BOUR_50, anchor="md")
            draw.text((text_x[j], text_y[i] + 10), player_text, fill=BLACK, font=constants.BOUR_50, anchor="ma")

    return img

def draw_header(img: Image.Image, draw: ImageDraw.ImageDraw, config):
    # Logo in top left
    pos = (MARGIN, MARGIN - 10)
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

def create_image(config, data_path):
    img_width = 2400
    img_height = 2000
    img = Image.new(mode = "RGBA", size = (round(img_width), img_height), color = WHITE)
    draw = ImageDraw.Draw(img)

    team_data, player_data = calculate_demo_data(data_path, config)
    team_map, player_map = get_top_scorers(team_data, player_data)

    draw_header(img, draw, config)
    field_img = draw_main(team_map, player_map, config)
    img.paste(field_img, (int((img_width / 2) - (field_img.width / 2)), 350))
    dir_len = draw.textlength("Attacking Direction", font=constants.BOUR_50)
    draw.text(((img_width / 2) - (dir_len / 2) + MARGIN, 340), "Attacking Direction >>", fill=DARK_GREY, font=constants.BOUR_40)

    os.makedirs(config['img_path'], exist_ok=True)
    img.save(os.path.join(config["img_path"], "top_demo_locations.png"))

def main():
    region = "Europe"
    rn = utils.get_region_label(region)
    base_path = os.path.join("RLCS 24", "Major 2", region, "Open Qualifiers 2")
    data_path = os.path.join("replays", base_path)
    
    config = {
        "logo": constants.TEAM_INFO["RLCS"]["logo"],
        "t1": "TOP DEMOS BY FIELD LOCATION",
        "t2": f"RLCS 24 {rn} | OQ 5",
        "t3": "TEAMS & PLAYERS",
        "region": utils.get_region_label(region),
        "c1": constants.TEAM_INFO["RLCS"]["c1"],
        "c2": constants.TEAM_INFO["RLCS"]["c2"],
        "img_path": os.path.join("viz", "images", base_path)
    }
    create_image(config, data_path)
    
    return 0
  
if __name__ == "__main__":
    main()
