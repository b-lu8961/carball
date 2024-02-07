from viz import constants, utils

import os
from PIL import Image, ImageDraw

IMAGE_X, IMAGE_Y = 2650, 1800
MARGIN = 40

MARKER_SIZE = 10
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
    gp, shots, goals, xG = 0, 0, 0, 0
    goal_locs = []
    
    for game in game_list:
        active_players = [player.name for player in game.players]
        #print(active_players)
        if player_name not in active_players:
            continue
        
        if player is None:
            player = [player for player in game.players if player.name == player_name][0]
        gp += 1
        for shot in game.game_metadata.shot_details:
            corr_hit = [hit for hit in game.game_stats.hits if hit.frame_number == shot.frame_number][0]
            if corr_hit.player_id.id != player.id.id:
                continue

            if player.is_orange:
                shot.ball_pos.pos_y *= -1
                shot.ball_pos.pos_x *= -1
                
            shots += 1
            xG_val = utils.get_xG_val(game, shot)
            size = (xG_val * (3 * MARKER_SIZE)) + MARKER_SIZE
            xG += xG_val
            if shot.is_goal:
                goals += 1
                goal_locs.append(shot.ball_pos)
                draw_marker(draw, shot.ball_pos, "C", height, size, fill=color_set[0], outline=color_set[1], width=3)
            else:
                draw_marker(draw, shot.ball_pos, "C", height, size, outline=color_set[2], width=4)
    
    return img, (gp, shots, goals, "{:.2f}".format(xG))

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
    p1 = (141, 238) if len(counts[3]) == 4 else (156, 238)
    p2 = (141, 446) if len(counts[3]) == 4 else (156, 446)
    detail_size = 60

    draw.ellipse([
            (field_img.width + p1[0] - detail_size, get_y(detail_y - p1[1] + detail_size, IMAGE_Y)), 
            (field_img.width + p1[0] + detail_size, get_y(detail_y - p1[1] - detail_size, IMAGE_Y))
        ], outline=color_set[2], width=4)
    draw.ellipse([
            (field_img.width + p2[0] - detail_size, get_y(detail_y - p2[1] + detail_size, IMAGE_Y)), 
            (field_img.width + p2[0] + detail_size, get_y(detail_y - p2[1] - detail_size, IMAGE_Y))
        ], fill=color_set[0], outline=color_set[1], width=3)
    draw.multiline_text((field_img.width + (2 * MARGIN) + 10, get_y(detail_y, IMAGE_Y)), 
        f"{counts[0]}\n\n\n\n{counts[1]}\n\n\n\n{counts[2]}\n\n\n\n{counts[3]}", fill=BLACK, font=constants.BOUR_60, align="center"
    )
    draw.multiline_text((field_img.width + (6.5 * MARGIN), get_y(detail_y, IMAGE_Y)),
        "games played\n\n\n\nshots\n\n\n\ngoals\n\n\n\nxG", fill=DARK_GREY, font=constants.BOUR_60
    )

    # Legend below detail text
    bbox = draw.multiline_textbbox((field_img.width + (6 * MARGIN), get_y(detail_y, IMAGE_Y)),
        "games played\n\n\n\nshots\n\n\n\ngoals\n\n\n\nxG", font=constants.BOUR_60)
    utils.draw_circle_legend(draw, bbox[3], MARGIN, IMAGE_X, MARKER_SIZE, constants.BOUR_40, 
        scaling=(2, 3, 4), labels=(("0 xG", 1), ("1 xG", 8.25)))
    
    # Dotted circle logo
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    
    img.save(os.path.join("viz", "images", config["img_name"]))

def main():
    player_name = "hockser"
    key = "SPACESTATION"
    data_path = os.path.join("replays", "The Draw", "Event 9")
    #game_list = utils.read_series_data(data_path)
    game_list = utils.read_group_data(data_path)
    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": "HOCKSER",
        "t2": "THE DRAW #9 | MAIN EVENT",
        "t3": "XG SHOT CHART",
        "c1": constants.TEAM_INFO[key]["c1"],
        "c2": constants.TEAM_INFO[key]["c2"],
        "img_name": os.path.join("The Draw", "exp_goals", "shot_charts", f"{player_name}_shots.png")
    }
    create_image(player_name, game_list, config, constants.ORANGE_COLORS)
    
    return 1
  
if __name__ == "__main__":
    main()