from viz import constants, utils

import numpy as np
import os
from PIL import Image, ImageDraw

HEADER_HEIGHT = 225
MARGIN = 40

MARKER_SIZE = 15
MID_X, MID_Y = (constants.MAP_Y + (MARGIN * 4)) / 2, (constants.MAP_X + (MARGIN * 2)) / 2

WHITE, BLACK = (255,255,255), (0,0,0)
LIGHT_GREY, DARK_GREY = (140,140,140), (70,70,70)

def get_y(val, img_height):
    return img_height - val

def calculate_metrics(game_lists, tag1, tag2):
    shot_data = {}
    for region in game_lists:
        region_list = game_lists[region]
        for game in region_list:
            if tag1 in game.game_metadata.tag:
                gp_key = "gp_1"
                sp_key = "sp_1"
                for_key = "for_1"
                against_key = "against_1"
            elif tag2 in game.game_metadata.tag:
                gp_key = "gp_2"
                sp_key = "sp_2"
                for_key = "for_2"
                against_key = "against_2"
            else:
                continue
            
            for team in game.teams:
                name = utils.get_team_label(team.name)
                
                if name not in shot_data:
                    #rn = utils.get_region_label(region)
                    shot_data[name] = {
                        "region": region,
                        "gp_1": 0,
                        "gp_2": 0,
                        "sp_1": 0,
                        "sp_2": 0,
                        "for_1": 0,
                        "for_2": 0,
                        "against_1": 0,
                        "against_2": 0
                    }
                    #print(utils.get_team_label(player.team_name))
                shot_data[name][gp_key] += 1
                shot_data[name][sp_key] += game.game_metadata.seconds

            for shot in game.game_metadata.shot_details:
                xG_val = utils.get_xG_val(game, shot)

                for_team = [team for team in game.teams if team.is_orange == shot.is_orange][0]
                for_name = utils.get_team_label(for_team.name)
                shot_data[for_name][for_key] += xG_val

                against_team = [team for team in game.teams if team.is_orange != shot.is_orange][0]
                against_name = utils.get_team_label(against_team.name)
                shot_data[against_name][against_key] += xG_val
    
    return {k: v for k, v in shot_data.items()}

def draw_scatter(game_lists, config):
    metrics = calculate_metrics(game_lists, config["g1"], config["g2"])
    #print(metrics)
    for team in metrics:
        data = metrics[team]
        print("{:15} {:5} {:5} {:5} {:5}".format(team, 
            round(data["for_1"] / (data["sp_1"] / 300), 2), round(data["for_2"] / (data["sp_2"] / 300), 2), 
            round(data["against_1"] / (data["sp_1"] / 300), 2), round(data["against_2"] / (data["sp_2"] / 300), 2))
        )
    # print(len(metrics))
    #print(sorted(metrics))
    max_data = [max(
                    round(np.sum(metrics[name]["for_1"]) / (metrics[name]["sp_1"] / 300), 3), 
                    round(np.sum(metrics[name]["for_2"]) / (metrics[name]["sp_2"] / 300), 3),
                    round(np.sum(metrics[name]["against_1"]) / (metrics[name]["sp_1"] / 300), 3),
                    round(np.sum(metrics[name]["against_2"]) / (metrics[name]["sp_2"] / 300), 3)
                ) for name in metrics]
    min_data = [min(
                    round(np.sum(metrics[name]["for_1"]) / (metrics[name]["sp_1"] / 300), 3), 
                    round(np.sum(metrics[name]["for_2"]) / (metrics[name]["sp_2"] / 300), 3),
                    round(np.sum(metrics[name]["against_1"]) / (metrics[name]["sp_1"] / 300), 3),
                    round(np.sum(metrics[name]["against_2"]) / (metrics[name]["sp_2"] / 300), 3)
                ) for name in metrics]
    
    
    min_xG, max_xG = (round(min(min_data) * 10) / 10) - 0.1, 0.1 + (round(max(max_data) * 10) / 10)
    print(min_xG, max_xG)

    ax_pad = 10 * MARGIN
    #tick_px_x, tick_px_y = 300, 250
    tick_px_x, tick_jump_x = 650, 0.5
    plot_width = round((max_xG - min_xG) / tick_jump_x) * tick_px_x
    plot_height = 450
    width, height = plot_width + ax_pad + (3 * MARGIN), (plot_height * len(metrics)) + MARGIN
    img = Image.new(mode="RGBA", size = (width, height), color=WHITE)
    draw = ImageDraw.Draw(img)

    base_x, base_y = (3 * MARGIN), 10 
    teams = ["RMC", "GEN.G MOBIL1", "G2 STRIDE", "SPACESTATION", "REBELLION", "DIGNITAS", "OG ESPORTS", "INCORRECT", "PIRATES", "FUN"]
    #teams = ["OXYGEN ESPORTS", "100%", "JOBLESS", "ENDPOINT", "ESPARTACO", "LUNA GALAXY", "FAKE GA", "SAUDADE", "GS RESOLVE", "TEAM JJROX"]
    for i in range(len(teams)):

        name = teams[i]
        top_y = base_y + (plot_height * i)
        for_y, against_y = top_y + 120, top_y + 240
        draw.text((base_x, top_y), name, fill=BLACK, font=constants.BOUR_70)
        draw.text((base_x + 40, for_y), "xG For", fill=DARK_GREY, font=constants.BOUR_50, anchor="lm")
        draw.text((base_x + 40, against_y), "xG Against", fill=DARK_GREY, font=constants.BOUR_50, anchor="lm")

        # X-axis
        ax_y = top_y + plot_height - 110
        draw.line([
            (ax_pad, ax_y), (ax_pad + plot_width, ax_y)
        ], fill=LIGHT_GREY, width=6)
        
        if i == 0:
            draw.text((ax_pad + (plot_width / 2), ax_y + 60), 
                "xG per 5:00", fill=DARK_GREY, font=constants.BOUR_50, anchor='ma')
        for j in np.arange(round(min_xG * 10) / 10, max_xG + 0.02, (tick_jump_x / 5)):
            val = round(j * 10) / 10
            pos_x = ax_pad + (((val - min_xG) / (max_xG - min_xG)) * plot_width)
            draw.line([(pos_x, ax_y - 5), (pos_x, ax_y + 5)], fill=DARK_GREY, width=2)
            if int(val * 10) % 5 == 0:
                draw.text((pos_x, ax_y + (0.5 * MARGIN)), "{:.1f}".format(val), fill=DARK_GREY, font=constants.BOUR_40, anchor="ma")

        # Stat dots
        radius = 25
        f1_val = np.sum(metrics[name]["for_1"]) / (metrics[name]["sp_1"] / 300)
        f2_val = np.sum(metrics[name]["for_2"]) / (metrics[name]["sp_2"] / 300)
        f1_pos = ax_pad + (((f1_val - min_xG) / (max_xG - min_xG)) * plot_width)
        f2_pos = ax_pad + (((f2_val - min_xG) / (max_xG - min_xG)) * plot_width)
        
        a1_val = np.sum(metrics[name]["against_1"]) / (metrics[name]["sp_1"] / 300)
        a2_val = np.sum(metrics[name]["against_2"]) / (metrics[name]["sp_2"] / 300)
        a1_pos = ax_pad + (((a1_val - min_xG) / (max_xG - min_xG)) * plot_width)
        a2_pos = ax_pad + (((a2_val - min_xG) / (max_xG - min_xG)) * plot_width)

        if name in constants.TEAM_INFO:
            colors = [constants.TEAM_INFO[name]["c1"], constants.TEAM_INFO[name]["c2"]]
        else:
            colors = constants.REGION_COLORS[metrics[name]["region"]]
        draw.ellipse([(f1_pos - radius, for_y - radius), (f1_pos + radius, for_y + radius)], fill=colors[0], outline=colors[1], width=2)
        draw.rectangle([(f2_pos - radius, for_y - radius), (f2_pos + radius, for_y + radius)], fill=colors[0], outline=colors[1], width=2)
        draw.ellipse([(a1_pos - radius, against_y - radius), (a1_pos + radius, against_y + radius)], fill=colors[1], outline=colors[0], width=2)
        draw.rectangle([(a2_pos - radius, against_y - radius), (a2_pos + radius, against_y + radius)], fill=colors[1], outline=colors[0], width=2)
        
        txt_1, txt_2 = "1", "2"
        txt_offset, arw_offset = 50, 50
        arw_o2 = arw_offset + 20
        min_sep = 125
        if f1_val > f2_val:
            draw.text((f1_pos + txt_offset, for_y), txt_1, fill=LIGHT_GREY, font=constants.BOUR_50, anchor="mm")
            draw.text((f2_pos - txt_offset, for_y), txt_2, fill=LIGHT_GREY, font=constants.BOUR_50, anchor="mm")
            if f1_pos - f2_pos > min_sep:
                draw.line([(f2_pos + arw_offset, for_y), (f1_pos - arw_offset, for_y)], fill=(200, 0, 0), width=3)
                draw.line([(f2_pos + arw_o2, for_y - 20), (f2_pos + arw_offset, for_y), (f2_pos + arw_o2, for_y + 20)], fill=(200, 0, 0), width=3, joint="curve")
        else:
            draw.text((f1_pos - txt_offset, for_y), txt_1, fill=LIGHT_GREY, font=constants.BOUR_50, anchor="mm")
            draw.text((f2_pos + txt_offset, for_y), txt_2, fill=LIGHT_GREY, font=constants.BOUR_50, anchor="mm")
            if f2_pos - f1_pos > min_sep:
                draw.line([(f1_pos + arw_offset, for_y), (f2_pos - arw_offset, for_y)], fill=(0, 200, 0), width=3)
                draw.line([(f2_pos - arw_o2, for_y - 20), (f2_pos - arw_offset, for_y), (f2_pos - arw_o2, for_y + 20)], fill=(0, 200, 0), width=3, joint="curve")

        
        if a1_val > a2_val:
            draw.text((a1_pos + txt_offset, against_y), txt_1, fill=LIGHT_GREY, font=constants.BOUR_50, anchor="mm")
            draw.text((a2_pos - txt_offset, against_y), txt_2, fill=LIGHT_GREY, font=constants.BOUR_50, anchor="mm")
            if a1_pos - a2_pos > min_sep:
                draw.line([(a2_pos + arw_offset, against_y), (a1_pos - arw_offset, against_y)], fill=(0, 200, 0), width=3)
                draw.line([(a2_pos + arw_o2, against_y - 20), (a2_pos + arw_offset, against_y), (a2_pos + arw_o2, against_y + 20)], fill=(0, 200, 0), width=3, joint="curve")
        else:
            draw.text((a1_pos - txt_offset, against_y), txt_1, fill=LIGHT_GREY, font=constants.BOUR_50, anchor="mm")
            draw.text((a2_pos + txt_offset, against_y), txt_2, fill=LIGHT_GREY, font=constants.BOUR_50, anchor="mm")
            if a2_pos - a1_pos > min_sep:
                draw.line([(a1_pos + arw_offset, against_y), (a2_pos - arw_offset, against_y)], fill=(200, 0, 0), width=3)
                draw.line([(a2_pos - arw_o2, against_y - 20), (a2_pos - arw_offset, against_y), (a2_pos - arw_o2, against_y + 20)], fill=(200, 0, 0), width=3, joint="curve")
                

    # # Median lines
    # for_pos = ax_pad + (((np.median(for_data) - bounds_x[0]) / (bounds_x[1] - bounds_x[0])) * plot_width)
    # utils.linedashed(draw, LIGHT_GREY, 3, for_pos, for_pos, get_y(height - MARGIN, height), get_y(ax_pad, height))
    # draw.multiline_text((for_pos - 15, MARGIN), "Median\nxG", 
    #     fill=LIGHT_GREY, font=constants.BOUR_30, align="right", anchor="ra")

    # against_pos = get_y(ax_pad + (((np.median(against_data) - bounds_y[0]) / (bounds_y[1] - bounds_y[0])) * plot_height), height)
    # utils.linedashed(draw, LIGHT_GREY, 3, ax_pad, width - MARGIN, against_pos, against_pos)
    # draw.multiline_text((ax_pad + MARGIN, against_pos - 35), "Median xG\nCreated", 
    #     fill=LIGHT_GREY, font=constants.BOUR_30, align="center", spacing=15)

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
    utils.draw_dotted_circle_2(img, draw, IMAGE_X, MARGIN, config["c1"], config["c2"])

    os.makedirs(config["img_path"], exist_ok=True)
    img.save(os.path.join(config["img_path"], config["g1"] + "_" + config["g2"] + "_comparison.png"))

def main():
    key = "SHIFT SL"
    region = "North America"
    rn = utils.get_region_label(region)
    base_path = os.path.join("Shift Summer League", region, "2. League Play", "Week 1", "Matchday 1")

    game_list = utils.read_group_data(os.path.join("replays", base_path))
    
    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": "TEAM xG PERFORMANCE",
        "t2": f"SHIFT SUMMER LEAGUE | NORTH AMERICA",
        "t3": "WEEK 1 & 2 COMPARISON",
        "c1": constants.TEAM_INFO[key]["c1"],
        "c2": constants.TEAM_INFO[key]["c2"],
        "c3": constants.TEAM_INFO[key]["c3"],
        "g1": "Round 1",
        "g2": "Round 2",
        "img_path": os.path.join("viz", "images", base_path)
    }

    create_image({rn: game_list}, config)
    
    return 0
  
if __name__ == "__main__":
    main()