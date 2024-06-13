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
    totals = {"goals_scored": 0, "time_in_off_half": [], "cons_touches": [], "time_after_ko": []}
    for region in game_lists:
        region_list = game_lists[region]
        for game in region_list:
            for team in game.teams:
                name = utils.get_team_label(team.name, region)
                if name not in goal_data:
                    goal_data[name] = {
                        "region": region,
                        "games_played": 0,
                        "goals_scored": 0,
                        "time_in_off_half": [],
                        "cons_touches": [],
                        "time_after_ko": []
                    }
                goal_data[name]["games_played"] += 1

            for curr_goal in game.game_metadata.goals:
                name = utils.get_team_label(curr_goal.team_name, region)
                
                goal_data[name]["goals_scored"] += 1
                goal_data[name]["time_in_off_half"].append(curr_goal.time_in_off_half)
                goal_data[name]["cons_touches"].append(curr_goal.cons_team_touches)
                goal_data[name]["time_after_ko"].append(curr_goal.time_after_kickoff)

                totals["goals_scored"] += 1
                totals["time_in_off_half"].append(curr_goal.time_in_off_half)
                totals["cons_touches"].append(curr_goal.cons_team_touches)
                totals["time_after_ko"].append(curr_goal.time_after_kickoff)
    
    return goal_data, totals

def draw_scatter(game_lists, config):
    metrics, totals = calculate_metrics(game_lists)
    #print(len(metrics))
    ko_med_list = [round(np.median(metrics[name]["time_after_ko"]), 3) for name in metrics]
    oh_med_list = [round(np.median(metrics[name]["time_in_off_half"]), 3) for name in metrics]
    # for name in sorted(metrics):
    #     print(
    #         "{:<15}".format(name),
    #         metrics[name]['games_played'],
    #         "{:<7}".format(round(np.median(metrics[name]["time_after_ko"]), 3)),
    #         round(np.median(metrics[name]["time_in_off_half"]), 3)
    #     )
    #print(metrics["KARMINE CORP"])
    bounds_x = (min(ko_med_list) - 1, max(ko_med_list) + 1)
    bounds_y = (min(oh_med_list) - 1, max(oh_med_list) + 1)

    ax_pad = 5 * MARGIN
    tick_px_x, tick_px_y = 300, 250
    tick_jump_x, tick_jump_y = 5, 1
    plot_width = round((bounds_x[1] - bounds_x[0]) / tick_jump_x) * tick_px_x
    plot_height = round((bounds_y[1] - bounds_y[0]) / tick_jump_y) * tick_px_y
    width, height = plot_width + ax_pad + MARGIN, plot_height + ax_pad + MARGIN
    img = Image.new(mode="RGBA", size = (width, height), color=WHITE)
    
    draw = ImageDraw.Draw(img)
    draw.line([
        (ax_pad, MARGIN), (ax_pad, height - ax_pad), (width - MARGIN, height - ax_pad)
    ], fill=LIGHT_GREY, width=6)
    
    # X-axis
    x_label_len = draw.textlength("Seconds after Kickoff", font=constants.BOUR_60)
    draw.text((ax_pad + (plot_width / 2) - (x_label_len / 2), get_y(ax_pad - (2 * MARGIN), height)), 
        "Seconds after Kickoff", fill=DARK_GREY, font=constants.BOUR_60)
    for i in range(int(np.ceil(bounds_x[0])), int(bounds_x[1]) + 1, tick_jump_x):
        num_len = draw.textlength(str(i), font=constants.BOUR_40)
        pos_x = ax_pad + (((i - bounds_x[0]) / (bounds_x[1] - bounds_x[0])) * plot_width)
        draw.text((pos_x - (num_len / 2), get_y(ax_pad - (0.5 * MARGIN), height)), str(i), fill=DARK_GREY, font=constants.BOUR_40)
    
    # Y-axis
    y_label_len = round(draw.textlength("Ball Time in Off. Half  (s)", constants.BOUR_60))
    y_label_img = Image.new("RGB", size=(y_label_len, 60), color=WHITE)
    y_label_draw = ImageDraw.Draw(y_label_img)
    y_label_draw.text((0, 0), "Ball Time in Off. Half  (s)", fill=DARK_GREY, font=constants.BOUR_60)
    y_label_rot = y_label_img.rotate(90, expand=True)
    img.paste(y_label_rot, (ax_pad - int((3.5 * MARGIN)), get_y(ax_pad + int(plot_height / 2) + int(y_label_len / 2), height)))
    for i in range(int(np.ceil(bounds_y[0])), int(bounds_y[1]) + 1, tick_jump_y):
        pos_y = get_y(ax_pad + (((i - bounds_y[0]) / (bounds_y[1] - bounds_y[0])) * plot_height), height)
        draw.text((ax_pad - (1 * MARGIN), pos_y - 20), str(i), fill=DARK_GREY, font=constants.BOUR_40, anchor="ma")

    # Plot elements
    # Top left style label
    tl_text = "Sustained Pressure,\nKickoff Plays"
    tl_pos = (ax_pad + MARGIN, get_y(plot_height, height))
    tl_bbox = draw.multiline_textbbox(tl_pos, tl_text, font=constants.BOUR_50, align="center")
    draw.rounded_rectangle([tl_bbox[0] - 8, tl_bbox[1] - 8, tl_bbox[2] + 8, tl_bbox[3] + 8], 10, fill=config["c3"])
    draw.text(tl_pos, tl_text, fill=WHITE, font=constants.BOUR_50, align="center")
    
    # Bottom right style label
    br_text = "Quick Attacks,\nMidfield Plays"
    br_text_len = draw.textlength("Quick Attacks,", font=constants.BOUR_50)
    br_pos = (width - br_text_len - MARGIN, get_y(ax_pad + (3 * MARGIN), height))
    br_bbox = draw.multiline_textbbox(br_pos, br_text, font=constants.BOUR_50, align="center")
    draw.rounded_rectangle([br_bbox[0] - 8, br_bbox[1] - 8, br_bbox[2] + 8, br_bbox[3] + 8], 10, fill=config["c3"])
    draw.multiline_text(br_pos, br_text, fill=WHITE, font=constants.BOUR_50, align="center")

    # Median lines
    ko_pos = ax_pad + (((np.median(ko_med_list) - bounds_x[0]) / (bounds_x[1] - bounds_x[0])) * plot_width)
    utils.linedashed(draw, LIGHT_GREY, 3, ko_pos, ko_pos, get_y(height - MARGIN, height), get_y(ax_pad, height))
    draw.multiline_text((ko_pos - 15, MARGIN), "Median Time\nafter Kickoff", 
        fill=LIGHT_GREY, font=constants.BOUR_30, align="right", anchor="ra")

    oh_pos = get_y(ax_pad + (((np.median(oh_med_list) - bounds_y[0]) / (bounds_y[1] - bounds_y[0])) * plot_height), height)
    utils.linedashed(draw, LIGHT_GREY, 3, ax_pad, width - MARGIN, oh_pos, oh_pos)
    draw.multiline_text((ax_pad + MARGIN, oh_pos - 35), "Median Ball Time\nin Off. Half", 
        fill=LIGHT_GREY, font=constants.BOUR_30, align="center", spacing=15)

    # Player points
    for name in metrics:
        radius = 15
        val_x, val_y = np.median(metrics[name]["time_after_ko"]), np.median(metrics[name]["time_in_off_half"])
        pos_x = ax_pad + (((val_x - bounds_x[0]) / (bounds_x[1] - bounds_x[0])) * plot_width)
        pos_y = get_y(ax_pad + (((val_y - bounds_y[0]) / (bounds_y[1] - bounds_y[0])) * plot_height), height)
        reg = utils.get_region_from_team(name) #metrics[name]["region"]
        color = constants.REGION_COLORS[reg][0]
        draw.ellipse([(pos_x - radius, pos_y - radius), (pos_x + radius, pos_y + radius)], fill=color)
        name_len = draw.textlength(name, font=constants.BOUR_30)
        if name == "ELEVATE":
            name_len = -50
        draw.text((pos_x - name_len - (1.5 * radius), pos_y - (1 * radius)), name, fill=BLACK, font=constants.BOUR_30)

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
    
    os.makedirs(config["img_path"], exist_ok=True)
    img.save(os.path.join(config["img_path"], "team_goal_style.png"))

def main():
    key = "RL ESPORTS"
    region = "[1] Major"
    rn = "EU" #utils.get_region_label(region)
    base_path = os.path.join("RLCS 24", "Major 1", region)
    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": "ATTACKING STYLE COMPARISON",
        "t2": f"RLCS 24 MAJOR 1",
        "t3": "",
        "c1": constants.TEAM_INFO[key]["c1"],
        "c2": constants.TEAM_INFO[key]["c2"],
        "c3": constants.REGION_COLORS[rn][0],
        "img_path": os.path.join("viz", "images", base_path)
    }

    game_list = utils.read_group_data(os.path.join("replays", base_path))
    create_image({rn: game_list}, config)
    
    return 0
  
if __name__ == "__main__":
    main()