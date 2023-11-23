from viz import constants, utils

import os
from PIL import Image, ImageDraw, ImageFont

IMAGE_X, IMAGE_Y = 2650, 1800
MARGIN = 40

MARKER_SIZE = 20
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
    
    gp, shots, saves, goals = 0, 0, 0, 0
    for game in game_list:
        active_teams = [team.name for team in game.teams]
        if team_name not in active_teams:
            continue

        team_is_orange = [team.is_orange for team in game.teams if team.name == team_name][0]
        goal_color = constants.BLUE_COLORS if team_is_orange else constants.ORANGE_COLORS
        save_color = constants.ORANGE_COLORS if team_is_orange else constants.BLUE_COLORS

        gp += 1
        team_ids = [player.id.id for player in game.players if player.team_name == team_name]
        save_list = [hit for hit in game.game_stats.hits if hit.match_save and hit.player_id.id in team_ids]
        shot_frames = []
        for save in save_list:
            saves += 1
            last_opposing_touch = [hit for hit in game.game_stats.hits if hit.player_id.id not in team_ids and
                hit.frame_number < save.frame_number][-1]
            if last_opposing_touch.match_shot:
                shots += 1
                shot_frames.append(last_opposing_touch.frame_number)
            if team_is_orange:
                last_opposing_touch.ball_data.pos_y *= -1
                last_opposing_touch.ball_data.pos_x *= -1
            size = (((last_opposing_touch.ball_data.pos_z / constants.SCALE) / constants.MAP_Z) * (1.5 * MARKER_SIZE)) + MARKER_SIZE
            draw_marker(draw, last_opposing_touch.ball_data, "C", height, size, outline=save_color[0], width=4)

        # Some goals are not shots
        shots_faced = [hit for hit in game.game_stats.hits if (hit.match_shot or hit.match_goal) and 
            hit.player_id.id not in team_ids]
        for shot in shots_faced:
            size = (((shot.ball_data.pos_z / constants.SCALE) / constants.MAP_Z) * (1.5 * MARKER_SIZE)) + MARKER_SIZE
            if team_is_orange:
                shot.ball_data.pos_y *= -1
                shot.ball_data.pos_x *= -1

            if shot.match_goal and not shot.match_shot:
                goals += 1
                draw_marker(draw, shot.ball_data, "C", height, size, fill=goal_color[0])

            if shot.match_shot:
                if shot.match_goal:
                    shots += 1
                    goals += 1
                    draw_marker(draw, shot.ball_data, "C", height, size, fill=goal_color[0])
                    continue

                if shot.frame_number not in shot_frames:
                    shots += 1
                    draw_marker(draw, shot.ball_data, "C", height, size / 2, fill=BLACK)
                
    return img, (gp, shots, saves, goals)


def create_image(team_name: str, game_list, config):
    img = Image.new(mode = "RGBA", size = (IMAGE_X, IMAGE_Y), color = WHITE)
    draw = ImageDraw.Draw(img)
    
    # Logo in top left
    logo_width, _ = utils.draw_team_logo(img, MARGIN, config["logo"])

    # Title text
    utils.draw_title_text(draw, logo_width, MARGIN, config, constants.BOUR_80, constants.BOUR_40)

    # Main field image
    goal_image, counts = draw_field(team_name, game_list)
    goal_img_width, goal_img_height = goal_image.width, goal_image.height
    img.paste(goal_image, (MARGIN, get_y(goal_image.height + MARGIN, IMAGE_Y)))

    # Attack direction text
    attack_text = "Defending Direction"
    attack_len = draw.textlength(attack_text, font=constants.BOUR_50)
    draw.text((MID_X - (attack_len / 2) + MARGIN, get_y(goal_img_height + (1.5 * MARGIN), IMAGE_Y)), 
        attack_text, fill=DARK_GREY, font=constants.BOUR_50)
    attack_bbox = draw.textbbox((MID_X - (attack_len / 2) + MARGIN, get_y(goal_img_height + (1.5 * MARGIN), IMAGE_Y)), 
        attack_text, font=constants.BOUR_50)
    arrow_len = draw.textlength("<< ", constants.BOUR_50)
    draw.text((attack_bbox[0] - arrow_len, attack_bbox[1] - 8), "<< ", fill=DARK_GREY, font=constants.BOUR_50)

    # Detail text on right
    detail_y = goal_img_height - (4 * MARGIN)
    p1 = (120, 446) if counts[1] < 100 else (136, 446)
    p2 = (120, 655) if counts[1] < 100 else (136, 655)
    detail_size = 60

    draw.ellipse([
            (goal_img_width + p1[0] - detail_size, get_y(detail_y - p1[1] + detail_size, IMAGE_Y)), 
            (goal_img_width + p1[0] + detail_size, get_y(detail_y - p1[1] - detail_size, IMAGE_Y))
        ], outline=constants.ORANGE_COLORS[0], width=4)
    draw.ellipse([
            (goal_img_width + p2[0] - detail_size, get_y(detail_y - p2[1] + detail_size, IMAGE_Y)), 
            (goal_img_width + p2[0] + detail_size, get_y(detail_y - p2[1] - detail_size, IMAGE_Y))
        ], fill=constants.BLUE_COLORS[0])

    draw.multiline_text((goal_img_width + (2 * MARGIN) + 10, get_y(detail_y, IMAGE_Y)), 
        f"{counts[0]}\n\n\n\n{counts[1]}\n\n\n\n{counts[2]}\n\n\n\n{counts[3]}", fill=BLACK, font=constants.BOUR_60, align="center"
    )
    draw.multiline_text((goal_img_width + (6 * MARGIN), get_y(detail_y, IMAGE_Y)),
        "games played\n\n\n\nshots faced\n\n\n\nsaves made\n\n\n\ngoals conceded", fill=DARK_GREY, font=constants.BOUR_60
    )

    # Legend below detail text
    bbox = draw.multiline_textbbox((goal_img_width + (6 * MARGIN), get_y(detail_y, IMAGE_Y)),
        "games played\n\n\n\nshots faced\n\n\n\nsaves made\n\n\n\ngoals conceded", font=constants.BOUR_60)
    utils.draw_height_legend(draw, bbox[3], MARGIN, IMAGE_X, MARKER_SIZE, constants.BOUR_40)
    
    # Dotted circle logo
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    
    img.save(os.path.join("viz", "images", config["img_name"]))


def main():
    team_name = "ATOMIK"
    key = "SPAIN"
    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": "ATOMIK",
        "t2": "SALT MINE 3 - EU | STAGE 2 | GROUP B",
        "t3": "RW9 3 - 1 ATOMIK",
        "c1": constants.TEAM_INFO[key]["c1"],
        "c2": constants.TEAM_INFO[key]["c2"],
        "img_name": os.path.join("Salt Mine 3", "saves", f"{team_name.lower()}_saves.png")
    }

    data_path = os.path.join("replays", "Salt Mine 3", "Stage 2", "Region - EU", "Groups", "Group B", "RW9 VS ATOMIK")
    game_iter = utils.read_series_data(data_path)
    create_image(team_name, game_iter, config)
    
    return 1
  
if __name__ == "__main__":
    main()