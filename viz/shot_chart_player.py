from viz import constants, utils

import os
from PIL import Image, ImageDraw

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

def draw_field(player_name, game_list, color_set):
    width, height = round(constants.MAP_Y) + (MARGIN * 4), round(constants.MAP_X) + (MARGIN * 2)
    img = Image.new(mode="RGBA", size = (width, height), color=WHITE)
    
    draw = ImageDraw.Draw(img)
    utils.draw_field_lines(draw, MARGIN, height)

    player = None
    gp, shots, goals = 0, 0, 0
    
    for game in game_list:
        active_players = [player.name for player in game.players]
        #print(active_players)
        if player_name not in active_players:
            continue
        
        if player is None:
            player = [player for player in game.players if player.name == player_name][0]
        gp += 1
        player_hits = [hit for hit in game.game_stats.hits if hit.player_id.id == player.id.id]
        for hit in player_hits:
            size = ((((hit.ball_data.pos_z - constants.BALL_RAD) / constants.SCALE) / constants.MAP_Z) * (1.5 * MARKER_SIZE)) + MARKER_SIZE
            if player.is_orange:
                hit.ball_data.pos_y *= -1
                hit.ball_data.pos_x *= -1
                
            if hit.match_shot:
                shots += 1
                if hit.match_goal:
                    goals += 1
                    draw_marker(draw, hit.ball_data, "C", height, size, fill=color_set[0])
                else:
                    draw_marker(draw, hit.ball_data, "C", height, size, outline=color_set[2], width=4)
            else:
                # Some goals are not shots
                if hit.match_goal:
                    goals += 1
                    draw_marker(draw, hit.ball_data, "C", height, size, fill=color_set[0])
    
    return img, (gp, shots, goals, round(100 * (goals / shots), 1))

def create_image(player_name, game_list, config, color_set):
    img = Image.new(mode = "RGBA", size = (IMAGE_X, IMAGE_Y), color = WHITE)
    draw = ImageDraw.Draw(img)
    
    # Logo in top left
    logo_width, _ = utils.draw_team_logo(img, MARGIN, config["logo"])

    # Title text
    utils.draw_title_text(draw, logo_width, MARGIN, config, constants.BOUR_80, constants.BOUR_40)

    # Main field image
    field_img, counts = draw_field(player_name, game_list, color_set)
    img.paste(field_img, (MARGIN, get_y(field_img.height + MARGIN, IMAGE_Y)))

    # Attack direction text
    attack_text = "Attacking Direction"
    attack_len = draw.textlength(attack_text, font=constants.BOUR_50)
    draw.text((MID_X - (attack_len / 2) + MARGIN, get_y(field_img.height + (1.5 * MARGIN), IMAGE_Y)), 
        f"{attack_text} >>", fill=DARK_GREY, font=constants.BOUR_50)
    
    # Detail text on right
    detail_y = field_img.height - (4 * MARGIN)
    p1 = (147, 238)
    p2 = (147, 446)
    detail_size = 60

    draw.ellipse([
            (field_img.width + p1[0] - detail_size, get_y(detail_y - p1[1] + detail_size, IMAGE_Y)), 
            (field_img.width + p1[0] + detail_size, get_y(detail_y - p1[1] - detail_size, IMAGE_Y))
        ], outline=color_set[2], width=4)
    draw.ellipse([
            (field_img.width + p2[0] - detail_size, get_y(detail_y - p2[1] + detail_size, IMAGE_Y)), 
            (field_img.width + p2[0] + detail_size, get_y(detail_y - p2[1] - detail_size, IMAGE_Y))
        ], fill=color_set[0])
    draw.multiline_text((field_img.width + (2 * MARGIN) + 10, get_y(detail_y, IMAGE_Y)), 
        f"{counts[0]}\n\n\n\n{counts[1]}\n\n\n\n{counts[2]}\n\n\n\n{counts[3]}", fill=BLACK, font=constants.BOUR_60, align="center"
    )
    draw.multiline_text((field_img.width + (6 * MARGIN), get_y(detail_y, IMAGE_Y)),
        "games played\n\n\n\nshots\n\n\n\ngoals\n\n\n\nshooting %", fill=DARK_GREY, font=constants.BOUR_60
    )

    # Legend below detail text
    bbox = draw.multiline_textbbox((field_img.width + (6 * MARGIN), get_y(detail_y, IMAGE_Y)),
        "games played\n\n\n\nshots\n\n\n\ngoals\n\n\n\nshooting %", font=constants.BOUR_60)
    utils.draw_height_legend(draw, bbox[3], MARGIN, IMAGE_X, MARKER_SIZE, constants.BOUR_40)
    
    # Dotted circle logo
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    
    img.save(os.path.join("viz", "images", config["img_name"]))

def main():
    player_name = "Little dIAZ^^"
    key = "BRAZIL"
    data_path = os.path.join("replays", "Salt Mine 3", "Finals", "Region - NA", "UBSF - FIRSTKILLER VS DIAZ")
    game_list = utils.read_series_data(data_path)
    #game_list = utils.read_group_data(data_path)
    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": "DIAZ",
        "t2": "SALT MINE 3 - NA | FINALS | UBSF",
        "t3": "FIRSTKILLER 2 - 3 DIAZ",
        "c1": constants.TEAM_INFO[key]["c1"],
        "c2": constants.TEAM_INFO[key]["c2"],
        "img_name": os.path.join("Salt Mine 3", "shots", "diaz_shots.png")
    }
    create_image(player_name, game_list, config, constants.ORANGE_COLORS)
    
    return 1
  
if __name__ == "__main__":
    main()