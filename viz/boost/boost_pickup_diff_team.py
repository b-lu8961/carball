from viz import constants, utils

import os
from PIL import Image, ImageDraw

IMAGE_X, IMAGE_Y = 2350, 1800
MARGIN = 40

MARKER_SIZE = 20
MID_X, MID_Y = (constants.MAP_Y + (MARGIN * 4)) / 2, (constants.MAP_X + (MARGIN * 2)) / 2

WHITE, BLACK = (255,255,255), (0,0,0)
LIGHT_GREY, DARK_GREY = (140,140,140), (70,70,70)

def get_y(val, img_height):
    return img_height - val

def calculate_diffs(game_list):
    data = {}
    id_map = {}
    locations = {}
    for game in game_list:
        for player in game.players:
            if player.id.id not in id_map:
                id_map[player.id.id] = player.is_orange

        for pad in game.game_stats.boost_pads:
            data[pad.label] = {
                'diff': 0,
                0: 0,
                1: 0
            }
            locations[pad.label] = {
                "pos_x": pad.pos_x,
                "pos_y": pad.pos_y,
                "big": pad.big
            }
            for pickup in pad.pickups:
                is_orange = id_map[pickup.player_id.id]
                data[pad.label][is_orange] += 1
                diff = -1 if is_orange else 1
                data[pad.label]['diff'] += diff

    return data, locations

def draw_field(game_list):
    pickup_map, locations = calculate_diffs(game_list)
    max_diff = max([abs(loc['diff']) for loc in pickup_map.values()])
    blue_total = sum([loc[False] for loc in pickup_map.values()])
    orange_total = sum([loc[True] for loc in pickup_map.values()])

    width, height = round(constants.MAP_Y) + (MARGIN * 4), round(constants.MAP_X) + (MARGIN * 2)
    img = Image.new(mode="RGBA", size = (width, height), color=WHITE)

    draw = ImageDraw.Draw(img)
    utils.draw_field_lines(draw, MARGIN, height)

    for label in locations.keys():
        loc = locations[label]
        pad = pickup_map[label]
        loc_x, loc_y = MID_X + loc['pos_y'] / constants.SCALE, MID_Y + loc['pos_x'] / constants.SCALE
        radius = 35 if loc['big'] else 20
        lower = 40 if loc['big'] else 25
        
        if pad['diff'] < 0:
            color_str = f"hsl(19, 82%, {100 - (50 * ((-1 * pad['diff']) / max_diff))}%)"
        else:
            color_str = f"hsl(205, 64%, {100 - (50 * (pad['diff'] / max_diff))}%)"
        draw.ellipse([
            (loc_x - radius, get_y(loc_y + radius, height)), (loc_x + radius, get_y(loc_y - radius, height))
        ], fill=color_str, outline=DARK_GREY, width=2)
        text_len = draw.textlength(f"{pad[False]}:{pad[True]}", font=constants.BOUR_40)
        draw.text((loc_x - (text_len / 2), get_y(loc_y - lower, height)), 
            f"{pad[False]}:{pad[True]}", fill=BLACK, font=constants.BOUR_40)
    

    return img, (blue_total, orange_total)

def create_image(team_names, game_list, config):
    img = Image.new(mode = "RGBA", size = (IMAGE_X, IMAGE_Y), color = WHITE)
    draw = ImageDraw.Draw(img)
    
    # Logo in top left
    logo_width, _ = utils.draw_team_logo(img, MARGIN, config["logo"])

    # Main field image
    field_image, totals = draw_field(game_list)
    field_left = round((IMAGE_X / 2) - (field_image.width / 2))
    field_right = round((IMAGE_X / 2) + (field_image.width / 2))
    img.paste(field_image, (field_left, get_y(field_image.height + MARGIN, IMAGE_Y)))

    # Title text
    utils.draw_title_text(draw, logo_width, MARGIN, config, constants.BOUR_80, constants.BOUR_40)

    # Pickup totals
    total_len = draw.textlength(f"{totals[0]}:{totals[1]}", font=constants.BOUR_50)
    blue_len = draw.textlength(str(totals[0]), font=constants.BOUR_50)
    total_left = ((IMAGE_X - total_len) / 2) - 1
    draw.text((total_left, get_y(field_image.height + (1.5 * MARGIN), IMAGE_Y)), 
        f"{totals[0]}", fill=constants.TEAM_INFO["RL ESPORTS"]["c1"], font=constants.BOUR_50)
    draw.text((total_left + blue_len, get_y(field_image.height + (1.5 * MARGIN), IMAGE_Y)), 
        ":", fill=DARK_GREY, font=constants.BOUR_50)
    draw.text((total_left + blue_len + 14, get_y(field_image.height + (1.5 * MARGIN), IMAGE_Y)), 
        f"{totals[1]}", fill=constants.TEAM_INFO["RL ESPORTS"]["c2"], font=constants.BOUR_50)

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
        img.paste(rot_img, (x_pos, get_y(round(((field_image.height + (2 * MARGIN)) / 2) + (name_len / 2)), IMAGE_Y)))


    # Dotted circle logo
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    
    img.save(os.path.join("viz", "images", config["img_name"]))

def main():
    team_names = ("FALCONS", "FEARLESS")
    key = "RL ESPORTS"
    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": f"{team_names[0]} 3 - 0 {team_names[1]}",
        "t2": "RLCS 24 MAJOR 1 | MENA OQ 1 | SWISS R3",
        "t3": "BOOST PICKUPS",
        "c1": constants.TEAM_INFO[key]["c1"],
        "c2": constants.TEAM_INFO[key]["c2"],
        "img_name": os.path.join("RLCS 24", "MENA",  "boost", f"{team_names[0].lower()}_{team_names[1].lower()}_boost.png")
    }

    data_path = os.path.join("replays", "RLCS 24", "Major 1", "MENA", "OQ 1", "Swiss", "Round 3", "FEAR vs FLCN")
    game_list = utils.read_series_data(data_path)
    create_image(team_names, game_list, config)
    
    return 1
  
if __name__ == "__main__":
    main()