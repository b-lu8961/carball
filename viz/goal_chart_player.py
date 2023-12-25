from viz import constants, utils

import os
from PIL import Image, ImageDraw

IMAGE_X, IMAGE_Y = 2600, 925
MARGIN = 40

MARKER_SIZE = 20
MID_X, MID_Y = (constants.GOAL_X + (MARGIN * 4)) / 2, constants.GOAL_Z / 2

WHITE, BLACK = (255,255,255), (0,0,0)

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

def draw_goal(player_name, game_list):
    width, height = constants.GOAL_X + (MARGIN * 4), round(constants.GOAL_Z - 80) + (MARGIN * 2)
    img = Image.new(mode="RGBA", size = (width, height), color=WHITE)
    
    draw = ImageDraw.Draw(img)
    utils.draw_goal_lines(draw, MARGIN, height)

    gp, go_ahead, tying, total = 0, 0, 0, 0
    for game in game_list:
        active_players = [player.name for player in game.players]
        if player_name not in active_players:
            continue

        gp += 1
        player_goals = [goal for goal in game.game_metadata.goals if goal.scorer == player_name]
        for goal in player_goals:
            if goal.is_orange: 
                marker_color = constants.ORANGE_COLORS
            else:
                marker_color = constants.BLUE_COLORS
            if goal.is_go_ahead:
                draw_marker(draw, goal.ball_pos, "C", height, fill=marker_color[0])
                go_ahead += 1
            elif goal.is_tying:
                draw_marker(draw, goal.ball_pos, "C", height, outline=marker_color[2], width=3)
                tying += 1
            else:
                draw_marker(draw, goal.ball_pos, "C", height, size=(MARKER_SIZE/2), fill=BLACK)
            total += 1
    
    return img, (gp, go_ahead, tying, total)
  

def create_image(player_name: str, game_list, config):
    img = Image.new(mode = "RGBA", size = (IMAGE_X, IMAGE_Y), color = WHITE)
    draw = ImageDraw.Draw(img)

    # Logo in top left
    logo_width, _ = utils.draw_team_logo(img, MARGIN, config["logo"])
    
    # Main goal image
    goal_image, counts = draw_goal(player_name, game_list)
    goal_img_width, goal_img_height = goal_image.width, goal_image.height
    img.paste(goal_image, (MARGIN, get_y(goal_image.height + MARGIN, IMAGE_Y)))

    # Title text
    utils.draw_title_text(draw, logo_width, MARGIN, config, constants.BOUR_80, constants.BOUR_40)
    
    # Detail text on right
    p1 = (111, 197)
    p2 = (111, 351) 
    draw.regular_polygon((goal_img_width + p1[0], get_y(goal_img_height - p1[1], IMAGE_Y), 50), 200, fill=constants.ORANGE_COLORS[0])
    draw.ellipse([
            (goal_img_width + p2[0] - 50, get_y(goal_img_height - p2[1] + 50, IMAGE_Y)), 
            (goal_img_width + p2[0] + 50, get_y(goal_img_height - p2[1] - 50, IMAGE_Y))
        ], outline=constants.ORANGE_COLORS[2], width=4)
    
    draw.multiline_text((goal_img_width + (2 * MARGIN), get_y(goal_img_height - 10, IMAGE_Y)), 
        f"{counts[0]}\n\n\n{counts[1]}\n\n\n{counts[2]}\n\n\n{counts[3]}", fill=BLACK, font=constants.BOUR_60, align="center"
    )
    draw.multiline_text((goal_img_width + (5 * MARGIN), get_y(goal_img_height - 10, IMAGE_Y)),
        "games played\n\n\ngo-ahead goals\n\n\ntying goals\n\n\ntotal goals", fill=(70,70,70), font=constants.BOUR_60
    )
    
    # Dotted circle logo
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    
    img.save(os.path.join("viz", "images", config["img_name"]))

def main():
    player_name = "Nwpo"
    key = "SAUDI ARABIA"
    data_path = os.path.join("replays", "Salt Mine 3", "Stage 2", "Region - EU", "Groups", "Group A", "ZEN VS NWPO")
    game_list = utils.read_series_data(data_path)
    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": "NWPO",
        "t2": "SALT MINE 3 - EU | STAGE 2 | GROUP A",
        "t3": "ZEN 3 - 2 NWPO",
        "c1": constants.TEAM_INFO[key]["c1"],
        "c2": constants.TEAM_INFO[key]["c2"],
        "img_name": os.path.join("Salt Mine 3", "goals", f"{player_name.lower()}_goals.png")
    }
    create_image(player_name, game_list, config)
    
    return 1
  
if __name__ == "__main__":
    main()