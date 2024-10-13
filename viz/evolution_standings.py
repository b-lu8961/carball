from viz import constants, utils

import numpy as np
import os
from PIL import Image, ImageDraw

MARGIN = 40

MARKER_SIZE = 20
MID_X, MID_Y = (constants.MAP_Y + (MARGIN * 4)) / 2, (constants.MAP_X + (MARGIN * 2)) / 2

WHITE, BLACK = (255,255,255), (0,0,0)
LIGHT_GREY, DARK_GREY = (140,140,140), (70,70,70)

def get_y(val, img_height):
    return img_height - val

def parse_rank_file(rank_file):
    rank_data = {}
    for line in rank_file.readlines():
        team, ranks = line.split("|")
        rank_data[team] = [int(num) for num in ranks.split(",")]
    
    return rank_data

def draw_team_lines(rank_file):
    rank_data = parse_rank_file(rank_file)
    num_teams, num_rounds = len(rank_data), len(rank_data[list(rank_data.keys())[0]])
    round_width, rank_height = 125, 150
    
    max_team_len = max([len(team) for team in rank_data])
    #team_label_width = (max_team_len * 12) + 210 + MARGIN
    team_label_width = (max_team_len * 12) + 200 + MARGIN
    width, height = int((num_rounds * round_width) + team_label_width + (MARGIN * 4)), int((num_teams * rank_height) + (MARGIN * 3))
    
    img = Image.new(mode="RGBA", size = (width, height), color=WHITE)
    draw = ImageDraw.Draw(img)

    base_x, base_y = (2 * MARGIN), 0
    
    # Axis lines
    x_axis_y = base_y + (num_teams * rank_height)
    draw.line([(base_x, x_axis_y), (base_x + (num_rounds * round_width), x_axis_y)], fill=DARK_GREY, width=2)
    for i in range(num_rounds):
        tick_x = base_x + ((i + 1) * round_width) - (round_width / 2)
        tick_height = 15
        draw.line([(tick_x, x_axis_y - tick_height), (tick_x, x_axis_y + tick_height)], fill=BLACK, width=2)
        draw.text((tick_x, x_axis_y + 20), str(i + 1), fill=DARK_GREY, font=constants.BOUR_30, anchor="ma")
    draw.text(((base_x + (num_rounds * round_width)) / 2, x_axis_y + 60), "Round", fill=DARK_GREY, font=constants.BOUR_40, anchor="ma")

    draw.line([(base_x, base_y), (base_x, x_axis_y)], fill=DARK_GREY, width=2)
    for i in range(num_teams):
        tick_y = ((i + 1) * rank_height) - (rank_height / 2)
        tick_width = 15
        draw.line([(base_x - tick_width, tick_y), (base_x + tick_width, tick_y)], fill=BLACK, width=2)
        draw.text((base_x - 30, tick_y), str(i + 1), fill=BLACK, font=constants.BOUR_30, anchor="rm")
    y_label_len = round(draw.textlength("Rank", constants.BOUR_40))
    y_label_img = Image.new("RGB", size=(y_label_len, 40), color=WHITE)
    y_label_draw = ImageDraw.Draw(y_label_img)
    y_label_draw.text((0, 0), "Rank", fill=DARK_GREY, font=constants.BOUR_40)
    y_label_rot = y_label_img.rotate(90, expand=True)
    img.paste(y_label_rot, (base_x - 90, int((x_axis_y / 2) - (y_label_len / 2))))

    # Team rank line
    for team in rank_data:
        ranks = rank_data[team]

        line_points = []
        for i in range(len(ranks)):
            round_x = base_x + ((i + 1) * round_width) - (round_width / 2)
            round_y = (ranks[i] * rank_height) - (rank_height / 2)
            line_points.append((round_x, round_y))
        draw.line(line_points, fill=constants.TEAM_INFO[team]["c1"], width=7)

        for i in range(len(line_points)):
            point = line_points[i]
            rad = 15
            draw.ellipse([(point[0] - rad, point[1] - rad), (point[0] + rad, point[1] + rad)], 
                fill=WHITE, outline=constants.TEAM_INFO[team]["c1"], width=5)
        #draw.text((point[0] + 210, point[1]), team, fill=BLACK, font=constants.BOUR_40, anchor="lm")
        draw.text((point[0] + 200, point[1]), team, fill=BLACK, font=constants.BOUR_40, anchor="lm")
        with Image.open(os.path.join("viz", "images", "logos", constants.TEAM_INFO[team]["logo"])) as logo:
            #logo_small = logo.resize((126, 140))
            logo_small = logo.resize((112, 140))
            #pos = (int(point[0] + 55), int(point[1] - 75))
            pos = (int(point[0] + 50), int(point[1] - 75))
            img.paste(logo_small, pos)

    return img


def create_image(rank_file, config):
    rank_img = draw_team_lines(rank_file)
    
    HEADER_HEIGHT = 225
    IMAGE_X, IMAGE_Y = rank_img.width + (2 * MARGIN), rank_img.height + HEADER_HEIGHT + (2 * MARGIN)
    img = Image.new(mode = "RGBA", size = (IMAGE_X, IMAGE_Y), color = WHITE)
    draw = ImageDraw.Draw(img)
    
    # Logo in top left
    logo_width, _ = utils.draw_team_logo(img, MARGIN, config["logo"])

    # Title text
    utils.draw_title_text(draw, logo_width, MARGIN, config, constants.BOUR_80, constants.BOUR_40)

    # Game charts
    img.paste(rank_img, (MARGIN, HEADER_HEIGHT))

    # Dotted circle logo
    #utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    utils.draw_dotted_circle_2(img, draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    
    os.makedirs(config["img_path"], exist_ok=True)
    img.save(os.path.join(config["img_path"], "standings_evo.png"))

def main():
    event = "SHIFT SL"
    region = "North America"
    rn = utils.get_region_label(region)
    base_path = os.path.join("Shift Summer League", region, "2. League Play")

    config = {
        "logo": constants.TEAM_INFO[event]["logo"],
        "t1": "STANDINGS PROGRESSION",
        "t2": f"SHIFT SUMMER LEAGUE | {region.upper()} | LEAGUE PLAY",
        "t3": "",
        "c1": constants.TEAM_INFO[event]["c1"],
        "c2": constants.TEAM_INFO[event]["c2"],
        "img_path": os.path.join("viz", "images", base_path)
    }

    rank_file = open(os.path.join("replays", base_path, rn + "_1_ranks.csv"))
    create_image(rank_file, config)
    
    return 0
  
if __name__ == "__main__":
    main()