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

def calculate_stats(game_list):
    team_data = {}
    id_map = {}
    for game in game_list:
        for idx in range(len(game.teams)):
            team = game.teams[idx]
            if team.name not in team_data:
                for id_str in [player_id.id for player_id in team.player_ids]:
                    id_map[id_str] = team
                team_data[team.name] = {
                    "gp": 0,
                    "oh_touches": 0,
                    "ha_touches": 0,
                    "boost_use": 0,
                    "goal_diff": 0,
                    "shots": 0,
                    "assists": 0,
                    "goals": 0
                }
            team_data[team.name]["gp"] += 1
            team_data[team.name]["goals"] += team.score
            if idx == 0:
                team_data[team.name]["goal_diff"] += (team.score - game.teams[1].score)
            else:
                team_data[team.name]["goal_diff"] += (team.score - game.teams[0].score)
                
        for player in game.players:
            team_data[player.team_name]["shots"] += player.shots
            team_data[player.team_name]["assists"] += player.assists
            team_data[player.team_name]["boost_use"] += player.stats.boost.boost_usage
            
        for hit in [hit for hit in game.game_stats.hits]:
            team = id_map[hit.player_id.id]
            ball_y = -1 * hit.ball_data.pos_y if team.is_orange else hit.ball_data.pos_y
            if ball_y > 0:
                team_data[team.name]["oh_touches"] += 1
            if hit.ball_data.pos_z > 642.775:
                team_data[team.name]["ha_touches"] += 1
    return team_data

def create_image(player_name, game_list, config):
    img = Image.new(mode = "RGBA", size = (IMAGE_X, IMAGE_Y), color = WHITE)
    draw = ImageDraw.Draw(img)
    
    # Logo in top left
    logo_width, _ = utils.draw_team_logo(img, MARGIN, config["logo"])

    team_data = calculate_stats(game_list)
    for data in team_data.values():
        for key in data.keys():
            if key != "gp":
                data[key] = round(data[key] / data["gp"], 2)
    data_sorted = dict(sorted(team_data.items(), key=lambda item: item[1]["goal_diff"], reverse=True))
    
    name_y, base_y, row_y = 325, 450, 125
    base_x = 150
    draw.text((base_x, name_y), "Team Name", fill=BLACK, font=constants.BOUR_60)
    draw.text((base_x + 440, name_y), "Goal Diff.", fill=BLACK, font=constants.BOUR_60)
    draw.text((base_x + 775, name_y), "Goals", fill=BLACK, font=constants.BOUR_60)
    draw.text((base_x + 1070, name_y), "Shots", fill=BLACK, font=constants.BOUR_60)
    draw.text((base_x + 1300, name_y), "Off. Half Touches", fill=BLACK, font=constants.BOUR_60)
    draw.text((base_x + 1805, name_y), "Boost Usage", fill=BLACK, font=constants.BOUR_60)
    team_list = list(data_sorted.keys())
    for i in range(len(team_list)):
        name = team_list[i]
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
        draw.text((base_x + 500, base_y + (i * row_y)), "{:.2f}".format(data_sorted[name]['goal_diff']), fill=BLACK, font=constants.BOUR_50)
        draw.text((base_x + 800, base_y + (i * row_y)), "{:.2f}".format(data_sorted[name]['goals']), fill=BLACK, font=constants.BOUR_50)
        draw.text((base_x + 1100, base_y + (i * row_y)), "{:.2f}".format(data_sorted[name]['shots']), fill=BLACK, font=constants.BOUR_50)
        draw.text((base_x + 1460, base_y + (i * row_y)), "{:.2f}".format(data_sorted[name]['oh_touches']), fill=BLACK, font=constants.BOUR_50)
        draw.text((base_x + 1870, base_y + (i * row_y)), "{:.2f}".format(data_sorted[name]['boost_use']), fill=BLACK, font=constants.BOUR_50)

    # Title text
    utils.draw_title_text(draw, logo_width, MARGIN, config, constants.BOUR_80, constants.BOUR_40)

    # Dotted circle logo
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    
    img.save(os.path.join("viz", "images", config["img_name"]))

def main():
    player_name = "CHEESE."
    key = "LATAM CHAMP"
    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": "ATTACKING STATS",
        "t2": "LATAM CHAMPIONSHIP 2023 | BRAZIL | EVENT 3 | DAY 2 & 3",
        "t3": "PER-GAME VALUES, RANKED BY GOAL DIFFERENTIAL",
        "c1": constants.TEAM_INFO[key]["c1"],
        "c2": constants.TEAM_INFO[key]["c2"],
        "img_name": os.path.join("rankings", "latam_3_ranking.png")
    }

    data_path = os.path.join("replays", "Playoffs")
    game_list = utils.read_group_data(data_path)
    create_image(player_name, game_list, config)
    
    return 1
  
if __name__ == "__main__":
    main()