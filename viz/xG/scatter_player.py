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
    shot_data = {}
    for region in game_lists:
        region_list = game_lists[region]
        for game in region_list:
            for player in game.players:
                name = utils.get_player_label(player.name)
                team_name = utils.get_team_label(player.team_name)
                rn = utils.get_region_from_team(team_name)
                
                if name not in shot_data:
                    #rn = utils.get_region_label(region)
                    shot_data[name] = {
                        "region": rn,
                        "team": utils.get_team_label(player.team_name),
                        "games_played": 0,
                        "seconds_played": 0,
                        "xG": 0,
                        "xG_created": 0,
                        "goals": 0,
                        "assists": 0
                    }
                    #print(utils.get_team_label(player.team_name))
                shot_data[name]["games_played"] += 1
                shot_data[name]["seconds_played"] += game.game_metadata.seconds
                shot_data[name]["goals"] += player.goals
                shot_data[name]["assists"] += player.assists

            for shot in game.game_metadata.shot_details:
                xG_val = utils.get_xG_val(game, shot)

                shot_player = [pl for pl in game.players if shot.shooter_name == pl.name][0]
                shooter = utils.get_player_label(shot_player.name)
                shot_data[shooter]["xG"] += xG_val

                shot_touch = [hit for hit in game.game_stats.hits if hit.frame_number == shot.frame_number][0]
                candidates = [hit for hit in game.game_stats.hits if hit.goal_number == shot_touch.goal_number 
                    and shot.frame_number - (5 * 30) <= hit.frame_number and hit.frame_number < shot.frame_number]
                teammates = [pl.id.id for pl in game.players if pl.is_orange == shot_player.is_orange]
                if len(candidates) > 0:
                    opp_touches = 0
                    for i in range(len(candidates) - 1, -1, -1):
                        if candidates[i].player_id.id in teammates:
                            ast_player = [pl for pl in game.players if pl.id.id == candidates[i].player_id.id][0]
                            assister = utils.get_player_label(ast_player.name)
                            break
                        else:
                            opp_touches += 1
                    if opp_touches <= 2:
                        shot_data[assister]["xG_created"] += xG_val
    
    return {k: v for k, v in shot_data.items() if v["games_played"] >= 3}

def draw_scatter(game_lists, config):
    metrics = calculate_metrics(game_lists)
    # for pl in metrics:
    #     data = metrics[pl]
    #     print("{:15} {:5} {:5} {:5} {:5}".format(pl, round(data["xG"], 1), data["goals"], round(data["xG_created"], 1), data["assists"]))
    # print(len(metrics))
    #print(sorted(metrics))
    taken_data = [round(np.sum(metrics[name]["xG"]) / (metrics[name]["seconds_played"] / 300), 3) for name in metrics]
    created_data = [round(np.sum(metrics[name]["xG_created"]) / (metrics[name]["seconds_played"] / 300), 3) for name in metrics]
    
    bounds_x = (min(0.3, (round(min(taken_data) * 10) / 10) - 0.1), max(1.1, 0.1 + (round(max(taken_data) * 10) / 10)))
    bounds_y = (min(0.3, (round(min(created_data) * 10) / 10) - 0.1), max(1.1, 0.1 + (round(max(created_data) * 10) / 10)))
    #print(bounds_x, bounds_y)

    ax_pad = 5 * MARGIN
    #tick_px_x, tick_px_y = 300, 250
    tick_px_x, tick_px_y = 450, 300
    tick_jump_x, tick_jump_y = 0.25, 0.25
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
        "xG per 5:00", fill=DARK_GREY, font=constants.BOUR_60, anchor='ma')
    for i in np.arange(round(bounds_x[0] * 20) / 20, bounds_x[1], (tick_jump_x / 5)):
        val = round(i * 20) / 20
        pos_x = ax_pad + (((val - bounds_x[0]) / (bounds_x[1] - bounds_x[0])) * plot_width)
        pos_y = get_y(ax_pad, height)
        draw.line([(pos_x, pos_y - 5), (pos_x, pos_y + 5)], fill=DARK_GREY, width=2)
        if int(val * 20) % 5 == 0:
            draw.text((pos_x, pos_y + (0.5 * MARGIN)), "{:.1f}".format(val), fill=DARK_GREY, font=constants.BOUR_40, anchor="ma")
    
    # Y-axis
    y_label_len = round(draw.textlength("xG Created Per 5:00", constants.BOUR_60))
    y_label_img = Image.new("RGB", size=(y_label_len, 60), color=WHITE)
    y_label_draw = ImageDraw.Draw(y_label_img)
    y_label_draw.text((0, 0), "xG Created per 5:00", fill=DARK_GREY, font=constants.BOUR_60)
    y_label_rot = y_label_img.rotate(90, expand=True)
    img.paste(y_label_rot, (ax_pad - int((3.5 * MARGIN)), get_y(ax_pad + int(plot_height / 2) + int(y_label_len / 2), height)))
    for i in np.arange(round(bounds_y[0] * 20) / 20, bounds_y[1], (tick_jump_y / 5)):
        print(i)
        val = round(i * 20) / 20
        pos_y = get_y(ax_pad + (((val - bounds_y[0]) / (bounds_y[1] - bounds_y[0])) * plot_height), height)
        draw.line([(ax_pad - 5, pos_y), (ax_pad + 5, pos_y)], fill=DARK_GREY, width=2)
        if int(val * 20) % 5 == 0:
            draw.text((ax_pad - (1.75 * MARGIN), pos_y), "{:.1f}".format(val), fill=DARK_GREY, font=constants.BOUR_40, anchor="lm")

    # Plot elements
    # Top left style label
    tl_text = "High xG\nShots Created"
    tl_pos = (ax_pad + MARGIN, get_y(plot_height + ax_pad - (3 * MARGIN), height))
    tl_bbox = draw.multiline_textbbox(tl_pos, tl_text, font=constants.BOUR_50, align="center")
    draw.rounded_rectangle([tl_bbox[0] - 8, tl_bbox[1] - 8, tl_bbox[2] + 8, tl_bbox[3] + 8], 10, fill=config["c3"])
    draw.text(tl_pos, tl_text, fill=WHITE, font=constants.BOUR_50, align="center")
    
    # Bottom right style label
    br_text = "High xG\nShots Taken"
    br_text_len = draw.textlength("Shots Taken", font=constants.BOUR_50)
    br_pos = (width - br_text_len - (2 * MARGIN), get_y(ax_pad + (3 * MARGIN), height))
    br_bbox = draw.multiline_textbbox(br_pos, br_text, font=constants.BOUR_50, align="center")
    draw.rounded_rectangle([br_bbox[0] - 8, br_bbox[1] - 8, br_bbox[2] + 8, br_bbox[3] + 8], 10, fill=config["c3"])
    draw.multiline_text(br_pos, br_text, fill=WHITE, font=constants.BOUR_50, align="center")

    # Median lines
    for_pos = ax_pad + (((np.median(taken_data) - bounds_x[0]) / (bounds_x[1] - bounds_x[0])) * plot_width)
    utils.linedashed(draw, LIGHT_GREY, 3, for_pos, for_pos, get_y(height - MARGIN, height), get_y(ax_pad, height))
    draw.multiline_text((for_pos - 15, MARGIN), "Median\nxG", 
        fill=LIGHT_GREY, font=constants.BOUR_30, align="right", anchor="ra")

    against_pos = get_y(ax_pad + (((np.median(created_data) - bounds_y[0]) / (bounds_y[1] - bounds_y[0])) * plot_height), height)
    utils.linedashed(draw, LIGHT_GREY, 3, ax_pad, width - MARGIN, against_pos, against_pos)
    draw.multiline_text((ax_pad + MARGIN, against_pos - 35), "Median xG\nCreated", 
        fill=LIGHT_GREY, font=constants.BOUR_30, align="center", spacing=15)

    # Player points
    for name in metrics:
        radius = 15
        val_x = np.sum(metrics[name]["xG"]) / (metrics[name]["seconds_played"] / 300)
        val_y = np.sum(metrics[name]["xG_created"]) / (metrics[name]["seconds_played"] / 300)
        #print(name, val_x, val_y)
        pos_x = ax_pad + (((val_x - bounds_x[0]) / (bounds_x[1] - bounds_x[0])) * plot_width)
        pos_y = get_y(ax_pad + (((val_y - bounds_y[0]) / (bounds_y[1] - bounds_y[0])) * plot_height), height)
        colors = constants.REGION_COLORS[metrics[name]["region"]]
        draw.ellipse([(pos_x - radius, pos_y - radius), (pos_x + radius, pos_y + radius)], fill=colors[0], outline=colors[1], width=2)
        
        if name in []:
            utils.draw_scatter_label(draw, name, pos_x, pos_y, radius, "u")
        elif name in []:
            utils.draw_scatter_label(draw, name, pos_x, pos_y, radius, "d")
        elif name in []:
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
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, (16, 75, 228), (172, 136, 53))

    os.makedirs(config["img_path"], exist_ok=True)
    img.save(os.path.join(config["img_path"], "player_xG_perf.png"))

def main():
    key = "RLCS"
    region = "North America"
    rn = utils.get_region_label(region)
    base_path = os.path.join("RLCS 24", "World Championship", "[1] Swiss Stage")

    game_list = utils.read_group_data(os.path.join("replays", base_path))
    
    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": "PLAYER xG PERFORMANCE",
        "t2": f"RLCS 24 | WORLDS | SWISS",
        "t3": "",
        "c1": constants.TEAM_INFO[key]["c1"],
        "c2": constants.TEAM_INFO[key]["c2"],
        "c3": constants.TEAM_INFO[key]["c2"],
        "img_path": os.path.join("viz", "images", base_path)
    }

    create_image({rn: game_list}, config)
    
    return 0
  
if __name__ == "__main__":
    main()