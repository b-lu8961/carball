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
    team_data = {}
    id_map = {}
    for game in game_list:
        for idx in range(len(game.teams)):
            team = game.teams[idx]
            team_name = "KRÜ ESPORTS" if team.name == "KRU ESPORTS" else team.name
            if team_name not in team_data:
                for id_str in [player_id.id for player_id in team.player_ids]:
                    id_map[id_str] = team
                team_data[team_name] = {
                    "gp": 0,
                    "sp": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "xG_for": 0,
                    "xG_against": 0,
                    "xG_diff": 0
                }
            team_data[team_name]["gp"] += 1
            team_data[team_name]["sp"] += game.game_metadata.seconds
            team_data[team_name]["goals_for"] += team.score
            other_idx = 1 if idx == 0 else 0
            team_data[team_name]["goals_against"] += game.teams[other_idx].score 
            
        
        for shot in game.game_metadata.shot_details:
            xG_val = utils.get_xG_val(game, shot)
            for_team = [team for team in game.teams if team.is_orange == shot.is_orange][0]
            for_name = "KRÜ ESPORTS" if for_team.name == "KRU ESPORTS" else for_team.name
            against_team = [team for team in game.teams if team.is_orange != shot.is_orange][0]
            against_name = "KRÜ ESPORTS" if against_team.name == "KRU ESPORTS" else against_team.name
            team_data[for_name]["xG_for"] += xG_val
            team_data[for_name]["xG_diff"] += xG_val
            team_data[against_name]["xG_against"] += xG_val
            team_data[against_name]["xG_diff"] -= xG_val
            
    return team_data

def create_image(game_list, config):
    team_data = calculate_stats(game_list)
    for data in team_data.values():
        for key in data.keys():
            if key not in ["gp", "sp"]:
                data[key] = round(data[key] / (data["sp"] / 300), 2)
    data_sorted = dict(sorted(team_data.items(), key=lambda item: item[1]["xG_for"], reverse=True))

    img_height = (len(data_sorted.keys()) * 130) + 400
    img = Image.new(mode = "RGBA", size = (IMAGE_X, img_height), color = WHITE)
    draw = ImageDraw.Draw(img)
    
    # Logo in top left
    logo_width, _ = utils.draw_team_logo(img, MARGIN, config["logo"])
    
    name_y, base_y, row_y = 325, 450, 125
    base_x = 150
    draw.text((base_x, name_y), "Team Name", fill=BLACK, font=constants.BOUR_60)
    draw.text((base_x + 400, name_y), "Games", fill=BLACK, font=constants.BOUR_60)
    draw.text((base_x + 680, name_y), "Goals For", fill=BLACK, font=constants.BOUR_60)
    draw.text((base_x + 1000, name_y), "Goals Against", fill=BLACK, font=constants.BOUR_60)
    draw.text((base_x + 1450, name_y), "xG For", fill=BLACK, font=constants.BOUR_60)
    draw.text((base_x + 1720, name_y), "xG Against", fill=BLACK, font=constants.BOUR_60)
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
        draw.text((base_x + 460, base_y + (i * row_y)), str(data_sorted[name]['gp']), fill=BLACK, font=constants.BOUR_50)
        draw.text((base_x + 745, base_y + (i * row_y)), "{:.2f}".format(data_sorted[name]['goals_for']), fill=BLACK, font=constants.BOUR_50)
        draw.text((base_x + 1120, base_y + (i * row_y)), "{:.2f}".format(data_sorted[name]['goals_against']), fill=BLACK, font=constants.BOUR_50)
        draw.text((base_x + 1480, base_y + (i * row_y)), "{:.2f}".format(data_sorted[name]['xG_for']), fill=BLACK, font=constants.BOUR_50)
        draw.text((base_x + 1810, base_y + (i * row_y)), "{:.2f}".format(data_sorted[name]['xG_against']), fill=BLACK, font=constants.BOUR_50)

    # Title text
    utils.draw_title_text(draw, logo_width, MARGIN, config, constants.BOUR_80, constants.BOUR_40)

    # Dotted circle logo
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    
    img.save(os.path.join("viz", "images", config["img_name"]))

def main():

    # TODO: Change col order, games -> 5:00

    key = "RL ESPORTS"
    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": "EXPECTED GOAL STATS",
        "t2": "RLCS 24 NA | OQ 1 | SWISS",
        "t3": "PER-GAME VALUES, RANKED BY XG FOR",
        "c1": constants.TEAM_INFO[key]["c1"],
        "c2": constants.TEAM_INFO[key]["c2"],
        "img_name": os.path.join("RLCS 24", "NA", "xG", "OQ1_swiss_xG_ranking.png")
    }

    data_path = os.path.join("replays", "RLCS 24", "Major 1", "North America", "Open Qualifiers 1", "Day 3 - Swiss Stage")
    game_list = utils.read_group_data(data_path)
    create_image(game_list, config)
    
    return 1
  
if __name__ == "__main__":
    main()