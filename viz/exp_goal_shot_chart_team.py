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

def draw_field(team_name, game_list):
    width, height = round(constants.MAP_Y) + (MARGIN * 4), round(constants.MAP_X) + (MARGIN * 2)
    img = Image.new(mode="RGBA", size = (width, height), color=WHITE)
    
    draw = ImageDraw.Draw(img)
    utils.draw_field_lines(draw, MARGIN, height)

    team, color_set = None, None
    gp, shots, goals, xG = 0, 0, 0, 0
    
    for game in game_list:
        active_teams = [team.name for team in game.teams]
        #print(active_teams)
        if team_name not in active_teams:
            continue
        
        if team is None:
            team = [team for team in game.teams if team.name == team_name][0]
            color_set = constants.ORANGE_COLORS if team.is_orange else constants.BLUE_COLORS
        gp += 1
        for shot in game.game_metadata.shot_details:
            corr_hit = [hit for hit in game.game_stats.hits if hit.frame_number == shot.frame_number][0]
            corr_player = [player for player in game.players if player.id.id == corr_hit.player_id.id][0]
            if corr_player.is_orange != team.is_orange:
                continue

            if team.is_orange:
                shot.ball_pos.pos_y *= -1
                shot.ball_pos.pos_x *= -1
                
            shots += 1
            xG_val = utils.get_xG_val(game, shot)
            size = (xG_val * (3 * MARKER_SIZE)) + MARKER_SIZE
            xG += xG_val
            if shot.is_goal:
                goals += 1
                draw_marker(draw, shot.ball_pos, "C", height, size, fill=color_set[0])
            else:
                draw_marker(draw, shot.ball_pos, "C", height, size, outline=color_set[2], width=4)
    
    return img, (gp, shots, goals, "{:.2f}".format(xG)), color_set

def create_image(team_name, game_list, config):
    img = Image.new(mode = "RGBA", size = (IMAGE_X, IMAGE_Y), color = WHITE)
    draw = ImageDraw.Draw(img)
    
    # Logo in top left
    logo_width, _ = utils.draw_team_logo(img, MARGIN, config["logo"])

    # Title text
    utils.draw_title_text(draw, logo_width, MARGIN, config, constants.BOUR_80, constants.BOUR_40)

    # Main field image
    field_img, counts, color_set = draw_field(team_name, game_list)
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
        ], fill=color_set[0])
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
    team_name = "TEAM VITALITY"
    key = "TEAM VITALITY"
    data_path = os.path.join("replays", "RLCS 23", "Worlds", "Main Event", "Playoffs", "Quarterfinals", "VIT vs FLCN")
    game_list = utils.read_series_data(data_path)
    #game_list = utils.read_group_data(data_path)
    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": key,
        "t2": "ALPHA54 | RADOSIN | ZEN",
        "t3": "RLCS WORLDS 23 | PLAYOFFS | QUARTERFINAL",
        "c1": constants.TEAM_INFO[key]["c1"],
        "c2": constants.TEAM_INFO[key]["c2"],
        "img_name": os.path.join("exp_goals", "shot_charts", f"{team_name}_shots.png")
    }
    create_image(team_name, game_list, config)
    
    return 1
  
if __name__ == "__main__":
    main()