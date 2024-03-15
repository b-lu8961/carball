from viz import constants, utils

import numpy as np
import os
from PIL import Image, ImageDraw

IMAGE_X, IMAGE_Y = 2700, 925
MARGIN = 40

MARKER_SIZE = 20
MID_X, MID_Y = (constants.GOAL_X + (MARGIN * 4)) / 2, constants.GOAL_Z / 2

WHITE, BLACK = (255,255,255), (0,0,0)
LIGHT_GREY, DARK_GREY = (140,140,140), (70,70,70)

def get_y(val, img_height):
    return img_height - val

def get_goal_desc(game, goal, score):
    if goal.seconds_remaining < 0:
        secs = -1 * goal.seconds_remaining
        goal_time = f"+{abs(secs // 60)}:{secs % 60:02d}"
    else:
        goal_time = f"{abs(goal.seconds_remaining // 60)}:{goal.seconds_remaining % 60:02d}"
    score_text = f" {score[0]} - [{score[1]}]" if goal.is_orange else f"[{score[0]}] - {score[1]} "
    blue_team = [team for team in game.teams if not team.is_orange][0]
    orange_team = [team for team in game.teams if team.is_orange][0]
    blue_name = "Blue" if blue_team.name == "" else utils.get_team_label(blue_team.name)
    orange_name = "Orange" if orange_team.name == "" else utils.get_team_label(orange_team.name)
    scorer_name = utils.get_player_label(goal.scorer)
    return f"{blue_name} {score_text} {orange_name}", f"{scorer_name} - {goal_time}"

def calculate_goal_map(game_list):
    max_speed, speed_desc, speed_log, speed_game = 0, "", "", ""
    max_time, time_desc, time_log, time_game = 0, "", "", ""
    max_touches, touch_desc, touch_log, touch_game = 0, "", "", ""
    player_data = {}

    goal_locs = [
        [0,0,0], 
        [0,0,0], 
        [0,0,0]
    ]
    bounds_x = [(constants.GOAL_X_THIRD / 2, np.inf), (-constants.GOAL_X_THIRD / 2, constants.GOAL_X_THIRD / 2), (-np.inf, constants.GOAL_X_THIRD / 2)]
    bounds_z = [(0, constants.GOAL_Z_THIRD), (constants.GOAL_Z_THIRD, 2 * constants.GOAL_Z_THIRD), (2 * constants.GOAL_Z_THIRD, constants.GOAL_Z)]
    for game in game_list:
        for player in game.players:
            pn = utils.get_player_label(player.name)
            if pn not in player_data:
                player_data[pn] = [
                    [0,0,0],
                    [0,0,0],
                    [0,0,0]
                ]
        score = [0, 0]
        for goal in game.game_metadata.goals:
            scorer = utils.get_player_label(goal.scorer)
            if goal.is_orange:
                score[1] += 1
            else:
                score[0] += 1
            goal_speed = np.sqrt((goal.ball_vel.pos_x ** 2) + (goal.ball_vel.pos_y ** 2) + (goal.ball_vel.pos_z ** 2)) * (100/2778) * (1/1.609344)
            if goal_speed > max_speed:
                max_speed = goal_speed
                speed_desc = get_goal_desc(game, goal, score)
                speed_log = f"{game.game_metadata.name} {goal.scorer} {goal.seconds_remaining}"
                speed_game = game.game_metadata.tag.split("/")[-1]

            if goal.time_in_off_half > max_time:
                max_time = goal.time_in_off_half
                time_desc = get_goal_desc(game, goal, score)
                time_log = f"{game.game_metadata.name} {goal.scorer} {goal.seconds_remaining}"
                time_game = game.game_metadata.tag.split("/")[-1]
            
            if goal.cons_team_touches > max_touches:
                max_touches = goal.cons_team_touches
                touch_desc = get_goal_desc(game, goal, score)
                touch_log = f"{game.game_metadata.name} {goal.scorer} {goal.seconds_remaining}"
                touch_game = game.game_metadata.tag.split("/")[-1]

            ball_x, ball_z = goal.ball_pos.pos_x, goal.ball_pos.pos_z
            for i in range(len(bounds_z)):
                if bounds_z[i][0] <= ball_z and ball_z < bounds_z[i][1]:
                    for j in range(len(bounds_x)):
                        if bounds_x[j][0] <= ball_x and ball_x < bounds_x[j][1]:
                            goal_locs[j][i] += 1
                            player_data[scorer][j][i] += 1
                            break

    print(speed_desc, round(max_speed, 2), speed_log, speed_game)
    print(time_desc, round(max_time, 2), time_log, time_game)
    print(touch_desc, max_touches, touch_log, touch_game)
    return goal_locs, player_data, [max_speed, speed_desc, speed_game], [max_time, time_desc, time_game], [max_touches, touch_desc, touch_game]

def draw_goal(game_list):
    goal_map, player_data, speed_info, time_info, touch_info = calculate_goal_map(game_list)

    ball_pad = 70
    goal_width, goal_height = constants.GOAL_X - (2 * ball_pad), constants.GOAL_Z - (2 * ball_pad)
    goal_left = (2 * MARGIN) + ball_pad
    width, height = constants.GOAL_X + (MARGIN * 4), round(goal_height) + (MARGIN * 2)
    img = Image.new(mode="RGBA", size = (width, height), color=WHITE)
    
    draw = ImageDraw.Draw(img)
    utils.draw_goal_lines(draw, MARGIN, height, sections=True)

    min_section, max_section = np.min(np.array(goal_map)), np.max(np.array(goal_map))
    coords_x = [
        (goal_left + 5, goal_left + (goal_width / 3) - 5), 
        (goal_left + (goal_width / 3) + 5, goal_left + ((2 * goal_width) / 3) - 5), 
        (goal_left + ((2 * goal_width) / 3) + 5, (2 * MARGIN) + constants.GOAL_X - ball_pad - 5)
    ]
    coords_z = [
        (get_y(ball_pad + (goal_height / 3) - 5, height), get_y(ball_pad + 5, height)), 
        (get_y(ball_pad + ((2 * goal_height) / 3) - 5, height), get_y(ball_pad + (goal_height / 3) + 5, height)), 
        (get_y(constants.GOAL_Z - ball_pad - 5, height), get_y(ball_pad + ((2 * goal_height) / 3) + 5, height))
    ]
    text_x = [
        goal_left + (goal_width / 6),
        goal_left + (goal_width / 2),
        goal_left + (5 * goal_width / 6)
    ]
    text_y = [
        get_y(ball_pad + (goal_height / 6), height),
        get_y(ball_pad + (goal_height / 2), height),
        get_y(ball_pad + (5 * goal_height / 6), height)
    ]
    for i in range(len(coords_z)):
        for j in range(len(coords_x)):
            section_sorted = sorted(player_data.items(), key=lambda item: (-item[1][j][i], str.casefold(item[0])))
            max_player_str = f"{section_sorted[0][0]} ({section_sorted[0][1][j][i]})"
            base_color = constants.REGION_COLORS["NA"][2]
            color = base_color.format(100 + (-50 * ((goal_map[j][i] - min_section + 5) / max_section)))
            text = f"{round(100 * (goal_map[j][i] / np.sum(np.array(goal_map))), 2)}% ({goal_map[j][i]})"
            draw.rectangle([(coords_x[j][0], coords_z[i][0]), (coords_x[j][1], coords_z[i][1])], fill=color)
            draw.multiline_text((text_x[j], text_y[i]), f"{text}\n{max_player_str}", fill=BLACK, 
                font=constants.BOUR_40, align="center", anchor="mm")
        
    return img, speed_info, time_info, touch_info

def create_image(game_list, config):
    img = Image.new(mode = "RGBA", size = (IMAGE_X, IMAGE_Y), color = WHITE)
    draw = ImageDraw.Draw(img)
    
    # Logo in top left
    logo_width, _ = utils.draw_team_logo(img, MARGIN, config["logo"])

    # Title text
    utils.draw_title_text(draw, logo_width, MARGIN, config, constants.BOUR_80, constants.BOUR_40)

    # Main goal image
    goal_image, speed_info, time_info, touch_info = draw_goal(game_list)
    img.paste(goal_image, (MARGIN, get_y(goal_image.height + MARGIN, IMAGE_Y)))

    # Detail text on right
    detail_header = "Fastest Goal\n\n\n\n\nLongest Time in Off. Half\n\n\n\n\nMost Cons. Team Touches"
    draw.multiline_text((goal_image.width + (9 * MARGIN), get_y(goal_image.height + (2.5 * MARGIN), IMAGE_Y)), 
        detail_header, fill=BLACK, font=constants.BOUR_50, align="center", anchor="ma"
    )
    speed_text = f"\n{round(speed_info[0], 2)} mph\n{speed_info[1][0]}\n{speed_info[1][1]} | {speed_info[2]}"
    speed_color = constants.TEAM_INFO["RL ESPORTS"]["c1"] if '[' in speed_info[1][0].split('-')[0] else constants.TEAM_INFO["RL ESPORTS"]["c2"]
    draw.multiline_text((goal_image.width + (9 * MARGIN), get_y(goal_image.height + (2.5 * MARGIN) - 15, IMAGE_Y)),
        speed_text, fill=DARK_GREY, font=constants.BOUR_40, align="center", anchor="ma"
    )
    draw.rounded_rectangle([
        (goal_image.width + MARGIN, get_y(goal_image.height + (2.75 * MARGIN), IMAGE_Y)), 
        (IMAGE_X - (2 * MARGIN), get_y(goal_image.height + (-2 * MARGIN), IMAGE_Y))
    ], 50, outline=speed_color, width=3)
    time_text = f"\n\n\n\n{round(time_info[0], 2)} s\n{time_info[1][0]}\n{time_info[1][1]} | {time_info[2]}"
    time_color = constants.TEAM_INFO["RL ESPORTS"]["c1"] if '[' in time_info[1][0].split('-')[0] else constants.TEAM_INFO["RL ESPORTS"]["c2"]
    draw.multiline_text((goal_image.width + (9 * MARGIN), get_y(goal_image.height + (-0.25 * MARGIN) - 15, IMAGE_Y)),
        time_text, fill=DARK_GREY, font=constants.BOUR_40, align="center", anchor="ma"
    )
    draw.rounded_rectangle([
        (goal_image.width + MARGIN, get_y(goal_image.height + (-2.75 * MARGIN), IMAGE_Y)), 
        (IMAGE_X - (2 * MARGIN), get_y(goal_image.height + (-7.5 * MARGIN), IMAGE_Y))
    ], 50, outline=time_color, width=3)
    touch_text = f"\n\n\n\n{round(touch_info[0], 2)}\n{touch_info[1][0]}\n{touch_info[1][1]} | {touch_info[2]}"
    touch_color = constants.TEAM_INFO["RL ESPORTS"]["c1"] if '[' in touch_info[1][0].split('-')[0] else constants.TEAM_INFO["RL ESPORTS"]["c2"]
    draw.multiline_text((goal_image.width + (9 * MARGIN), get_y(goal_image.height + (-5.75 * MARGIN) - 15, IMAGE_Y)),
        touch_text, fill=DARK_GREY, font=constants.BOUR_40, align="center", anchor="ma"
    )
    draw.rounded_rectangle([
        (goal_image.width + MARGIN, get_y(goal_image.height + (-8.25 * MARGIN), IMAGE_Y)), 
        (IMAGE_X - (2 * MARGIN), get_y(goal_image.height + (-13 * MARGIN), IMAGE_Y))
    ], 50, outline=touch_color, width=3)

    # Dotted circle logo
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    
    os.makedirs(config["img_path"], exist_ok=True)
    img.save(os.path.join(config["img_path"], "event_goals.png"))

def main():
    key = "RL ESPORTS"
    base_path = os.path.join("RLCS 24", "Major 1", "North America", "Open Qualifiers 2")
    game_list = utils.read_group_data(os.path.join("replays", base_path))
    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": "GOAL PLACEMENT",
        "t2": "RLCS 24 NA | OPEN QUALIFIER 2",
        "t3": "SWISS + PLAYOFFS",
        "c1": constants.TEAM_INFO[key]["c1"],
        "c2": constants.TEAM_INFO[key]["c2"],
        "img_path": os.path.join("viz", "images", base_path)
    }
    create_image(game_list, config)
    
    return 1
  
if __name__ == "__main__":
    main()