from viz import constants, utils

import numpy as np
import os
from PIL import Image, ImageDraw

HEADER_HEIGHT = 250
MARGIN = 40

MARKER_SIZE = 15
MID_X, MID_Y = (constants.MAP_Y + (MARGIN * 4)) / 2, (constants.MAP_X + (MARGIN * 2)) / 2

WHITE, BLACK = (255,255,255), (0,0,0)
LIGHT_GREY, DARK_GREY = (140,140,140), (70,70,70)

def get_y(val, img_height):
    return img_height - val

def calculate_metrics(game_list):
    boost_data = {}

    for game in game_list:        
        for player in game.players:
            name = utils.get_player_label(player.name)
            if name not in boost_data:
                boost_data[name] = {
                    "games_played": 0,
                    "seconds_played": 0,
                    "boost_usage": [],
                    "sb_ratio": [],
                    "avg_boost": [],
                    "time_empty": []
                }
            boost_data[name]["games_played"] += 1
            boost_data[name]["seconds_played"] += game.game_metadata.seconds
            boost_data[name]["boost_usage"].append(player.stats.boost.boost_usage)
            boost_data[name]["sb_ratio"].append(player.stats.boost.num_small_boosts / player.stats.boost.num_large_boosts)
            boost_data[name]["avg_boost"].append(player.stats.boost.average_boost_level)
            boost_data[name]["time_empty"].append(player.stats.boost.time_no_boost)
    
    return boost_data

def draw_scatter(game_list, config):
    metrics = calculate_metrics(game_list)
    bu_data = [round(np.sum(metrics[name]["boost_usage"]) / (metrics[name]['seconds_played'] / 300), 3) for name in metrics]
    sb_data = [round(np.mean(metrics[name]["sb_ratio"]), 3) for name in metrics]
    # for name in metrics:
    #     print(
    #         "{:<10}".format(name),
    #         "{:<7}".format(round(np.mean(metrics[name]["time_after_ko"]), 3)),
    #         round(np.mean(metrics[name]["time_in_off_half"]), 3)
    #     )
    pad_x = 50
    bounds_x = (int(round((min(bu_data) - (1.5 * pad_x)) / pad_x) * pad_x), int(round((max(bu_data) + (0.75 * pad_x)) / pad_x) * pad_x))
    bounds_y = (min(sb_data) - 0.5, max(sb_data) + 0.5)

    ax_pad = 5 * MARGIN
    tick_px_x, tick_px_y = 300, 250
    tick_jump_x, tick_jump_y = 100, 0.5
    plot_width = round((bounds_x[1] - bounds_x[0]) / tick_jump_x) * tick_px_x
    plot_height = round((bounds_y[1] - bounds_y[0]) / tick_jump_y) * tick_px_y
    width, height = plot_width + ax_pad + MARGIN, plot_height + ax_pad + MARGIN
    img = Image.new(mode="RGBA", size = (width, height), color=WHITE)
    
    draw = ImageDraw.Draw(img)
    draw.line([
        (ax_pad, MARGIN), (ax_pad, height - ax_pad), (width - MARGIN, height - ax_pad)
    ], fill=LIGHT_GREY, width=6)
    
    # X-axis
    x_label_len = draw.textlength("Boost Usage Per 5:00", font=constants.BOUR_60)
    draw.text((ax_pad + (plot_width / 2) - (x_label_len / 2), get_y(ax_pad - (2 * MARGIN), height)), 
        "Boost Usage Per 5:00", fill=DARK_GREY, font=constants.BOUR_60)
    for i in range(int(np.ceil(bounds_x[0])), int(bounds_x[1]) + 1, tick_jump_x):
        num_len = draw.textlength(str(i), font=constants.BOUR_40)
        pos_x = ax_pad + (((i - bounds_x[0]) / (bounds_x[1] - bounds_x[0])) * plot_width)
        draw.text((pos_x - (num_len / 2), get_y(ax_pad - (0.5 * MARGIN), height)), str(i), fill=DARK_GREY, font=constants.BOUR_40)
    
    # Y-axis
    y_label_len = round(draw.textlength("Small to Big Boost Pickup Ratio", constants.BOUR_60))
    y_label_img = Image.new("RGB", size=(y_label_len, 60), color=WHITE)
    y_label_draw = ImageDraw.Draw(y_label_img)
    y_label_draw.text((0, 0), "Small to Big Boost Pickup Ratio", fill=DARK_GREY, font=constants.BOUR_60)
    y_label_rot = y_label_img.rotate(90, expand=True)
    img.paste(y_label_rot, (ax_pad - int((3.5 * MARGIN)), get_y(ax_pad + int(plot_height / 2) + int(y_label_len / 2), height)))
    for i in np.arange(int(np.ceil(bounds_y[0])), int(bounds_y[1]) + 1, tick_jump_y):
        pos_y = get_y(ax_pad + (((i - bounds_y[0]) / (bounds_y[1] - bounds_y[0])) * plot_height), height)
        draw.text((ax_pad - (1.5 * MARGIN), pos_y - 20), str(i), fill=DARK_GREY, font=constants.BOUR_40)

    # Plot elements
    #Top left style label
    tl_text = "Favors Small Pads,\nBoost Light"
    tl_pos = (ax_pad + MARGIN, get_y(plot_height + MARGIN, height))
    tl_bbox = draw.multiline_textbbox(tl_pos, tl_text, font=constants.BOUR_50, align="center")
    draw.rounded_rectangle([tl_bbox[0] - 8, tl_bbox[1] - 8, tl_bbox[2] + 8, tl_bbox[3] + 8], 10, fill=config["colors"][0])
    draw.text(tl_pos, tl_text, fill=WHITE, font=constants.BOUR_50, align="center")
    
    # Bottom right style label
    br_text = "Favors Big Pads,\nBoost Heavy"
    br_text_len = draw.textlength("Quick Attacks,", font=constants.BOUR_50)
    br_pos = (width - br_text_len - MARGIN, get_y(ax_pad + (3 * MARGIN), height))
    br_bbox = draw.multiline_textbbox(br_pos, br_text, font=constants.BOUR_50, align="center")
    draw.rounded_rectangle([br_bbox[0] - 8, br_bbox[1] - 8, br_bbox[2] + 8, br_bbox[3] + 8], 10, fill=config['colors'][0])
    draw.multiline_text(br_pos, br_text, fill=WHITE, font=constants.BOUR_50, align="center")

    # Median lines
    bu_pos = ax_pad + (((np.median(bu_data) - bounds_x[0]) / (bounds_x[1] - bounds_x[0])) * plot_width)
    utils.linedashed(draw, LIGHT_GREY, 3, bu_pos, bu_pos, get_y(height - MARGIN, height), get_y(ax_pad, height))
    draw.multiline_text((bu_pos - 15, MARGIN), "Median Boost\nUsage", 
        fill=LIGHT_GREY, font=constants.BOUR_30, align="right", anchor="ra")

    sb_pos = get_y(ax_pad + (((np.median(sb_data) - bounds_y[0]) / (bounds_y[1] - bounds_y[0])) * plot_height), height)
    utils.linedashed(draw, LIGHT_GREY, 3, ax_pad, width - MARGIN, sb_pos, sb_pos)
    draw.multiline_text((ax_pad + MARGIN, sb_pos - 35), "Median Small-Big\nPickup Ratio", 
        fill=LIGHT_GREY, font=constants.BOUR_30, align="center", spacing=15)

    # Player points
    for name in metrics:
        radius = 15
        val_x, val_y = np.sum(metrics[name]["boost_usage"]) / (metrics[name]['seconds_played'] / 300), np.mean(metrics[name]["sb_ratio"])
        pos_x = ax_pad + (((val_x - bounds_x[0]) / (bounds_x[1] - bounds_x[0])) * plot_width)
        pos_y = get_y(ax_pad + (((val_y - bounds_y[0]) / (bounds_y[1] - bounds_y[0])) * plot_height), height)
        draw.ellipse([(pos_x - radius, pos_y - radius), (pos_x + radius, pos_y + radius)], fill=config['colors'][0], 
            outline=config['colors'][1], width=2)

        if name in ['sosa', 'CHEESE.', 'Joreuz', 'Realize ;)', 'Chicago', 'justin.']:
            utils.draw_scatter_label(draw, name, pos_x, pos_y, radius, 'r')
        else:
            utils.draw_scatter_label(draw, name, pos_x, pos_y, radius, 'l')

    print(len(metrics))
    #print([(name, metrics[name]['seconds_played'] / metrics[name]['games_played']) for name in metrics])
    return img

def create_image(game_lists, config):
    scatter_img = draw_scatter(game_lists, config)
    
    IMAGE_X, IMAGE_Y = scatter_img.width + (3 * MARGIN), scatter_img.height + HEADER_HEIGHT + MARGIN
    img = Image.new(mode="RGBA", size=(IMAGE_X, IMAGE_Y), color=WHITE)
    draw = ImageDraw.Draw(img)
    
    # Logo in top left
    logo_width, _ = utils.draw_team_logo(img, MARGIN, config["logo"])

    # Title text
    utils.draw_title_text(draw, logo_width, MARGIN, config, constants.BOUR_80, constants.BOUR_40)

    
    img.paste(scatter_img, (MARGIN, HEADER_HEIGHT))

    # Dotted circle logo
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    
    img.save(os.path.join("viz", "images", config["img_name"]))

def main():
    key = "RL ESPORTS"
    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": "BOOST STYLE COMPARISON",
        "t2": "RLCS NA | OQ 1 | SWISS",
        "t3": "",
        "c1": constants.TEAM_INFO[key]['c1'],
        "c2": constants.TEAM_INFO[key]['c2'],
        "colors": constants.REGION_COLORS['NA'],
        "img_name": os.path.join("RLCS 24", "NA", "scatter", "OQ_1_boost_style.png")
    }

    data_path = os.path.join("replays", "RLCS 24", "Major 1", "North America", "Open Qualifiers 1", "Day 3 - Swiss Stage")
    game_list = utils.read_group_data(data_path)
    create_image(game_list, config)
    
    return 1
  
if __name__ == "__main__":
    main()