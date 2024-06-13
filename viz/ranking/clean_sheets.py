from viz import constants, utils

import os
from PIL import Image, ImageDraw

IMAGE_X = 1400
MARGIN = 40

MID_X, MID_Y = (constants.MAP_Y + (MARGIN * 4)) / 2, (constants.MAP_X + (MARGIN * 2)) / 2

WHITE, BLACK = (255,255,255), (0,0,0)
LIGHT_GREY, DARK_GREY = (140,140,140), (70,70,70)

def get_y(val, img_height):
    return img_height - val

def calculate_stats(tag):
    clean_sheets = {}
    event_data = {}
    team_info = {}

    regions = ["Asia-Pacific", "Europe", "Middle East & North Africa", "North America", "Oceania", "South America", "Sub-Saharan Africa"]
    for maj_name in ["Major 1", "Major 2"]:
        reg_list = regions + ["[1] Major"] if maj_name == "Major 1" else regions
        for region in reg_list:
            group_path = os.path.join("replays", "RLCS 24", maj_name, region)
            game_list = utils.read_group_data(group_path)
            reg = utils.get_region_label(region)

            for game in game_list:
                t0, t1 = "", ""
                for i in range(len(game.teams)):
                    curr_team = game.teams[i]
                    team_ids = [player_id.id for player_id in curr_team.player_ids]
                    team_players = [player.name for player in game.players if player.id.id in team_ids]
                    tn = utils.get_team_label(curr_team.name, reg, team_players)
                    if i == 0:
                        t0 = tn
                    else:
                        t1 = tn
                    if tn not in clean_sheets: 
                        clean_sheets[tn] = 0
                        event_data[tn] = 0
                        team_info[tn] = reg

                if game.teams[0].score == 0 and game.game_metadata.last_second <= 1:
                    clean_sheets[t1] += 1
                    if tag in game.game_metadata.tag or ("Major 2" in game.game_metadata.tag and "Open Qualifiers 1" in game.game_metadata.tag):
                        event_data[t1] += 1
                if game.teams[1].score == 0 and game.game_metadata.last_second <= 1:
                    clean_sheets[t0] += 1
                    if tag in game.game_metadata.tag or ("Major 2" in game.game_metadata.tag and "Open Qualifiers 1" in game.game_metadata.tag):
                        event_data[t0] += 1

            print(region)
        
    print(len(clean_sheets))
    stat_data = dict(sorted(clean_sheets.items(), key=lambda item: (-item[1], str.casefold(item[0]))))
    old_ranks = dict(sorted(clean_sheets.items(), key=lambda item: (-item[1] + event_data[item[0]], str.casefold(item[0]))))
    return stat_data, team_info, event_data, old_ranks

def create_image(tag, config):
    team_data, team_info, event_data, old_ranks = calculate_stats(tag)
    NUM_SPOTS = 15
    ROW_Y = 125

    img_height = (NUM_SPOTS * (ROW_Y + 5)) + 400
    img = Image.new(mode = "RGBA", size = (IMAGE_X, img_height), color = WHITE)
    draw = ImageDraw.Draw(img)
    
    # Logo in top left
    logo_width, _ = utils.draw_team_logo(img, MARGIN, config["logo"])

    # Title text
    utils.draw_title_text(draw, logo_width, MARGIN, config, constants.BOUR_80, constants.BOUR_40)
    
    # Ranking table
    name_y, base_y = 325, 450
    col_locs = [550, 925]
    base_x = 150
    draw.text((base_x, name_y), "Team", fill=BLACK, font=constants.BOUR_60)
    draw.text((base_x + col_locs[0], name_y), "Region", fill=BLACK, font=constants.BOUR_60, anchor="ma")
    draw.text((base_x + col_locs[1], name_y), "Amount", fill=BLACK, font=constants.BOUR_60, anchor="ma")
    team_list = list(team_data.keys())
    for i in range(NUM_SPOTS):
        name = team_list[i]
        region = team_info[name]
        if i == 0:
            rect_color = "#FFD700"
        elif i == 1:
            rect_color = "#C0C0C0"
        elif i == 2:
            rect_color = "#D7995B"
        else:
            rect_color = WHITE
        rect_line = constants.REGION_COLORS[region][0]

        draw.rounded_rectangle([
            (base_x - 50, base_y + (i * ROW_Y) - 26), (base_x + col_locs[-1] + 200, base_y + (i * ROW_Y) + 74)
        ], 50, fill=rect_color, outline=rect_line, width=5)
        draw.text((base_x, base_y + (i * ROW_Y)), name, fill=BLACK, font=constants.BOUR_50)
        draw.text((base_x + col_locs[0], base_y + (i * ROW_Y)), region, fill=BLACK, font=constants.BOUR_50, anchor="ma")
        inc_str = "(+{})".format(event_data[name]) if name in event_data else ""
        draw.text((base_x + col_locs[1], base_y + (i * ROW_Y)), "{} {}".format(team_data[name], inc_str), 
            fill=BLACK, font=constants.BOUR_50, anchor="ma")
        change = i - list(old_ranks).index(name) 
        if change < 0:
            change_str = f"{abs(change)}"
            change_color = (50,250,50)
            draw.text((base_x - 120, base_y + (i * ROW_Y) + 8), "↑", fill=change_color, font=constants.ARIAL)
        elif change > 0:
            change_str = f"{abs(change)}"
            change_color = (250,50,50)
            draw.text((base_x - 120, base_y + (i * ROW_Y) + 8), "↓", fill=change_color, font=constants.ARIAL)
        else:
            change_str = "-"
            change_color = DARK_GREY
        draw.text((base_x - 100, base_y + (i * ROW_Y) + 5), change_str, fill=change_color, font=constants.BOUR_40)
        
    print([key for key in team_data if team_data[key] == team_data[name]])

    # Dotted circle logo
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    
    img.save(os.path.join("viz", "images", config["img_name"]))

def main():
    key = "RL ESPORTS"
    tag = "Open Qualifier 4"
    folder = "Post OQ4"
    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": "CLEAN SHEETS",
        "t2": f"RLCS 24 | {folder.upper()}",
        "t3": "TOP 15 TEAMS",
        "c1": constants.TEAM_INFO[key]["c1"],
        "c2": constants.TEAM_INFO[key]["c2"],
        "img_name": os.path.join("RLCS 24", "Leaderboards", "Season", folder, "clean_sheets.png")
    }
    
    create_image(tag, config)
    
    return 0
  
if __name__ == "__main__":
    main()