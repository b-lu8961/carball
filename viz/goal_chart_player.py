from viz import constants, utils

import os
from PIL import Image, ImageDraw, ImageFont

IMAGE_X, IMAGE_Y = 2600, 1050
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

def draw_goal(player_name, data_path):
    width, height = constants.GOAL_X + (MARGIN * 4), round(constants.GOAL_Z) + (MARGIN * 2)
    img = Image.new(mode="RGBA", size = (width, height), color=WHITE)
    
    draw = ImageDraw.Draw(img)
    utils.draw_goal_lines(draw, MARGIN, height)
    
    game_iter = utils.read_group_data(data_path)

    gp, go_ahead, tying, total = 0, 0, 0, 0
    for game in game_iter:
        active_players = [player.name for player in game.players]
        if player_name not in active_players:
            continue

        gp += 1
        player_goals = [goal for goal in game.game_metadata.goals if goal.scorer == player_name]
        for goal in player_goals:
            marker_color = constants.ORANGE_COLORS[0] if goal.is_orange else constants.BLUE_COLORS[0]
            if goal.is_go_ahead:
                draw_marker(draw, goal.ball_pos, "C", height,  fill=marker_color)
                go_ahead += 1
            elif goal.is_tying:
                draw_marker(draw, goal.ball_pos, "C", height, outline=marker_color, width=3)
                tying += 1
            else:
                draw_marker(draw, goal.ball_pos, "C", height, size=(MARKER_SIZE/2), fill=BLACK)
            total += 1
    
    return img, (gp, go_ahead, tying, total)
  

def create_image(player_name: str, data_path: str, config):
    img = Image.new(mode = "RGBA", size = (IMAGE_X, IMAGE_Y), color = WHITE)
    
    # Logo in top left
    logo_width, _ = utils.draw_team_logo(img, MARGIN, config["logo"])
    
    # Main goal image
    goal_image, counts = draw_goal(player_name, data_path)
    goal_img_width, goal_img_height = goal_image.width, goal_image.height
    img.paste(goal_image, (MARGIN, get_y(goal_image.height + MARGIN, IMAGE_Y)))
    
    draw = ImageDraw.Draw(img)
    # Title text
    font_big = ImageFont.truetype("C:\\Users\\blu89\\Downloads\\Bourgeois Bold\\Bourgeois Bold.otf", 80)
    font_medium = ImageFont.truetype("C:\\Users\\blu89\\Downloads\\Bourgeois Bold\\Bourgeois Bold.otf", 60)
    font_small = ImageFont.truetype("C:\\Users\\blu89\\Downloads\\Bourgeois Bold\\Bourgeois Bold.otf", 40)
    draw.text((logo_width + 50 + MARGIN, 10 + MARGIN), config["t1"], fill=BLACK, font=font_big)
    draw.text((logo_width + 50 + MARGIN, 90 + MARGIN), config["t2"], fill=(70,70,70), font=font_small)
    draw.text((logo_width + 50 + MARGIN, 140 + MARGIN), config["t3"], fill=(70,70,70), font=font_small)
    
    # Detail text on right
    padding_one = 109 if counts[1] < 10 else 113
    draw.regular_polygon((goal_img_width + padding_one, get_y(goal_img_height - 226, IMAGE_Y), 50), 200, fill=constants.ORANGE_COLORS[0])
    padding_two = 109 if counts[2] < 10 else 113
    draw.ellipse([
            (goal_img_width + padding_two - 50, get_y(goal_img_height - 382 + 50, IMAGE_Y)), 
            (goal_img_width + padding_two + 50, get_y(goal_img_height - 382 - 50, IMAGE_Y))
        ], outline=BLACK, width=4)
    draw.multiline_text((goal_img_width + (2 * MARGIN), get_y(goal_img_height - MARGIN, IMAGE_Y)), 
        f"{counts[0]}\n\n\n{counts[1]}\n\n\n{counts[2]}\n\n\n{counts[3]}", fill=BLACK, font=font_medium, align="center"
    )
    draw.multiline_text((goal_img_width + (5 * MARGIN), get_y(goal_img_height - MARGIN, IMAGE_Y)),
        "games played\n\n\ngo-ahead goals\n\n\ntying goals\n\n\ntotal goals", fill=(70,70,70), font=font_medium
    )
    
    # Dotted circle logo
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    
    img.save(os.path.join("viz", "images", "goals", config["img_name"]))

def main():
    player_name = "Alpha54"
    data_path = os.path.join("replays", "Playoffs")
    config = {
        "logo": "vitality.png",
        "t1": "ALPHA54",
        "t2": "TEAM VITALITY",
        "t3": "GOAL PLACEMENT | WORLDS '23 - PLAYOFFS",
        "c1": constants.TEAM_INFO["TEAM VITALITY"]["c1"],
        "c2": constants.TEAM_INFO["TEAM VITALITY"]["c2"],
        "img_name": "alpha54_goals.png"
    }
    create_image(player_name, data_path, config)
    
    return 1
  
if __name__ == "__main__":
    main()