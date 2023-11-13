from viz import constants, utils

import os
from PIL import Image, ImageDraw, ImageFont

IMAGE_X, IMAGE_Y = 2600, 1100
MARGIN = 40

MARKER_SIZE = 20
MID_X, MID_Y = (constants.GOAL_X + (MARGIN * 4)) / 2, constants.GOAL_Z / 2

WHITE, BLACK = (255,255,255), (0,0,0)

def get_y(val, img_height):
    return img_height - val

def draw_marker(draw, pos, mark_type, img_height, size=MARKER_SIZE, outline=None, fill=None, width=2):
    base_x = MID_X + pos.pos_x
    base_y = MARGIN + pos.pos_z
    if mark_type == "C":
        draw.ellipse([(base_x - size, get_y(base_y + size, img_height)), (base_x + size, get_y(base_y - size, img_height))], 
            outline=outline, fill=fill, width=width)
    elif mark_type == "S":
        draw.regular_polygon((base_x, get_y(base_y, img_height), size), 4, 
            outline=outline, fill=fill, width=width, rotation=45)
    else:
        draw.regular_polygon((base_x, get_y(base_y, img_height), size + 5), 3, 
            outline=outline, fill=fill, width=width, rotation=60)

def draw_goal(team_name, data_path):
    width, height = constants.GOAL_X + (MARGIN * 4), round(constants.GOAL_Z) + (MARGIN * 2)
    img = Image.new(mode="RGBA", size = (width, height), color=WHITE)
    
    draw = ImageDraw.Draw(img)
    utils.draw_goal_lines(draw, MARGIN, height)
    
    game_iter = utils.read_group_data(data_path)

    gp, solo, assisted, total = 0, 0, 0, 0
    player_map = {}
    for game in game_iter:
        active_teams = [team.name for team in game.teams]
        if team_name not in active_teams:
            continue

        gp += 1
        team_goals = [goal for goal in game.game_metadata.goals if goal.team_name == team_name]
        for goal in team_goals:
            if goal.scorer not in player_map:
                players_seen = len(player_map.keys())
                player_map[goal.scorer] = players_seen

            if goal.assister == "":
                assisted += 1
            else:
                solo += 1
            total += 1

            team_color = constants.ORANGE_COLORS if goal.is_orange else constants.BLUE_COLORS
            width = 4 if goal.assister == "" else 2
            if player_map[goal.scorer] == 0:
                outline = BLACK if goal.assister == "" else team_color[0]
                draw_marker(draw, goal.ball_pos, "C", height, outline=outline, fill=team_color[0], width=width)
            elif player_map[goal.scorer] == 1:
                outline = BLACK if goal.assister == "" else team_color[1]
                draw_marker(draw, goal.ball_pos, "S", height, outline=outline, fill=team_color[1], width=width)
            else:
                outline = BLACK if goal.assister == "" else team_color[2]
                draw_marker(draw, goal.ball_pos, "T", height, outline=outline, fill=team_color[2], width=width)

    players = (
        [key for key, val in player_map.items() if val == 0][0],
        [key for key, val in player_map.items() if val == 1][0],
        [key for key, val in player_map.items() if val == 2][0],
    )
    return img, (gp, solo, assisted, total), players, team_color
  

def create_image(team_name: str, data_path: str, config):
    img = Image.new(mode = "RGBA", size = (IMAGE_X, IMAGE_Y), color = WHITE)
    draw = ImageDraw.Draw(img)
    
    # Logo in top left
    logo_width, _ = utils.draw_team_logo(img, MARGIN, config["logo"])

    # Title text
    font_big = ImageFont.truetype("C:\\Users\\blu89\\Downloads\\Bourgeois Bold\\Bourgeois Bold.otf", 80)
    font_medium = ImageFont.truetype("C:\\Users\\blu89\\Downloads\\Bourgeois Bold\\Bourgeois Bold.otf", 60)
    font_50 = ImageFont.truetype("C:\\Users\\blu89\\Downloads\\Bourgeois Bold\\Bourgeois Bold.otf", 50)
    font_small = ImageFont.truetype("C:\\Users\\blu89\\Downloads\\Bourgeois Bold\\Bourgeois Bold.otf", 40)
    draw.text((logo_width + 50 + MARGIN, 10 + MARGIN), config["t1"], fill=BLACK, font=font_big)
    draw.text((logo_width + 50 + MARGIN, 90 + MARGIN), config["t2"], fill=(70,70,70), font=font_small)
    draw.text((logo_width + 50 + MARGIN, 140 + MARGIN), config["t3"], fill=(70,70,70), font=font_small)

    # Main goal image
    goal_image, counts, players, team_color = draw_goal(team_name, data_path)
    goal_img_width, goal_img_height = goal_image.width, goal_image.height
    img.paste(goal_image, (MARGIN, get_y(goal_image.height + MARGIN, IMAGE_Y)))

    # Legend above goal
    legend_text = [
        f" -  - {players[0]}  |  ",
        f" -  - {players[1]}  |  ",
        f" -  - {players[2]}"
    ]
    legend_len = [
        draw.textlength(legend_text[0], font=font_50),
        draw.textlength(legend_text[1], font=font_50),
        draw.textlength(legend_text[2], font=font_50),
    ]
    legend_base_x = MID_X - (sum(legend_len) / 2) + 30
    legend_base_y = goal_img_height + (1.5 * MARGIN)
    icon_padding = (4, -10)

    draw.text((legend_base_x, get_y(legend_base_y, IMAGE_Y)), 
        legend_text[0], fill=(70,70,70), font=font_50)
    draw.ellipse([
            (legend_base_x + icon_padding[0], get_y(legend_base_y + icon_padding[1], IMAGE_Y)), 
            (legend_base_x + 30 + icon_padding[0], get_y(legend_base_y - 30 + icon_padding[1], IMAGE_Y))], 
        fill=team_color[0])
    draw.text((legend_base_x + legend_len[0], get_y(legend_base_y, IMAGE_Y)), 
        legend_text[1], fill=(70,70,70), font=font_50)
    draw.regular_polygon((legend_base_x + legend_len[0] + 16, get_y(legend_base_y - 25, IMAGE_Y), 15), 4, 
        fill=team_color[1], rotation=45)
    draw.text((legend_base_x + legend_len[0] + legend_len[1], get_y(legend_base_y, IMAGE_Y)), 
        legend_text[2], fill=(70,70,70), font=font_50)
    draw.regular_polygon((legend_base_x + legend_len[0] + legend_len[1] + 17, get_y(legend_base_y - 22, IMAGE_Y), 18), 3, 
        fill=team_color[1], rotation=60)
    
    # Detail text on right
    padding = 109 if counts[2] < 10 else 113
    draw.ellipse([
            (goal_img_width + padding - 50, get_y(goal_img_height - 382 + 50, IMAGE_Y)), 
            (goal_img_width + padding + 50, get_y(goal_img_height - 382 - 50, IMAGE_Y))
        ], outline=BLACK, width=4)

    draw.multiline_text((goal_img_width + (2 * MARGIN), get_y(goal_img_height - MARGIN, IMAGE_Y)), 
        f"{counts[0]}\n\n\n{counts[1]}\n\n\n{counts[2]}\n\n\n{counts[3]}", fill=BLACK, font=font_medium, align="center"
    )
    draw.multiline_text((goal_img_width + (5 * MARGIN), get_y(goal_img_height - MARGIN, IMAGE_Y)),
        "games played\n\n\nsolo goals\n\n\nassisted goals\n\n\ntotal goals", fill=(70,70,70), font=font_medium
    )
    
    # Dotted circle logo
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    
    img.save(os.path.join("viz", "images", "goals", config["img_name"]))

def main():
    team_name = "TEAM VITALITY"
    data_path = os.path.join("replays", "Playoffs")
    config = {
        "logo": "TEAM_VITALITY.png",
        "t1": "TEAM VITALITY",
        "t2": "ALPHA54 | RADOSIN | ZEN",
        "t3": "GOAL PLACEMENT | WORLDS '23 - PLAYOFFS",
        "c1": constants.TEAM_INFO[team_name]["c1"],
        "c2": constants.TEAM_INFO[team_name]["c2"],
        "img_name": "vitality_goals.png"
    }
    create_image(team_name, data_path, config)
    
    return 1
  
if __name__ == "__main__":
    main()