from viz import constants, utils

import json
import numpy as np
import os
from PIL import Image, ImageDraw
from scipy.stats import percentileofscore

MARGIN = 40

MARKER_SIZE = 10

WHITE, BLACK = (255,255,255), (0,0,0)
LIGHT_GREY, DARK_GREY = (180,180,180), (70,70,70)

COL_1_WIDTH = constants.GOAL_X + (4 * MARGIN)
COL_2_WIDTH = 2100
COL_3_WIDTH = 1750

HEADER_HEIGHT = 350
STAT_NAMES = [
    [("sb", "shots_allowed"), "Shots Allowed"], [("sb", "saves"), "Saves"], [("pssn", "recoveries"), "Recoveries"],
    [("pssn", "blocks"), "Blocks"], [("sb", "steals"), "Boost Steals"], [("sb", "demos"), "Demos"],
    [("sb", "shots"), "Shots"], [("sb", "goals"), "Goals"], [("sb", "assists"), "Assists"],
    [("pssn", "prog_passes"), "Prog Passes"], [("pssn", "prog_dribbles"), "Prog Dribbles"], [("sb", "touches"), "Touches"]
]

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

def get_rot_text(draw, text, font=constants.BOUR_60, height=50, fill=BLACK, rot=90):
    img_len = round(draw.textlength(text, font=font))
    img = Image.new(mode="RGBA", size=(img_len, height), color=WHITE)
    img_draw = ImageDraw.Draw(img)
    img_draw.text((0, 0), text, fill=fill, font=font)
    return img.rotate(rot, expand=True, fillcolor=(0,0,0,0))

def get_percentiles(player, event, stat_data, lan_only=False):
    player_data = {}
    for stat, _ in STAT_NAMES:
        if lan_only:
            pop_data = [stat_data[key][stat[0]][stat[1]] for key in stat_data if stat_data[key]["gp"] >= 9 and "LAN" in key[1]]
        else:
            pop_data = [stat_data[key][stat[0]][stat[1]] for key in stat_data if stat_data[key]["gp"] >= 9]
        player_val = stat_data[(player, event)][stat[0]][stat[1]]
        player_data[stat] = percentileofscore(pop_data, player_val)
    player_data[("sb", "shots_allowed")] = 100 - player_data[("sb", "shots_allowed")]
    return player_data

def draw_radar(img, draw, percentiles, player_data, region):
    X_MID, Y_MID = img.width / 2, (img.height + HEADER_HEIGHT)  / 2
    RADIUS, IN_RAD = 650, 150
    
    for i in range(len(STAT_NAMES)):
        stat, label = STAT_NAMES[i]
        pctile = percentiles[stat]
        start_ang, end_ang = (360 / 12) * i, (360 / 12) * (i + 1)

        # Slice
        stat_bbox = [
            (X_MID - ((RADIUS - IN_RAD) * (pctile / 100)) - IN_RAD, Y_MID - ((RADIUS - IN_RAD) * (pctile / 100)) - IN_RAD),
            (X_MID + ((RADIUS - IN_RAD) * (pctile / 100)) + IN_RAD, Y_MID + ((RADIUS - IN_RAD) * (pctile / 100)) + IN_RAD)
        ]
        if 0 <= i and i < 3:
            slice_fill, arc_fill = constants.TEAM_INFO["RLCS"]["c2"], (171, 83, 41)
        elif 3 <= i and i < 6:
            slice_fill, arc_fill = (38, 194, 110), (24, 125, 71)
        elif 6 <= i and i < 9:
            slice_fill, arc_fill = constants.TEAM_INFO["RLCS"]["c1"], (53, 109, 148)
        else:
            slice_fill, arc_fill = (230, 0, 125), (156, 0, 85)
        draw.pieslice(stat_bbox, start_ang, end_ang, fill=slice_fill)

        # Slice Stripes
        for j in range(0, int(pctile), 10):
            arc_bbox = [
                (X_MID - ((RADIUS - IN_RAD) * (j / 100)) - IN_RAD, Y_MID - ((RADIUS - IN_RAD) * (j / 100)) - IN_RAD),
                (X_MID + ((RADIUS - IN_RAD) * (j / 100)) + IN_RAD, Y_MID + ((RADIUS - IN_RAD) * (j / 100)) + IN_RAD)
            ]
            draw.arc(arc_bbox, start_ang + 12.5, end_ang - 12.5, fill=arc_fill, width=3)

        # Label
        rad = ((start_ang + end_ang) / 2 / 360) * 2 * np.pi
        point = (X_MID + ((RADIUS + 50) * np.cos(rad)), Y_MID + ((RADIUS + 50) * np.sin(rad)))
        rot_ang = -90 - ((start_ang + end_ang) / 2) if i > 5 else 90 - ((start_ang + end_ang) / 2)
        label_img = get_rot_text(draw, label, constants.BOUR_60, 60, DARK_GREY, rot_ang)
        img.paste(label_img, (round(point[0] - (label_img.width / 2)), round(point[1] - (label_img.height / 2))), mask=label_img)
        
        val_point = (X_MID + ((RADIUS + 125) * np.cos(rad)), Y_MID + ((RADIUS + 125) * np.sin(rad)))
        val_img = get_rot_text(draw, str(player_data[stat[0]][stat[1]]), constants.BOUR_70, 60, BLACK, rot_ang)
        img.paste(val_img, (round(val_point[0] - (val_img.width / 2)), round(val_point[1] - (val_img.height / 2))), mask=val_img)
        
        # Divider line
        div_rad = (start_ang / 360) * 2 * np.pi
        div_end = (X_MID + (RADIUS * np.cos(div_rad)), Y_MID + (RADIUS * np.sin(div_rad)))
        draw.line([(X_MID, Y_MID), div_end], fill=LIGHT_GREY, width=5)

    
    draw.circle((X_MID, Y_MID), RADIUS, outline=constants.REGION_COLORS[region][0], width=7)
    draw.circle((X_MID, Y_MID), IN_RAD, fill=WHITE, outline=DARK_GREY, width=5)
    draw.multiline_text((X_MID, Y_MID), f"{player_data["gp"]} GP\n{round(player_data["secs"] / 60)} MINS", 
        font=constants.BOUR_60, fill=BLACK, align="center", anchor="mm")



def create_image(config, player_name, event_name, data_path):
    img_width = 2000 + (2 * MARGIN)
    img_height = HEADER_HEIGHT + 1800 + (2 * MARGIN)
    img = Image.new(mode = "RGBA", size = (round(img_width), img_height), color = WHITE)
    draw = ImageDraw.Draw(img)

    stat_data = utils.read_event_stats_file(data_path)
    percentiles = get_percentiles(player_name, event_name, stat_data, lan_only=False)
    player_data = stat_data[(player_name, event_name)]

    draw_header(img, draw, stat_data, config)
    draw_radar(img, draw, percentiles, player_data, config["region"])

    bot_text = "Percentile rank versus event performances since RLCS 24"
    draw.text((img_width / 2, img_height - 60), bot_text, fill=DARK_GREY, font=constants.BOUR_50, anchor="ma")

    os.makedirs(config['img_path'], exist_ok=True)
    img.save(os.path.join(config["img_path"], f"{player_name.replace('.', '')}.png"))


def main():
    team_name = "OXYGEN ESPORTS"
    player_name = "Oski"
    event_name = "WC LAN"
    region = "Europe"
    base_path = os.path.join("RLCS 24", "World Championship")
    data_path = "rlcs24_player_event_data.csv"
    
    config = {
        "logo": constants.TEAM_INFO[team_name]["logo"],
        "t1": player_name,
        "t2": "RLCS 24 | WORLD CHAMPIONSHIP",
        "t3": "EVENT PERFORMANCE (PER 5:00)",
        "region": utils.get_region_label(region),
        "c1": constants.TEAM_INFO[team_name]["c1"],
        "c2": constants.TEAM_INFO[team_name]["c2"],
        "img_path": os.path.join("viz", "images", base_path, "Radars")
    }
    create_image(config, player_name, event_name, data_path)
    
    return 0
  
if __name__ == "__main__":
    main()