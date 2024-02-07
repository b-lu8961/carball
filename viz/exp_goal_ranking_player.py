from viz import constants, utils

import os
from PIL import Image, ImageDraw

IMAGE_X, IMAGE_Y = 2400, 2450
MARGIN = 40

MARKER_SIZE = 20
MID_X, MID_Y = (constants.MAP_Y + (MARGIN * 4)) / 2, (constants.MAP_X + (MARGIN * 2)) / 2

WHITE, BLACK = (255,255,255), (0,0,0)
LIGHT_GREY, DARK_GREY = (140,140,140), (70,70,70)

def get_y(val, img_height):
    return img_height - val

def calculate_stats(game_list):
    player_data = {}
    id_map = {}
    for game in game_list:
        for idx in range(len(game.players)):
            player = game.players[idx]
            player_name = "Sad" if player.name == "Sadness" else player.name
            if player_name not in player_data:
                id_map[player.id.id] = player.name
                player_data[player_name] = {
                    "gp": 0,
                    "goals": 0,
                    "shots": 0,
                    "xG": 0,
                }
            player_data[player_name]["gp"] += 1
            player_data[player_name]["goals"] += player.goals
            player_data[player_name]["shots"] += player.shots
        
        for shot in game.game_metadata.shot_details:
            xG_val = utils.get_xG_val(game, shot)
            shot_hit = [hit for hit in game.game_stats.hits if hit.frame_number == shot.frame_number][0]
            player_name = [player.name for player in game.players if shot_hit.player_id.id == player.id.id][0]
            player_name = "Sad" if player_name == "Sadness" else player_name
            player_data[player_name]["xG"] += xG_val

    return player_data

def create_image(game_list, config):
    player_data = calculate_stats(game_list)
    for data in player_data.values():
        data["shp"] = 100 * (data["goals"] / data["shots"])
        for key in data.keys():
            if key != "gp" and key != "shp":
                data[key] = round(data[key] / data["gp"], 2)
    data_sorted = dict(sorted(player_data.items(), key=lambda item: item[1]["xG"], reverse=True))

    img_height = (min(25, len(data_sorted.keys())) * 130) + 400
    img = Image.new(mode = "RGBA", size = (IMAGE_X, img_height), color = WHITE)
    draw = ImageDraw.Draw(img)
    
    # Logo in top left
    logo_width, _ = utils.draw_team_logo(img, MARGIN, config["logo"])
    
    name_y, base_y, row_y = 325, 450, 125
    base_x = 150
    draw.text((base_x, name_y), "Player Name", fill=BLACK, font=constants.BOUR_60)
    draw.text((base_x + 400, name_y), "Games", fill=BLACK, font=constants.BOUR_60)
    draw.text((base_x + 720, name_y), "Goals", fill=BLACK, font=constants.BOUR_60)
    draw.text((base_x + 1095, name_y), "Shots", fill=BLACK, font=constants.BOUR_60)
    draw.text((base_x + 1495, name_y), "xG", fill=BLACK, font=constants.BOUR_60)
    draw.text((base_x + 1760, name_y), "Shooting %", fill=BLACK, font=constants.BOUR_60)
    player_list = list(data_sorted.keys())
    for i in range(min(25, len(player_list))):
        name = player_list[i]
        if i == 0:
            rect_color = "#FFD700"
            rect_line = BLACK
        elif i == 1:
            rect_color = "#C0C0C0"
            rect_line = BLACK
        elif i == 2:
            rect_color = "#D7995B"
            rect_line = BLACK
        else:
            rect_color = WHITE
            rect_line = constants.TEAM_INFO["RL ESPORTS"]["c1"] if i % 2 == 0 else constants.TEAM_INFO["RL ESPORTS"]["c2"]
        draw.rounded_rectangle([
            (base_x - 50, base_y + (i * row_y) - 26), (base_x + 2100, base_y + (i * row_y) + 74)
        ], 50, fill=rect_color, outline=rect_line, width=5)
        draw.text((base_x, base_y + (i * row_y)), name, fill=BLACK, font=constants.BOUR_50)
        draw.text((base_x + 460, base_y + (i * row_y)), str(data_sorted[name]['gp']), fill=BLACK, font=constants.BOUR_50)
        draw.text((base_x + 745, base_y + (i * row_y)), "{:.2f}".format(data_sorted[name]['goals']), fill=BLACK, font=constants.BOUR_50)
        draw.text((base_x + 1120, base_y + (i * row_y)), "{:.2f}".format(data_sorted[name]['shots']), fill=BLACK, font=constants.BOUR_50)
        draw.text((base_x + 1480, base_y + (i * row_y)), "{:.2f}".format(data_sorted[name]['xG']), fill=BLACK, font=constants.BOUR_50)
        draw.text((base_x + 1810, base_y + (i * row_y)), "{:.2f}%".format(data_sorted[name]['shp']), fill=BLACK, font=constants.BOUR_50)

    # Title text
    utils.draw_title_text(draw, logo_width, MARGIN, config, constants.BOUR_80, constants.BOUR_40)

    # Dotted circle logo
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    
    img.save(os.path.join("viz", "images", config["img_name"]))

def main():
    key = "RL ESPORTS"
    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": "EXPECTED GOAL STATS",
        "t2": "RLCS 23 WORLDS | MAIN EVENT",
        "t3": "PER-GAME VALUES, RANKED BY XG",
        "c1": constants.TEAM_INFO[key]["c1"],
        "c2": constants.TEAM_INFO[key]["c2"],
        "img_name": os.path.join("exp_goals", "worlds_main_event_ranking_player.png")
    }

    data_path = os.path.join("replays", "RLCS 23", "Worlds", "Main Event")
    game_list = utils.read_group_data(data_path)
    create_image(game_list, config)
    
    return 1
  
if __name__ == "__main__":
    main()