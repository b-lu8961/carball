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
                    rn = utils.get_region_from_team(name)
                    goal_data[name] = {
                        "region": rn,
                        "games_played": 0,
                        "seconds_played": 0,
                        "xG_for": 0,
                        "shots_for": 0,
                        "bc_for": 0
                    }
                goal_data[name]["games_played"] += 1
                goal_data[name]["seconds_played"] += game.game_metadata.seconds

            for shot in game.game_metadata.shot_details:
                xG_val = utils.get_xG_val(game, shot)

                for_team = [team for team in game.teams if team.is_orange == shot.is_orange][0]
                for_name = utils.get_team_label(for_team.name)
                goal_data[for_name]["xG_for"] += xG_val
                goal_data[for_name]["shots_for"] += 1
                if xG_val >= 0.4:
                    goal_data[for_name]["bc_for"] += 1
                
    return goal_data

def draw_scatter(game_lists, config):
    metrics = calculate_metrics(game_lists)
    print(len(metrics))
    #print(sorted(metrics))
    for_data = [round(np.sum(metrics[name]["shots_for"]) / (metrics[name]["seconds_played"] / 300), 3) for name in metrics]
    bc_data = [round(np.sum(metrics[name]["bc_for"]) / (metrics[name]["seconds_played"] / 300), 3) for name in metrics]
    for name in sorted(metrics):
        print(
            "{:<16}".format(name),
            metrics[name]['games_played'],
            metrics[name]['seconds_played'],
            "{:<7}".format(round(np.median(metrics[name]["shots_for"]), 3)),
            np.median(metrics[name]["bc_for"])
        )
    bounds_x = (min(2, (round(min(for_data) * 10) / 10) - 0.1), max(12, 0.1 + (round(max(for_data) * 10) / 10)))
    bounds_y = (min(0.75, (round(min(bc_data) * 10) / 10) - 0.1), max(2.6, 0.1 + (round(max(bc_data) * 10) / 10)))
    #print(bounds_x, bounds_y)

    ax_pad = 5 * MARGIN
    tick_px_x, tick_px_y = 350, 250
    tick_jump_x, tick_jump_y = 2, 0.5
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
        "Shots For per 5:00", fill=DARK_GREY, font=constants.BOUR_60, anchor='ma')
    for i in np.arange(round(bounds_x[0] * 10) / 10, bounds_x[1], (tick_jump_x / 5)):
        val = round(i * 10) / 10
        pos_x = ax_pad + (((val - bounds_x[0]) / (bounds_x[1] - bounds_x[0])) * plot_width)
        pos_y = get_y(ax_pad, height)
        draw.line([(pos_x, pos_y - 5), (pos_x, pos_y + 5)], fill=DARK_GREY, width=2)
        if int(val * 10) % 5 == 0:
            draw.text((pos_x, pos_y + (0.5 * MARGIN)), "{:.1f}".format(val), fill=DARK_GREY, font=constants.BOUR_40, anchor="ma")
    
    # Y-axis
    y_label_len = round(draw.textlength("Big Chances For per 5:00", constants.BOUR_60))
    y_label_img = Image.new("RGB", size=(y_label_len, 60), color=WHITE)
    y_label_draw = ImageDraw.Draw(y_label_img)
    y_label_draw.text((0, 0), "Big Chances For per 5:00", fill=DARK_GREY, font=constants.BOUR_60)
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
    tl_text = "Few High Quality\nChances Created"
    tl_pos = (ax_pad + MARGIN, get_y(plot_height + ax_pad - (3 * MARGIN), height))
    tl_bbox = draw.multiline_textbbox(tl_pos, tl_text, font=constants.BOUR_50, align="center")
    draw.rounded_rectangle([tl_bbox[0] - 8, tl_bbox[1] - 8, tl_bbox[2] + 8, tl_bbox[3] + 8], 10, fill=config["c3"])
    draw.text(tl_pos, tl_text, fill=WHITE, font=constants.BOUR_50, align="center")
    
    # Bottom right style label
    br_text = "Many Low Quality\nChances Created"
    br_text_len = draw.textlength("Many Low Quality", font=constants.BOUR_50)
    br_pos = (width - br_text_len - MARGIN, get_y(ax_pad + (3 * MARGIN), height))
    br_bbox = draw.multiline_textbbox(br_pos, br_text, font=constants.BOUR_50, align="center")
    draw.rounded_rectangle([br_bbox[0] - 8, br_bbox[1] - 8, br_bbox[2] + 8, br_bbox[3] + 8], 10, fill=config["c3"])
    draw.multiline_text(br_pos, br_text, fill=WHITE, font=constants.BOUR_50, align="center")

    # Median lines
    for_pos = ax_pad + (((np.median(for_data) - bounds_x[0]) / (bounds_x[1] - bounds_x[0])) * plot_width)
    utils.linedashed(draw, LIGHT_GREY, 3, for_pos, for_pos, get_y(height - MARGIN, height), get_y(ax_pad, height))
    draw.multiline_text((for_pos - 15, MARGIN), "Median\nShots For", 
        fill=LIGHT_GREY, font=constants.BOUR_30, align="right", anchor="ra")

    against_pos = get_y(ax_pad + (((np.median(bc_data) - bounds_y[0]) / (bounds_y[1] - bounds_y[0])) * plot_height), height)
    utils.linedashed(draw, LIGHT_GREY, 3, ax_pad, width - MARGIN, against_pos, against_pos)
    draw.multiline_text((ax_pad + MARGIN, against_pos - 35), "Median Big\nChances For", 
        fill=LIGHT_GREY, font=constants.BOUR_30, align="center", spacing=15)

    # Player points
    for name in metrics:
        radius = 15
        val_x = np.sum(metrics[name]["shots_for"]) / (metrics[name]["seconds_played"] / 300)
        val_y = np.sum(metrics[name]["bc_for"]) / (metrics[name]["seconds_played"] / 300)
        #print(name, val_x, val_y)
        pos_x = ax_pad + (((val_x - bounds_x[0]) / (bounds_x[1] - bounds_x[0])) * plot_width)
        pos_y = get_y(ax_pad + (((val_y - bounds_y[0]) / (bounds_y[1] - bounds_y[0])) * plot_height), height)
        colors = constants.REGION_COLORS[metrics[name]["region"]]
        draw.ellipse([(pos_x - radius, pos_y - radius), (pos_x + radius, pos_y + radius)], fill=colors[0], outline=colors[1], width=2)
        
        if name in []:
            utils.draw_scatter_label(draw, name, pos_x, pos_y, radius, "u")
        elif name in ["OG ESPORTS"]:
            utils.draw_scatter_label(draw, name, pos_x, pos_y, radius, "d")
        elif name in ["TEAM VITALITY", "GENTLE MATES", "OXYGEN ESPORTS", "TEAM BDS"]:
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
    #utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, (16, 75, 228), (172, 136, 53))

    os.makedirs(config["img_path"], exist_ok=True)
    img.save(os.path.join(config["img_path"], "team_off_xG.png"))

def main():
    key = "RL ESPORTS"
    region = "[1] Major"
    rn = utils.get_region_label(region)
    base_path = os.path.join("RLCS 24", "World Championship", "[1] Swiss Stage")

    game_list = utils.read_group_data(os.path.join("replays", base_path))
    
    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": "TEAM OFFENSIVE PERFORMANCE",
        "t2": f"RLCS 24 | WORLDS | SWISS",
        "t3": "",
        "c1": constants.TEAM_INFO[key]["c1"],
        "c2": constants.TEAM_INFO[key]["c2"],
        "c3": constants.REGION_COLORS["EU"][0],
        "img_path": os.path.join("viz", "images", base_path)
    }

    create_image({rn: game_list}, config)
    
    return 0
  
if __name__ == "__main__":
    main()