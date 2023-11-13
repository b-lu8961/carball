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

def draw_field(team_name, data_path):
    width, height = round(constants.MAP_Y) + (MARGIN * 4), round(constants.MAP_X) + (MARGIN * 2)
    img = Image.new(mode="RGBA", size = (width, height), color=WHITE)

    draw = ImageDraw.Draw(img)
    utils.draw_field_lines(draw, MARGIN, height)
    
    game_iter = utils.read_group_data(data_path)
    gp, shots, saves, goals = 0, 0, 0, 0
    for game in game_iter:
        active_teams = [team.name for team in game.teams]
        if team_name not in active_teams:
            continue

        team_is_orange = [team.is_orange for team in game.teams if team.name == team_name][0]
        gp += 1
        opposing_player_ids = [player.id.id for player in game.players if player.team_name != team_name]
        # Some goals are not shots
        shots_faced = [hit for hit in game.game_stats.hits if (hit.match_shot or hit.match_goal) and 
            hit.player_id.id in opposing_player_ids]
        for shot in shots_faced:
            size = (((shot.ball_data.pos_z / constants.SCALE) / constants.MAP_Z) * MARKER_SIZE) + MARKER_SIZE
            if team_is_orange:
                shot.ball_data.pos_y *= -1

            if shot.match_goal and not shot.match_shot:
                goals += 1
                draw_marker(draw, shot.ball_data, "C", height, size, fill=constants.ORANGE_COLORS[0])

            if shot.match_shot:
                shots += 1
                if shot.match_goal:
                    goals += 1
                    draw_marker(draw, shot.ball_data, "C", height, size, fill=constants.ORANGE_COLORS[0])
                    continue
                last_team_hit = [hit for hit in game.game_stats.hits if hit.player_id.id not in opposing_player_ids and 
                    hit.frame_number > shot.frame_number][0]
                if last_team_hit.match_save:
                    saves += 1
                    draw_marker(draw, shot.ball_data, "C", height, size, outline=constants.BLUE_COLORS[0], width=4)
                else:
                    draw_marker(draw, shot.ball_data, "C", height, size / 2, fill=BLACK)


    draw = ImageDraw.Draw(img)
    utils.draw_field_lines(draw, MARGIN, height)

    return img, (gp, shots, saves, goals)


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

    # Main field image
    goal_image, counts = draw_field(team_name, data_path)
    goal_img_width, goal_img_height = goal_image.width, goal_image.height
    img.paste(goal_image, (MARGIN, get_y(goal_image.height + MARGIN, IMAGE_Y)))

    # Attack direction text
    attack_text = "Defending Direction"
    attack_len = draw.textlength(attack_text, font=font_50)
    draw.text((MID_X - (attack_len / 2) + MARGIN, get_y(goal_img_height + (1.5 * MARGIN), IMAGE_Y)), 
        attack_text, fill=DARK_GREY, font=font_50)
    attack_bbox = draw.textbbox((MID_X - (attack_len / 2) + MARGIN, get_y(goal_img_height + (1.5 * MARGIN), IMAGE_Y)), 
        attack_text, font=font_50)
    arrow_len = draw.textlength("<< ", font_50)
    draw.text((attack_bbox[0] - arrow_len, attack_bbox[1] - 8), "<< ", fill=DARK_GREY, font=font_50)

    # Detail text on right
    detail_y = goal_img_height - (4 * MARGIN)
    p1 = (120, 446) if counts[1] < 100 else (136, 446)
    p2 = (120, 655) if counts[1] < 100 else (136, 655)
    detail_size = 60

    draw.ellipse([
            (goal_img_width + p1[0] - detail_size, get_y(detail_y - p1[1] + detail_size, IMAGE_Y)), 
            (goal_img_width + p1[0] + detail_size, get_y(detail_y - p1[1] - detail_size, IMAGE_Y))
        ], outline=constants.BLUE_COLORS[0], width=4)
    draw.ellipse([
            (goal_img_width + p2[0] - detail_size, get_y(detail_y - p2[1] + detail_size, IMAGE_Y)), 
            (goal_img_width + p2[0] + detail_size, get_y(detail_y - p2[1] - detail_size, IMAGE_Y))
        ], fill=constants.ORANGE_COLORS[0])

    draw.multiline_text((goal_img_width + (2 * MARGIN) + 10, get_y(detail_y, IMAGE_Y)), 
        f"{counts[0]}\n\n\n\n{counts[1]}\n\n\n\n{counts[2]}\n\n\n\n{counts[3]}", fill=BLACK, font=font_medium, align="center"
    )
    draw.multiline_text((goal_img_width + (6 * MARGIN), get_y(detail_y, IMAGE_Y)),
        "games played\n\n\n\nshots faced\n\n\n\nshots saved\n\n\n\ngoals conceded", fill=DARK_GREY, font=font_medium
    )

    # Legend below detail text
    bbox = draw.multiline_textbbox((goal_img_width + (6 * MARGIN), get_y(detail_y, IMAGE_Y)),
        "games played\n\n\n\nshots faced\n\n\n\nshots saved\n\n\n\ngoals conceded", font=font_medium)
    utils.draw_height_legend(draw, bbox[3], MARGIN, IMAGE_X, MARKER_SIZE, font_small)
    
    # Dotted circle logo
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    
    img.save(os.path.join("viz", "images", "saves", config["img_name"]))


def main():
    team_name = "TEAM BDS"
    data_path = os.path.join("replays", "Playoffs")
    config = {
        "logo": "Team_BDS.png",
        "t1": "TEAM BDS",
        "t2": "M0NKEY M00N | RISE | SEIKOO",
        "t3": "SHOTS FACED | WORLDS '23 - PLAYOFFS",
        "c1": constants.TEAM_INFO[team_name]["c1"],
        "c2": constants.TEAM_INFO[team_name]["c2"],
        "img_name": "bds_saves.png"
    }
    create_image(team_name, data_path, config)
    
    return 1
  
if __name__ == "__main__":
    main()