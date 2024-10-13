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

def parse_gd_file(gd_file):
    gd_data = {}
    for line in gd_file.readlines():
        team, gds = line.split("|")
        gd_data[team] = [int(num) for num in gds.split(",")]
    
    return gd_data

def draw_team_lines(rank_file):
    gd_data = parse_gd_file(rank_file)
    gd_min = np.floor(min([min(data) for data in gd_data.values()]) / 5) * 5
    if gd_min == min([min(data) for data in gd_data.values()]):
        gd_min -= 5
    gd_max = np.ceil(max([max(data) for data in gd_data.values()]) / 5) * 5
    if gd_max == max([max(data) for data in gd_data.values()]):
        gd_max += 5
    num_rounds = len(gd_data[list(gd_data.keys())[0]])
    round_width, tick_px = 125, 15
    
    max_team_len = max([len(team) for team in gd_data])
    team_label_width = (max_team_len * 12) + (2 * MARGIN)
    #team_label_width = (max_team_len * 12) + 200 + MARGIN
    width, height = int((num_rounds * round_width) + team_label_width + (MARGIN * 5)), int(((gd_max - gd_min) * tick_px) + (MARGIN * 3))
    
    img = Image.new(mode="RGBA", size = (width, height), color=WHITE)
    draw = ImageDraw.Draw(img)

    base_x, base_y = (3 * MARGIN), 20
    
    # Axis lines
    x_axis_y = base_y + ((gd_max - gd_min) * tick_px)
    draw.line([(base_x, x_axis_y), (base_x + (num_rounds * round_width), x_axis_y)], fill=DARK_GREY, width=2)
    for i in range(num_rounds):
        tick_x = base_x + ((i + 1) * round_width) - (round_width / 2)
        tick_height = 15
        draw.line([(tick_x, x_axis_y - tick_height), (tick_x, x_axis_y + tick_height)], fill=BLACK, width=2)
        draw.text((tick_x, x_axis_y + 20), str(i + 1), fill=DARK_GREY, font=constants.BOUR_30, anchor="ma")
    draw.text(((base_x + (num_rounds * round_width)) / 2, x_axis_y + 60), "Round", fill=DARK_GREY, font=constants.BOUR_40, anchor="ma")

    draw.line([(base_x, base_y), (base_x, x_axis_y)], fill=DARK_GREY, width=2)
    for i in range(int(gd_max), int(gd_min) - 1, -1):
        if i % 5 == 0:
            tick_y = x_axis_y - ((i - gd_min) * tick_px)
            tick_width = 15
            draw.line([(base_x - tick_width, tick_y), (base_x + tick_width, tick_y)], fill=BLACK, width=2)
            draw.text((base_x - 30, tick_y), str(i), fill=BLACK, font=constants.BOUR_30, anchor="rm")

            if i == 0:
                utils.linedashed(draw, LIGHT_GREY, 3, base_x, base_x + (num_rounds * round_width) - 50, tick_y, tick_y)
    y_label_len = round(draw.textlength("Goal Differential", constants.BOUR_40))
    y_label_img = Image.new("RGB", size=(y_label_len, 40), color=WHITE)
    y_label_draw = ImageDraw.Draw(y_label_img)
    y_label_draw.text((0, 0), "Goal Differential", fill=DARK_GREY, font=constants.BOUR_40)
    y_label_rot = y_label_img.rotate(90, expand=True)
    img.paste(y_label_rot, (base_x - 120, int((x_axis_y / 2) - (y_label_len / 2))))

    # Team rank line
    for team in gd_data:
        gds = gd_data[team]

        line_points = []
        for i in range(len(gds)):
            round_x = base_x + ((i + 1) * round_width) - (round_width / 2)
            round_y = x_axis_y - ((gds[i] - gd_min) * tick_px)
            line_points.append((round_x, round_y))
            
        draw.line(line_points, fill=constants.TEAM_INFO[team]["c1"], width=7)

        for i in range(len(line_points)):
            point = line_points[i]
            rad = 12
            draw.ellipse([(point[0] - rad, point[1] - rad), (point[0] + rad, point[1] + rad)], 
                fill=WHITE, outline=constants.TEAM_INFO[team]["c1"], width=5)
        if team == "RESOLVE":
            label_y = point[1] - 20
        elif team == "FAKE GA":
            label_y = point[1] + 20
        elif team == "REBELLION":
            label_y = point[1] - 10
        elif team == "GEN.G":
            label_y = point[1] + 10
        else:
            label_y = point[1]
        draw.text((point[0] + 50, label_y), team + " ({})".format(gds[-1]), fill=BLACK, font=constants.BOUR_40, anchor="lm")

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
    img.save(os.path.join(config["img_path"], "goal_diff_evo.png"))

def main():
    event = "SHIFT SL"
    region = "North America"
    rn = utils.get_region_label(region)
    base_path = os.path.join("Shift Summer League", region, "2. League Play")

    config = {
        "logo": constants.TEAM_INFO[event]["logo"],
        "t1": "GOAL DIFF PROGRESSION",
        "t2": f"SHIFT SUMMER LEAGUE | {region.upper()} | LEAGUE PLAY",
        "t3": "",
        "c1": constants.TEAM_INFO[event]["c1"],
        "c2": constants.TEAM_INFO[event]["c2"],
        "img_path": os.path.join("viz", "images", base_path)
    }

    rank_file = open(os.path.join("replays", base_path, rn + "_1_gd.csv"))
    create_image(rank_file, config)
    
    return 0
  
if __name__ == "__main__":
    main()