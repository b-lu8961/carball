from viz import constants, utils

import math, os
from PIL import Image, ImageDraw

IMAGE_X, IMAGE_Y = 1900, 2100
MARGIN = 40

MARKER_SIZE = 20
MID_X, MID_Y = (constants.MAP_Y + (MARGIN * 4)) / 2, (constants.MAP_X + (MARGIN * 2)) / 2

WHITE, BLACK = (255,255,255), (0,0,0)
LIGHT_GREY, DARK_GREY = (140,140,140), (70,70,70)

def get_y(val, img_height):
    return img_height - val

def calculate_results(game_list):
    data = {}
    for game in game_list:
        for player in game.players:
            key = (player.is_orange, player.name)
            if key not in data:
                data[key] = [0, 0, 0]
            data[key][0] += player.stats.hit_counts.self_next
            data[key][1] += player.stats.hit_counts.team_next
            data[key][2] += player.stats.hit_counts.oppo_next

    return data

def create_image(team_keys, game_list, config):
    img = Image.new(mode = "RGBA", size = (IMAGE_X, IMAGE_Y), color = WHITE)
    draw = ImageDraw.Draw(img)

    # Team info
    draw.text(((IMAGE_X / 2 - 400), 300), team_keys[0], fill=constants.TEAM_INFO["RL ESPORTS"]["c1"], font=constants.BOUR_80, anchor="ma")
    draw.text(((IMAGE_X / 2 + 400), 300), team_keys[1], fill=constants.TEAM_INFO["RL ESPORTS"]["c2"], font=constants.BOUR_80, anchor="ma")

    # Player touch results
    self_color, team_color, oppo_color = (50,250,50), (50,50,250), (250,50,50)
    touch_results = calculate_results(game_list)
    blue_count, orange_count = 0, 0
    pad = 520
    for key in sorted(touch_results, key=lambda k: (k[0], str.casefold(k[1]))):
        pl_data = touch_results[key]
        orig, radius = ((IMAGE_X / 2) - 400, 675 + (pad * blue_count)) if key[0] == 0 else ((IMAGE_X / 2) + 400, 675 + (pad * orange_count)), 150
        bbox = [(orig[0] - radius, orig[1] - radius), (orig[0] + radius, orig[1] + radius)]
        
        draw.text((orig[0], orig[1] - radius - 20), key[1], fill=BLACK, font=constants.BOUR_50, anchor="md")
        draw.text((orig[0], orig[1] + radius + 30), f"{sum(pl_data)} touches", fill=DARK_GREY, font=constants.BOUR_40, anchor="ma")

        s_base = pl_data[0] / sum(pl_data)
        s_deg = (s_base * 360) - 90
        s_rad = ((s_deg + -90) / 2 / 360) * 2 * math.pi 
        s_point = (orig[0] + (radius * math.cos(s_rad)), orig[1] + (radius * math.sin(s_rad)))
        draw.text(s_point, "{:.1f}%".format(s_base * 100), fill=DARK_GREY, font=constants.BOUR_40, anchor="ld")
        draw.pieslice(bbox, -90, s_deg, fill=self_color)

        t_base = pl_data[1] / sum(pl_data)
        t_deg = (t_base * 360) + s_deg
        t_rad = ((t_deg + s_deg) / 2 / 360) * 2 * math.pi 
        t_point = (orig[0] + (radius * math.cos(t_rad)), orig[1] + (radius * math.sin(t_rad)))
        draw.text(t_point, "{:.1f}%".format(t_base * 100), fill=DARK_GREY, font=constants.BOUR_40, anchor="la")
        draw.pieslice(bbox, s_deg, t_deg, fill=team_color)

        o_base = pl_data[2] / sum(pl_data)
        o_deg = (o_base * 360) + t_deg
        o_rad = ((o_deg + t_deg) / 2 / 360) * 2 * math.pi 
        o_point = (orig[0] + (radius * math.cos(o_rad)), orig[1] + (radius * math.sin(o_rad)))
        draw.text((o_point[0] - 5, o_point[1]), "{:.1f}%".format(o_base * 100), fill=DARK_GREY, font=constants.BOUR_40, anchor="ra")
        draw.pieslice(bbox, t_deg, o_deg, fill=oppo_color)
        
        if key[0] == 0:
            blue_count += 1
        else:
            orange_count += 1
    
    # Legend text
    draw.text((IMAGE_X / 2, IMAGE_Y - 100), "Next touch:          - Self   |          - Teammate   |          - Opponent", 
        fill=DARK_GREY, font=constants.BOUR_50, anchor="ma")
    draw.rounded_rectangle([(630, IMAGE_Y - 100), (680, IMAGE_Y - 50)], 10, fill=self_color)
    draw.rounded_rectangle([(865, IMAGE_Y - 100), (915, IMAGE_Y - 50)], 10, fill=team_color)
    draw.rounded_rectangle([(1230, IMAGE_Y - 100), (1280, IMAGE_Y - 50)], 10, fill=oppo_color)
    
    # Logo in top left
    logo_width, _ = utils.draw_team_logo(img, MARGIN, config["logo"])

    # Title text
    utils.draw_title_text(draw, logo_width, MARGIN, config, constants.BOUR_80, constants.BOUR_40)

    # Dotted circle logo
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    
    os.makedirs(config["img_path"], exist_ok=True)
    img.save(os.path.join(config["img_path"], "touch_results.png"))

def main():
    team_keys = ["MOIST ESPORTS", "TEAM VITALITY"]
    event = "RL ESPORTS"
    base_path = os.path.join("RLCS 24", "Major 1", "Europe", "Open Qualifiers 1", "Day 4 - Single Elimination Stage", "VIT vs MST")

    config = {
        "logo": constants.TEAM_INFO[event]["logo"],
        "t1": f"{team_keys[0]} 1 - 4 {team_keys[1]}",
        "t2": "RLCS 24 EU | OQ 1 | QUARTERFINAL",
        "t3": "TOUCH RESULTS",
        "c1": constants.TEAM_INFO[event]["c1"],
        "c2": constants.TEAM_INFO[event]["c2"],
        "img_path": os.path.join("viz", "images", base_path, "touches"),
    }

    data_path = os.path.join("replays", base_path)
    game_iter = utils.read_series_data(data_path)
    create_image(team_keys, game_iter, config)
    
    return 1
  
if __name__ == "__main__":
    main()