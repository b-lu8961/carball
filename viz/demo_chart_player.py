from viz import constants, utils

import os
from PIL import Image, ImageDraw, ImageFont

IMAGE_X, IMAGE_Y = 2650, 1800
MARGIN = 40

MARKER_SIZE = 15
MID_X, MID_Y = (constants.MAP_Y + (MARGIN * 4)) / 2, (constants.MAP_X + (MARGIN * 2)) / 2

WHITE, BLACK = (255,255,255), (0,0,0)
LIGHT_GREY, DARK_GREY = (140,140,140), (70,70,70)

def get_y(val, img_height):
    return img_height - val

def draw_marker(draw, pos, mark_type, img_height, size=MARKER_SIZE, outline=None, fill=None, width=2):
    base_x = MID_X + (pos.pos_y / constants.SCALE)
    base_y = MID_Y + (pos.pos_x / constants.SCALE)
    if mark_type == "C":
        draw.ellipse([(base_x - size, get_y(base_y + size, img_height)), (base_x + size, get_y(base_y - size, img_height))], 
            outline=outline, fill=fill, width=width)
    elif mark_type == "ahead":
        draw.chord([(base_x - size, get_y(base_y + size, img_height)), (base_x + size, get_y(base_y - size, img_height))], 
            -90, 90, fill=BLACK)
    else:
        draw.chord([(base_x - size, get_y(base_y + size, img_height)), (base_x + size, get_y(base_y - size, img_height))], 
            90, 270, fill=BLACK)

def draw_field(player_name, data_path):
    width, height = round(constants.MAP_Y) + (MARGIN * 4), round(constants.MAP_X) + (MARGIN * 2)
    img = Image.new(mode="RGBA", size = (width, height), color=WHITE)
    
    draw = ImageDraw.Draw(img)
    utils.draw_field_lines(draw, MARGIN, height)

    player = None
    gp, behind, ahead, total = 0, 0, 0, 0
    game_iter = utils.read_group_data(data_path)
    for game in game_iter:
        active_players = [player.name for player in game.players]
        if player_name not in active_players:
            continue

        if player is None:
            player = [player for player in game.players if player.name == player_name][0]
        gp += 1
        player_demos = [demo for demo in game.game_metadata.demos if demo.attacker_name == player_name]
        for demo in player_demos:
            if not demo.is_valid:
                continue

            total += 1
            if player.is_orange:
                demo.location.pos_y *= -1
                demo.location.pos_z *= -1
            if demo.is_behind_ball:
                mark = "behind"
                behind += 1
            else:
                mark = "ahead"
                ahead += 1
            
            marker_color = BLACK
            size = (((demo.location.pos_z / constants.SCALE) / constants.MAP_Z) * MARKER_SIZE) + MARKER_SIZE
            draw_marker(draw, demo.location, mark, height, size = size, fill = marker_color)

    return img, (gp, behind, ahead, total)

def create_image(player_name, data_path, config):
    img = Image.new(mode = "RGBA", size = (IMAGE_X, IMAGE_Y), color = WHITE)
    draw = ImageDraw.Draw(img)
    
    # Logo in top left
    logo_width, _ = utils.draw_team_logo(img, MARGIN, config["logo"])

    # Main goal image
    goal_image, counts= draw_field(player_name, data_path)
    goal_img_width, goal_img_height = goal_image.width, goal_image.height
    img.paste(goal_image, (MARGIN, get_y(goal_image.height + MARGIN, IMAGE_Y)))

    # Title text
    utils.draw_title_text(draw, logo_width, MARGIN, config, constants.BOUR_80, constants.BOUR_40)

    # Attack direction text
    attack_text = "Attacking Direction"
    attack_len = draw.textlength(attack_text, font=constants.BOUR_50)
    draw.text((MID_X - (attack_len / 2) + MARGIN, get_y(goal_img_height + (1.5 * MARGIN), IMAGE_Y)), 
        f"{attack_text} >>", fill=DARK_GREY, font=constants.BOUR_50)

    # Detail text on right
    detail_y = goal_img_height - (4 * MARGIN)
    padding_one = 85
    padding_two = 158
    
    draw.chord([
            (goal_img_width + padding_one - 75, get_y(detail_y - 238 + 75, IMAGE_Y)), 
            (goal_img_width + padding_one + 75, get_y(detail_y - 238 - 75, IMAGE_Y))
        ], -90, 90, outline=DARK_GREY, width=3)
    draw.chord([
            (goal_img_width + padding_two - 75, get_y(detail_y - 448 + 75, IMAGE_Y)), 
            (goal_img_width + padding_two + 75, get_y(detail_y - 448 - 75, IMAGE_Y))
        ], 90, 270, outline=DARK_GREY, width=3)
    draw.multiline_text((goal_img_width + (2 * MARGIN) + 10, get_y(detail_y, IMAGE_Y)), 
        f"{counts[0]}\n\n\n\n{counts[1]}\n\n\n\n{counts[2]}\n\n\n\n{counts[3]}", fill=BLACK, font=constants.BOUR_60, align="center"
    )
    draw.multiline_text((goal_img_width + (5 * MARGIN) + 10, get_y(detail_y, IMAGE_Y)),
        "games played\n\n\n\nbehind ball demos\n\n\n\nahead of ball demos\n\n\n\ntotal demos", fill=DARK_GREY, font=constants.BOUR_60
    )

    # Legend below detail text
    bbox = draw.multiline_textbbox((goal_img_width + (5 * MARGIN) + 10, get_y(detail_y, IMAGE_Y)),
        "games played\n\n\n\nbehind ball demos\n\n\n\nahead of ball demos\n\n\n\ntotal demos", font=constants.BOUR_60)

    utils.draw_height_legend(draw, bbox[3], MARGIN, IMAGE_X, MARKER_SIZE, constants.BOUR_40)

    # Dotted circle logo
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    
    img.save(os.path.join("viz", "images", "demos", config["img_name"]))

def main():
    player_name = "rise."
    display_name = "rise"
    key = "TEAM BDS"
    data_path = os.path.join("replays", "Playoffs")
    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": display_name.upper(),
        "t2": "TEAM BDS",
        "t3": "DEMOS | WORLDS '23 - PLAYOFFS",
        "c1": constants.TEAM_INFO[key]["c1"],
        "c2": constants.TEAM_INFO[key]["c2"],
        "img_name": f"{display_name}_demos.png"
    }
    create_image(player_name, data_path, config)
    
    return 1
  
if __name__ == "__main__":
    main()