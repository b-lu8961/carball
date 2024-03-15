from viz import constants, utils

import os
from PIL import Image, ImageDraw

IMAGE_X = 1900
MARGIN = 40

MID_X, MID_Y = (constants.MAP_Y + (MARGIN * 4)) / 2, (constants.MAP_X + (MARGIN * 2)) / 2

WHITE, BLACK = (255,255,255), (0,0,0)
LIGHT_GREY, DARK_GREY = (140,140,140), (70,70,70)

def get_y(val, img_height):
    return img_height - val

def calculate_stats(game_list):
    thief_games = {}
    player_info = {}
    regions = ["Asia-Pacific", "Europe", "Middle East & North Africa", "North America", "Oceania", "South America", "Sub-Saharan Africa"]
    #regions = ["Asia-Pacific"]

    for region in regions:
        # for i in range(1, 3):
        #     maj_num = "Major 1" if i <= 3 else "Major 2"
        #     group_path = os.path.join("replays", "RLCS 24", maj_num, region, f"Open Qualifiers {i}")
        for maj_name in ["Major 1"]:
            group_path = os.path.join("replays", "RLCS 24", maj_name, region)
            game_list = utils.read_group_data(group_path)
            reg = utils.get_region_label(region)

            for game in game_list:
                for player in game.players:
                    pn = utils.get_player_label(player.name, reg)
                    curr_team = [team for team in game.teams if team.name == player.team_name][0]
                    team_ids = [player_id.id for player_id in curr_team.player_ids]
                    team_players = [player.name for player in game.players if player.id.id in team_ids]
                    tn = utils.get_team_label(player.team_name, reg, team_players)

                    if pn not in thief_games:
                        thief_games[pn] = 0
                        player_info[pn] = [tn, reg]
                    if player_info[pn][0] != tn:
                        player_info[pn][0] = tn

                    opp_big_labels = [40, 50] if player.is_orange else [300, 310]
                    opp_big_pads = [pad for pad in game.game_stats.boost_pads if pad.label in opp_big_labels]
                    player_steals = 0
                    for pad in opp_big_pads:
                        player_pickups = [pickup for pickup in pad.pickups if pickup.player_id.id == player.id.id]
                        player_steals += len(player_pickups)
                    if player_steals >= 7:
                        thief_games[pn] += 1

        print(region)
        
    print(len(thief_games))
    stat_data = dict(sorted(thief_games.items(), key=lambda item: (-item[1], str.casefold(item[0]))))
    return stat_data, player_info

def create_image(game_list, config):
    player_data, player_info = calculate_stats(game_list)
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
    col_locs = [575, 1025, 1425]
    base_x = 150
    draw.text((base_x, name_y), "Player", fill=BLACK, font=constants.BOUR_60)
    draw.text((base_x + col_locs[0], name_y), "Team", fill=BLACK, font=constants.BOUR_60, anchor="ma")
    draw.text((base_x + col_locs[1], name_y), "Region", fill=BLACK, font=constants.BOUR_60, anchor="ma")
    draw.text((base_x + col_locs[2], name_y), "Amount", fill=BLACK, font=constants.BOUR_60, anchor="ma")
    player_list = list(player_data.keys())
    for i in range(NUM_SPOTS):
        name = player_list[i]
        team_name = player_info[name][0]
        region = player_info[name][1]
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
        draw.text((base_x + col_locs[0], base_y + (i * ROW_Y)), team_name, fill=BLACK, font=constants.BOUR_50, anchor="ma")
        draw.text((base_x + col_locs[1], base_y + (i * ROW_Y)), region, fill=BLACK, font=constants.BOUR_50, anchor="ma")
        draw.text((base_x + col_locs[2], base_y + (i * ROW_Y)), "{}".format(player_data[name]), fill=BLACK, font=constants.BOUR_50, anchor="ma")
    print([key for key in player_data if player_data[key] == player_data[name]])

    # Dotted circle logo
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    
    img.save(os.path.join("viz", "images", config["img_name"]))

def main():
    key = "RL ESPORTS"
    reg_num = 3
    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": "HIGH BOOST STEAL GAMES",
        "t2": "RLCS 24 | SEASON | SWISS + PLAYOFFS",
        "t3": "TOP 15 PLAYERS",
        "c1": constants.TEAM_INFO[key]["c1"],
        "c2": constants.TEAM_INFO[key]["c2"],
        "img_name": os.path.join("RLCS 24", "Leaderboards", "Season", f"Post OQ{reg_num}", "thief_games.png")
    }

    base_path = os.path.join("replays", "RLCS 24", "Major 1", "{}")
    
    create_image(base_path, config)
    
    return 1
  
if __name__ == "__main__":
    main()