from viz import constants, utils

import numpy as np
import os
from PIL import Image, ImageDraw

IMAGE_X, IMAGE_Y = 2700, 2600
MARGIN = 40

MARKER_SIZE = 20
MID_X, MID_Y = (constants.MAP_Y + (MARGIN * 4)) / 2, (constants.MAP_X + (MARGIN * 2)) / 2

WHITE, BLACK = (255,255,255), (0,0,0)
LIGHT_GREY, DARK_GREY = (140,140,140), (70,70,70)

def get_y(val, img_height):
    return img_height - val

def calculate_stats(game_list):
    player_data = {}
    for game in game_list:
        for player in game.players:
            if player.name not in player_data:
                player_data[player.name] = {
                    "gp": 0,
                    "time_oh": 0,
                    "time_hi": 0,
                    "boost_use": 0,
                    "time_ss": 0,
                    "avg_spd": 0
                }
            player_data[player.name]['gp'] += 1
            player_data[player.name]['time_hi'] += player.stats.positional_tendencies.time_high
            player_data[player.name]['time_oh'] += player.stats.positional_tendencies.time_in_attacking_half
            player_data[player.name]['boost_use'] += player.stats.boost.boost_usage
            player_data[player.name]['time_ss'] += player.stats.speed.time_at_super_sonic
            player_data[player.name]['avg_spd'] += player.stats.averages.average_speed
    return player_data

def create_image(player_name, game_list, config):
    img = Image.new(mode = "RGBA", size = (IMAGE_X, IMAGE_Y), color = WHITE)
    draw = ImageDraw.Draw(img)
    
    # Logo in top left
    logo_width, _ = utils.draw_team_logo(img, MARGIN, config["logo"])

    player_data = calculate_stats(game_list)
    for data in player_data.values():
        for key in data.keys():
            if key != "gp":
                data[key] = round(data[key] / data["gp"], 2)
    data_sorted = dict(sorted(player_data.items(), key=lambda item: item[1]["boost_use"], reverse=True))
    
    # Table rows
    name_y, base_y, row_y = 350, 475, 125
    base_x = 150
    draw.text((base_x - 70, name_y), "Player Name", fill=BLACK, font=constants.BOUR_60)
    draw.multiline_text((base_x + 350, name_y - 50), "Games\nPlayed", fill=BLACK, font=constants.BOUR_60)
    draw.text((base_x + 620, name_y), "Boost Usage", fill=BLACK, font=constants.BOUR_60)
    draw.multiline_text((base_x + 1015, name_y - 50), "Time in\nOff. Half", fill=BLACK, font=constants.BOUR_60, align="center")
    draw.multiline_text((base_x + 1370, name_y - 50), "Time in\nHigh Air", fill=BLACK, font=constants.BOUR_60, align='center')
    draw.multiline_text((base_x + 1680, name_y - 50), "Time\nSupersonic",fill=BLACK, font=constants.BOUR_60, align='center')
    draw.text((base_x + 2060, name_y), "Avg. Speed*", fill=BLACK, font=constants.BOUR_60)
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
            (base_x - 50, base_y + (i * row_y) - 26), (base_x + 2400, base_y + (i * row_y) + 74)
        ], 50, fill=rect_color, outline=rect_line, width=5)
        draw.text((base_x, base_y + (i * row_y)), name, fill=BLACK, font=constants.BOUR_50)
        draw.text((base_x + 420, base_y + (i * row_y)), str(data_sorted[name]["gp"]), fill=BLACK, font=constants.BOUR_50)
        draw.text((base_x + 690, base_y + (i * row_y)), "{:.2f}".format(data_sorted[name]['boost_use']), fill=BLACK, font=constants.BOUR_50)
        draw.text((base_x + 1050, base_y + (i * row_y)), "{:.2f}".format(data_sorted[name]['time_oh']), fill=BLACK, font=constants.BOUR_50)
        draw.text((base_x + 1400, base_y + (i * row_y)), "{:.2f}".format(data_sorted[name]['time_hi']), fill=BLACK, font=constants.BOUR_50)
        draw.text((base_x + 1765, base_y + (i * row_y)), "{:.2f}".format(data_sorted[name]['time_ss']), fill=BLACK, font=constants.BOUR_50)
        draw.text((base_x + 2125, base_y + (i * row_y)), "{:.2f}%".format(round(data_sorted[name]['avg_spd'] / 220, 2)), fill=BLACK, font=constants.BOUR_50)

    draw.text((100, get_y(60, IMAGE_Y)), "*Average speed as a percentage of max speed (supersonic)", fill=DARK_GREY, font=constants.BOUR_40)

    # Title text
    utils.draw_title_text(draw, logo_width, MARGIN, config, constants.BOUR_80, constants.BOUR_40)

    # Dotted circle logo
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    
    img.save(os.path.join("viz", "images", config["img_name"]))

def main():
    player_name = "CHEESE."
    key = "SOLO Q"
    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": "MOVEMENT & POSITIONING STATS",
        "t2": "SOLO Q | MAIN EVENT 2",
        "t3": "PER-GAME VALUES, RANKED BY BOOST USAGE",
        "c1": constants.TEAM_INFO[key]["c1"],
        "c2": constants.TEAM_INFO[key]["c2"],
        "img_name": os.path.join("rankings", "soloq_ranking.png")
    }

    data_path = os.path.join("replays", "Solo Q", "Event 2")
    game_list = utils.read_group_data(data_path)
    create_image(player_name, game_list, config)
    
    return 1
  
if __name__ == "__main__":
    main()