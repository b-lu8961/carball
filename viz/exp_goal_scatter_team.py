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

def calculate_metrics(game_lists):
    goal_data = {}
    for region in game_lists:
        region_list = game_lists[region]
        for game in region_list:
            for team in game.teams:
                name = utils.get_team_label(team.name)
                
                if name not in goal_data:
                    goal_data[name] = {
                        "region": region,
                        "games_played": 0,
                        "seconds_played": 0,
                        "xG_for": 0,
                        "xG_against": 0
                    }
                goal_data[name]["games_played"] += 1
                goal_data[name]["seconds_played"] += game.game_metadata.seconds

            for shot in game.game_metadata.shot_details:
                xG_val = utils.get_xG_val(game, shot)

                for_team = [team for team in game.teams if team.is_orange == shot.is_orange][0]
                for_name = utils.get_team_label(for_team.name)
                goal_data[for_name]["xG_for"] += xG_val

                against_team = [team for team in game.teams if team.is_orange != shot.is_orange][0]
                against_name = utils.get_team_label(against_team.name)
                goal_data[against_name]["xG_against"] += xG_val
                
    
    return goal_data

def draw_scatter(game_lists, config):
    metrics = calculate_metrics(game_lists)
    print(len(metrics))
    #print(sorted(metrics))
    for_data = [round(np.sum(metrics[name]["xG_for"]) / (metrics[name]["seconds_played"] / 300), 3) for name in metrics]
    against_data = [round(np.sum(metrics[name]["xG_against"]) / (metrics[name]["seconds_played"] / 300), 3) for name in metrics]
    # for name in sorted(metrics):
    #     print(
    #         "{:<12}".format(name),
    #         metrics[name]['games_played'],
    #         "{:<7}".format(round(np.median(metrics[name]["time_after_ko"]), 3)),
    #         round(np.median(metrics[name]["time_in_off_half"]), 3)
    #     )
    bounds_x = (min(0.75, (round(min(for_data) * 10) / 10) - 0.1), max(3.1, 0.1 + (round(max(for_data) * 10) / 10)))
    bounds_y = (min(0.75, (round(min(against_data) * 10) / 10) - 0.1), max(3.1, 0.1 + (round(max(against_data) * 10) / 10)))
    #print(bounds_x, bounds_y)

    ax_pad = 5 * MARGIN
    tick_px_x, tick_px_y = 300, 250
    tick_jump_x, tick_jump_y = 0.5, 0.5
    plot_width = round((bounds_x[1] - bounds_x[0]) / tick_jump_x) * tick_px_x
    plot_height = round((bounds_y[1] - bounds_y[0]) / tick_jump_y) * tick_px_y
    width, height = plot_width + ax_pad + MARGIN, plot_height + ax_pad + MARGIN
    img = Image.new(mode="RGBA", size = (width, height), color=WHITE)
    
    draw = ImageDraw.Draw(img)
    draw.line([
        (ax_pad, MARGIN), (ax_pad, height - ax_pad), (width - MARGIN, height - ax_pad)
    ], fill=LIGHT_GREY, width=6)
    
    # X-axis
    draw.text((ax_pad + (plot_width / 2), get_y(ax_pad - (1.75 * MARGIN), height)), 
        "xG For per 5:00", fill=DARK_GREY, font=constants.BOUR_60, anchor='ma')
    for i in np.arange(round(bounds_x[0] * 10) / 10, bounds_x[1], (tick_jump_x / 5)):
        val = round(i * 10) / 10
        pos_x = ax_pad + (((val - bounds_x[0]) / (bounds_x[1] - bounds_x[0])) * plot_width)
        pos_y = get_y(ax_pad, height)
        draw.line([(pos_x, pos_y - 5), (pos_x, pos_y + 5)], fill=DARK_GREY, width=2)
        if int(val * 10) % 5 == 0:
            draw.text((pos_x, pos_y + (0.5 * MARGIN)), "{:.1f}".format(val), fill=DARK_GREY, font=constants.BOUR_40, anchor="ma")
    
    # Y-axis
    y_label_len = round(draw.textlength("xG Against Per 5:00", constants.BOUR_60))
    y_label_img = Image.new("RGB", size=(y_label_len, 60), color=WHITE)
    y_label_draw = ImageDraw.Draw(y_label_img)
    y_label_draw.text((0, 0), "xG Against per 5:00", fill=DARK_GREY, font=constants.BOUR_60)
    y_label_rot = y_label_img.rotate(90, expand=True)
    img.paste(y_label_rot, (ax_pad - int((3.5 * MARGIN)), get_y(ax_pad + int(plot_height / 2) + int(y_label_len / 2), height)))
    for i in np.arange(round(bounds_y[0] * 10) / 10, bounds_y[1], (tick_jump_y / 5)):
        val = round(i * 10) / 10
        pos_y = get_y(ax_pad + (((val - bounds_y[0]) / (bounds_y[1] - bounds_y[0])) * plot_height), height)
        draw.line([(ax_pad - 5, pos_y), (ax_pad + 5, pos_y)], fill=DARK_GREY, width=2)
        if int(val * 10) % 5 == 0:
            draw.text((ax_pad - (1.75 * MARGIN), pos_y), "{:.1f}".format(val), fill=DARK_GREY, font=constants.BOUR_40, anchor="lm")

    # Plot elements
    # Top left style label
    tl_text = "Bad Offense,\nBad Defense"
    tl_pos = (ax_pad + MARGIN, get_y(plot_height + ax_pad - (1 * MARGIN), height))
    tl_bbox = draw.multiline_textbbox(tl_pos, tl_text, font=constants.BOUR_50, align="center")
    draw.rounded_rectangle([tl_bbox[0] - 8, tl_bbox[1] - 8, tl_bbox[2] + 8, tl_bbox[3] + 8], 10, fill=config["c3"])
    draw.text(tl_pos, tl_text, fill=WHITE, font=constants.BOUR_50, align="center")
    
    # Bottom right style label
    br_text = "Good Offense,\nGood Defense"
    br_text_len = draw.textlength("Good Offense,", font=constants.BOUR_50)
    br_pos = (width - br_text_len - MARGIN, get_y(ax_pad + (3 * MARGIN), height))
    br_bbox = draw.multiline_textbbox(br_pos, br_text, font=constants.BOUR_50, align="center")
    draw.rounded_rectangle([br_bbox[0] - 8, br_bbox[1] - 8, br_bbox[2] + 8, br_bbox[3] + 8], 10, fill=config["c3"])
    draw.multiline_text(br_pos, br_text, fill=WHITE, font=constants.BOUR_50, align="center")

    # Median lines
    for_pos = ax_pad + (((np.median(for_data) - bounds_x[0]) / (bounds_x[1] - bounds_x[0])) * plot_width)
    utils.linedashed(draw, LIGHT_GREY, 3, for_pos, for_pos, get_y(height - MARGIN, height), get_y(ax_pad, height))
    draw.multiline_text((for_pos - 15, MARGIN), "Median\nxG For", 
        fill=LIGHT_GREY, font=constants.BOUR_30, align="right", anchor="ra")

    against_pos = get_y(ax_pad + (((np.median(against_data) - bounds_y[0]) / (bounds_y[1] - bounds_y[0])) * plot_height), height)
    utils.linedashed(draw, LIGHT_GREY, 3, ax_pad, width - MARGIN, against_pos, against_pos)
    draw.multiline_text((ax_pad + MARGIN, against_pos - 35), "Median xG\nAgainst", 
        fill=LIGHT_GREY, font=constants.BOUR_30, align="center", spacing=15)

    # Player points
    for name in metrics:
        radius = 15
        val_x = np.sum(metrics[name]["xG_for"]) / (metrics[name]["seconds_played"] / 300)
        val_y = np.sum(metrics[name]["xG_against"]) / (metrics[name]["seconds_played"] / 300)
        #print(name, val_x, val_y)
        pos_x = ax_pad + (((val_x - bounds_x[0]) / (bounds_x[1] - bounds_x[0])) * plot_width)
        pos_y = get_y(ax_pad + (((val_y - bounds_y[0]) / (bounds_y[1] - bounds_y[0])) * plot_height), height)
        colors = constants.REGION_COLORS[metrics[name]["region"]]
        draw.ellipse([(pos_x - radius, pos_y - radius), (pos_x + radius, pos_y + radius)], fill=colors[0], outline=colors[1], width=2)
        
        if name in ["TN", "OG ESPORTS", "UHUH", "FIRE HAWKS"]:
            utils.draw_scatter_label(draw, name, pos_x, pos_y, radius, "u")
        elif name in ["MUFFIN MEN", "CVENT"]:
            utils.draw_scatter_label(draw, name, pos_x, pos_y, radius, "d")
        elif name in ["HERO BASE", "INFINITY", "OBLIVIONE", "NRG", "LUMINOSITY", "THAT'S CRAZY", "DETONATOR", "ELITES", "BONJOUR", "LES PONEYS"]:
            utils.draw_scatter_label(draw, name, pos_x, pos_y, radius, "r")
        else:
            utils.draw_scatter_label(draw, name, pos_x, pos_y, radius, "l")

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
    region = "SAM"
    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": "TEAM xG PERFORMANCE",
        "t2": f"RLCS 24 {region} | OQ 1 | SWISS",
        "t3": "",
        "c1": constants.TEAM_INFO[key]["c1"],
        "c2": constants.TEAM_INFO[key]["c2"],
        "c3": constants.REGION_COLORS[region][0],
        "img_name": os.path.join("RLCS 24", region, "scatter", "OQ1_xG_perf.png")
    }

    if region == "APAC":
        apac_path = os.path.join("replays", "RLCS 24", "Major 1", "Asia-Pacific", "Open Qualifiers 1", "Day 3 - Swiss Stage")
        game_list = utils.read_group_data(apac_path)
    elif region == "EU":
        eu_path = os.path.join("replays", "RLCS 24", "Major 1", "Europe", "Open Qualifiers 1", "Day 3 - Swiss Stage")
        game_list = utils.read_group_data(eu_path)
    elif region == "MENA":
        mena_path = os.path.join("replays", "RLCS 24", "Major 1", "Middle East & North Africa", "Open Qualifiers 1", "Day 3 - Swiss Stage")
        game_list = utils.read_group_data(mena_path)
    elif region == "NA":
        na_path = os.path.join("replays", "RLCS 24", "Major 1", "North America", "Open Qualifiers 1", "Day 3 - Swiss Stage")
        game_list = utils.read_group_data(na_path)
    elif region == "OCE":
        oce_path = os.path.join("replays", "RLCS 24", "Major 1", "Oceania", "Open Qualifiers 1", "Day 3 - Swiss Stage")
        game_list = utils.read_group_data(oce_path)
    elif region == "SAM":
        sam_path = os.path.join("replays", "RLCS 24", "Major 1", "South America", "Open Qualifiers 1", "Day 3 - Swiss Stage")
        game_list = utils.read_group_data(sam_path)
    else:
        ssa_path = os.path.join("replays", "RLCS 24", "Major 1", "Sub-Saharan Africa", "Open Qualifiers 1", "Day 3 - Swiss Stage")
        game_list = utils.read_group_data(ssa_path)
    create_image({region: game_list}, config)
    
    return 1
  
if __name__ == "__main__":
    main()