from viz import constants, utils

import os
from PIL import Image, ImageDraw

IMAGE_X, IMAGE_Y = 2600, 1050
MARGIN = 40

MARKER_SIZE = 20
MID_X, MID_Y = (constants.GOAL_X + (MARGIN * 4)) / 2, constants.GOAL_Z / 2

WHITE, BLACK = (255,255,255), (0,0,0)
LIGHT_GREY, DARK_GREY = (180,180,180), (70,70,70)

def get_y(val, img_height):
    return img_height - val

def draw_marker(draw, pos, mark_type, img_height, size=MARKER_SIZE, outline=None, fill=None, width=2):
    base_x = MID_X + pos.pos_x
    base_y = pos.pos_z
    if mark_type == "C":
        draw.ellipse([(base_x - size, get_y(base_y + size, img_height)), (base_x + size, get_y(base_y - size, img_height))], 
            outline=outline, fill=fill, width=width)
    elif mark_type == "S":
        draw.regular_polygon((base_x, get_y(base_y, img_height), size), 4, 
            outline=outline, fill=fill, width=width, rotation=45)
    else:
        draw.regular_polygon((base_x, get_y(base_y, img_height), size + 5), 3, 
            outline=outline, fill=fill, width=width, rotation=60)

def draw_goal(team_name, game_list):
    width, height = constants.GOAL_X + (MARGIN * 4), round(constants.GOAL_Z - 80) + (MARGIN * 2)
    img = Image.new(mode="RGBA", size = (width, height), color=WHITE)
    
    draw = ImageDraw.Draw(img)
    utils.draw_goal_lines(draw, MARGIN, height)

    gp, solo, assisted, total = 0, 0, 0, 0
    player_map = {}
    mark_types = ["C", "S", "T"]
    for game in game_list:
        active_teams = [utils.get_team_label(team.name) for team in game.teams]
        if team_name not in active_teams:
            continue

        if len(player_map) == 0:
            player_names = []
            for player in game.players:
                if utils.get_team_label(player.team_name) == team_name:
                    player_names.append(utils.get_player_label(player.name))
            names_sorted = sorted(player_names, key=str.casefold)
            for i in range(len(names_sorted)):
                player_map[names_sorted[i]] = i

        gp += 1
        team_goals = [goal for goal in game.game_metadata.goals if utils.get_team_label(goal.team_name) == team_name]
        for goal in team_goals:
            scorer = utils.get_player_label(goal.scorer)
            if goal.assister != "":
                assisted += 1
            else:
                solo += 1
            total += 1

            #team_color = constants.ORANGE_COLORS if goal.is_orange else constants.BLUE_COLORS
            team_color = [constants.TEAM_INFO["G2 ESPORTS"]["c1"], constants.TEAM_INFO["G2 ESPORTS"]["c2"], constants.TEAM_INFO["G2 ESPORTS"]["c3"]]
            fill_color = team_color[player_map[scorer]]
            outline_color = WHITE if goal.assister == "" else team_color[player_map[utils.get_player_label(goal.assister)]]
            width = 3 if goal.assister != "" else 0
            draw_marker(draw, goal.ball_pos, mark_types[player_map[scorer]], height, outline=outline_color, fill=fill_color, width=width)
            
    
    return img, (gp, solo, assisted, total), list(player_map.keys()), team_color
  

def create_image(team_name: str, game_list, config):
    img = Image.new(mode = "RGBA", size = (IMAGE_X, IMAGE_Y), color = WHITE)
    draw = ImageDraw.Draw(img)
    
    # Logo in top left
    logo_width, _ = utils.draw_team_logo(img, MARGIN, config["logo"])

    # Title text
    utils.draw_title_text(draw, logo_width, MARGIN, config, constants.BOUR_80, constants.BOUR_40)

    # Main goal image
    goal_image, counts, players, team_color = draw_goal(team_name, game_list)
    goal_img_width, goal_img_height = goal_image.width, goal_image.height
    img.paste(goal_image, (MARGIN, get_y(goal_image.height + MARGIN, IMAGE_Y)))

    # Legend above goal
    legend_text = [
        f" -  - {players[0]}  |  ",
        f" -  - {players[1]}  |  ",
        f" -  - {players[2]}"
    ]
    legend_len = [
        draw.textlength(legend_text[0], font=constants.BOUR_50),
        draw.textlength(legend_text[1], font=constants.BOUR_50),
        draw.textlength(legend_text[2], font=constants.BOUR_50),
    ]
    legend_base_x = MID_X - (sum(legend_len) / 2) + 30
    legend_base_y = goal_img_height + (1.5 * MARGIN)
    icon_padding = (4, -10)

    draw.text((legend_base_x, get_y(legend_base_y, IMAGE_Y)), 
        legend_text[0], fill=(70,70,70), font=constants.BOUR_50)
    draw.ellipse([
            (legend_base_x + icon_padding[0], get_y(legend_base_y + icon_padding[1], IMAGE_Y)), 
            (legend_base_x + 30 + icon_padding[0], get_y(legend_base_y - 30 + icon_padding[1], IMAGE_Y))], 
        fill=team_color[0])
    draw.text((legend_base_x + legend_len[0], get_y(legend_base_y, IMAGE_Y)), 
        legend_text[1], fill=(70,70,70), font=constants.BOUR_50)
    draw.regular_polygon((legend_base_x + legend_len[0] + 16, get_y(legend_base_y - 25, IMAGE_Y), 15), 4, 
        fill=team_color[1], rotation=45)
    draw.text((legend_base_x + legend_len[0] + legend_len[1], get_y(legend_base_y, IMAGE_Y)), 
        legend_text[2], fill=(70,70,70), font=constants.BOUR_50)
    draw.regular_polygon((legend_base_x + legend_len[0] + legend_len[1] + 17, get_y(legend_base_y - 22, IMAGE_Y), 18), 3, 
        fill=team_color[2], rotation=60)
    
    # Detail text on right
    padding = 97 if max(counts) < 10 else 113
    draw.ellipse([
            (goal_img_width + padding - 50, get_y(goal_img_height - 382 + 70, IMAGE_Y)), 
            (goal_img_width + padding + 50, get_y(goal_img_height - 382 - 30, IMAGE_Y))
        ], outline=DARK_GREY, width=4)

    draw.multiline_text((goal_img_width + (2 * MARGIN), get_y(goal_img_height - (0.5 * MARGIN), IMAGE_Y)), 
        f"{counts[0]}\n\n\n{counts[1]}\n\n\n{counts[2]}\n\n\n{counts[3]}", fill=BLACK, font=constants.BOUR_60, align="center"
    )
    draw.multiline_text((goal_img_width + (5 * MARGIN), get_y(goal_img_height - (0.5 * MARGIN), IMAGE_Y)),
        "games played\n\n\nsolo goals\n\n\nassisted goals\n\n\ntotal goals", fill=(70,70,70), font=constants.BOUR_60
    )
    
    # Dotted circle logo
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    

    os.makedirs(config["img_path"], exist_ok=True)
    img.save(os.path.join(config["img_path"], f"{team_name}_goals.png"))

def main():
    team_name = "G2 STRIDE"
    key = "G2 ESPORTS"
    base_path = os.path.join("RLCS 24", "Major 1", "[1] Major")
    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": key,
        "t2": "ATOMIC | BEASTMODE | DANIEL",
        "t3": "RLCS 24 | MAJOR 1 | GOAL PLACEMENT",
        "c1": constants.TEAM_INFO[key]["c1"],
        "c2": constants.TEAM_INFO[key]["c2"],
        "img_path": os.path.join("viz", "images", base_path)
    }

    game_list = utils.read_group_data(os.path.join("replays", base_path))
    create_image(team_name, game_list, config)
    
    return 1
  
if __name__ == "__main__":
    main()