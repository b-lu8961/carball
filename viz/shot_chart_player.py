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
    gp, shots, goals = 0, 0, 0
    game_iter = utils.read_group_data(data_path)
    for game in game_iter:
        active_players = [player.name for player in game.players]
        if player_name not in active_players:
            continue
        
        if player is None:
            player = [player for player in game.players if player.name == player_name][0]
        gp += 1
        player_hits = [hit for hit in game.game_stats.hits if hit.player_id.id == player.id.id]
        for hit in player_hits:
            size = (((hit.ball_data.pos_z / constants.SCALE) / constants.MAP_Z) * MARKER_SIZE) + MARKER_SIZE
            if player.is_orange:
                hit.location.pos_y *= -1
                
            if hit.match_shot:
                shots += 1
                if hit.match_goal:
                    goals += 1
                    draw_marker(draw, hit.ball_data, "C", height, size, fill=constants.BLUE_COLORS[0])
                else:
                    draw_marker(draw, hit.ball_data, "C", height, size, outline=constants.BLUE_COLORS[2], width=4)
            else:
                # Some goals are not shots
                if hit.match_goal:
                    goals += 1
                    draw_marker(draw, hit.ball_data, "C", height, size, fill=constants.BLUE_COLORS[0])
    
    return img, (gp, shots, goals, round(100 * (goals / shots), 1))

def create_image(player_name, data_path, config):
    img = Image.new(mode = "RGBA", size = (IMAGE_X, IMAGE_Y), color = WHITE)
    draw = ImageDraw.Draw(img)
    
    # Logo in top left
    logo_width, _ = utils.draw_team_logo(img, MARGIN, config["logo"])

    # Main field image
    goal_image, counts = draw_field(player_name, data_path)
    goal_img_width, goal_img_height = goal_image.width, goal_image.height
    img.paste(goal_image, (MARGIN, get_y(goal_image.height + MARGIN, IMAGE_Y)))

    font_big = ImageFont.truetype("C:\\Users\\blu89\\Downloads\\Bourgeois Bold\\Bourgeois Bold.otf", 80)
    font_medium = ImageFont.truetype("C:\\Users\\blu89\\Downloads\\Bourgeois Bold\\Bourgeois Bold.otf", 60)
    font_50 = ImageFont.truetype("C:\\Users\\blu89\\Downloads\\Bourgeois Bold\\Bourgeois Bold.otf", 50)
    font_small = ImageFont.truetype("C:\\Users\\blu89\\Downloads\\Bourgeois Bold\\Bourgeois Bold.otf", 40)

    # Title text
    draw.text((logo_width + 50 + MARGIN, 10 + MARGIN), config["t1"], fill=BLACK, font=font_big)
    draw.text((logo_width + 50 + MARGIN, 90 + MARGIN), config["t2"], fill=DARK_GREY, font=font_small)
    draw.text((logo_width + 50 + MARGIN, 140 + MARGIN), config["t3"], fill=DARK_GREY, font=font_small)

    # Attack direction text
    attack_text = "Attacking Direction"
    attack_len = draw.textlength(attack_text, font=font_50)
    draw.text((MID_X - (attack_len / 2) + MARGIN, get_y(goal_img_height + (1.5 * MARGIN), IMAGE_Y)), 
        f"{attack_text} >>", fill=DARK_GREY, font=font_50)
    
    # Detail text on right
    detail_y = goal_img_height - (4 * MARGIN)
    p1 = (147, 238)
    p2 = (147, 446)
    detail_size = 60

    draw.ellipse([
            (goal_img_width + p1[0] - detail_size, get_y(detail_y - p1[1] + detail_size, IMAGE_Y)), 
            (goal_img_width + p1[0] + detail_size, get_y(detail_y - p1[1] - detail_size, IMAGE_Y))
        ], outline=constants.BLUE_COLORS[2], width=4)
    draw.ellipse([
            (goal_img_width + p2[0] - detail_size, get_y(detail_y - p2[1] + detail_size, IMAGE_Y)), 
            (goal_img_width + p2[0] + detail_size, get_y(detail_y - p2[1] - detail_size, IMAGE_Y))
        ], fill=constants.BLUE_COLORS[0])
    draw.multiline_text((goal_img_width + (2 * MARGIN) + 10, get_y(detail_y, IMAGE_Y)), 
        f"{counts[0]}\n\n\n\n{counts[1]}\n\n\n\n{counts[2]}\n\n\n\n{counts[3]}", fill=BLACK, font=font_medium, align="center"
    )
    draw.multiline_text((goal_img_width + (6 * MARGIN), get_y(detail_y, IMAGE_Y)),
        "games played\n\n\n\nshots\n\n\n\ngoals\n\n\n\nshooting %", fill=DARK_GREY, font=font_medium
    )

    # Legend below detail text
    bbox = draw.multiline_textbbox((goal_img_width + (6 * MARGIN), get_y(detail_y, IMAGE_Y)),
        "games played\n\n\n\nshots\n\n\n\ngoals\n\n\n\nshooting %", font=font_medium)
    utils.draw_height_legend(draw, bbox[3], MARGIN, IMAGE_X, MARKER_SIZE, font_small)
    
    # Dotted circle logo
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    
    img.save(os.path.join("viz", "images", "shots", config["img_name"]))

def main():
    player_name = "ExoTiiK"
    data_path = os.path.join("replays", "Playoffs")
    config = {
        "logo": "Karmine_Corp.png",
        "t1": "EXOTIIK",
        "t2": "KARMINE CORP",
        "t3": "SHOTS | WORLDS '23 - PLAYOFFS",
        "c1": constants.TEAM_INFO["KARMINE CORP"]["c1"],
        "c2": constants.TEAM_INFO["KARMINE CORP"]["c2"],
        "img_name": "exotiik_shots.png"
    }
    create_image(player_name, data_path, config)
    
    return 1
  
if __name__ == "__main__":
    main()