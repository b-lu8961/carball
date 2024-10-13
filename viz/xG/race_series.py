from viz import constants, utils

import numpy as np
import os
from PIL import Image, ImageDraw

MARGIN = 40

MARKER_SIZE = 20
MID_X, MID_Y = (constants.MAP_Y + (MARGIN * 4)) / 2, (constants.MAP_X + (MARGIN * 2)) / 2

WHITE, BLACK = (255,255,255), (0,0,0)
LIGHT_GREY, DARK_GREY = (140,140,140), (70,70,70)

def get_y(val, img_height):
    return img_height - val

def calculate_exp_goals(game_list, team_names):
    id_map = {}
    exp_goals = {}
    labels = []

    for idx in range(len(game_list)):
        game = game_list[idx]

        if idx == 0:
            print([team.name for team in game.teams])

        blue_team = [team for team in game.teams if not team.is_orange][0]
        orange_team = [team for team in game.teams if team.is_orange][0]
        labels.append(f"Game {idx + 1} | {team_names[0]} {blue_team.score} - {orange_team.score} {team_names[1]}")

        for player in game.players:
            id_map[player.id.id] = player.is_orange

        exp_goals[idx] = {True: [], False: []}
        ot_start = False
        for shot in game.game_metadata.shot_details:
            secs = shot.seconds_remaining
            if secs < 0 and not ot_start:
                ot_start = True
                exp_goals[idx][True].append((0, 0, False))
                exp_goals[idx][False].append((0, 0, False))
            xG_val = utils.get_xG_val(game, shot)
            exp_goals[idx][not shot.is_orange].append((secs, xG_val, shot.is_goal))

        
        last_sec = 300 - game.game_metadata.seconds
        exp_goals[idx][True].append((last_sec, 0, False))
        exp_goals[idx][False].append((last_sec, 0, False))
    
    return exp_goals, labels

def draw_goal_races(game_list, team_names, team_keys):
    xG_data, labels = calculate_exp_goals(game_list, team_names)
    num_games = len(xG_data)
    max_game_len = 300 - min([game_data[True][-1][0] for game_data in xG_data.values()])
    max_game_len = max_game_len if max_game_len <= 300 else max_game_len + 15
    max_xG = 0
    for idx in xG_data:
        game = xG_data[idx]
        blue_xG, orange_xG = 0, 0
        for team in game:
            if team:
                blue_xG += sum(shot[1] for shot in game[team])
            else:
                orange_xG += sum(shot[1] for shot in game[team])
        game_max = max(blue_xG, orange_xG)
        
        if game_max > max_xG:
            max_xG = game_max
    max_xG = np.ceil(max_xG * 2) / 2

    sec_width, one_height = 6, 100
    timeline_height = 110
    race_height = max_xG * one_height
    chart_height = race_height + timeline_height + 60
    width, height = int((max_game_len * sec_width) + (MARGIN * 5.5)), int((num_games * chart_height) + (MARGIN * (num_games + 1))) + 120
    if max_game_len > 300:
        width += 20
    img = Image.new(mode="RGBA", size = (width, height), color=WHITE)
    draw = ImageDraw.Draw(img)

    BLUE = constants.TEAM_INFO["RL ESPORTS"]["c1"]
    ORANGE = constants.TEAM_INFO["RL ESPORTS"]["c2"]
    for idx in range(num_games):
        data = xG_data[idx]
        base_y = (idx * (chart_height + (1.75 * MARGIN))) + race_height + (timeline_height / 2) + (2 * MARGIN)
        base_x = (2.75 * MARGIN)
        game_len = 300 - data[True][-1][0]
        
        # Per chart elements
        # Game label
        game_num_text = labels[idx].split(' | ')[0]
        lbl_len = draw.textlength(labels[idx], font=constants.BOUR_50)
        lbl_one_len = draw.textlength(game_num_text + " | ", font=constants.BOUR_50)
        name_two_len = draw.textlength(team_names[1], font=constants.BOUR_50)
        draw.text((MARGIN - 35, base_y - chart_height + 40), labels[idx], fill=DARK_GREY, font=constants.BOUR_50)
        draw.text((MARGIN - 35 + lbl_one_len, base_y - chart_height + 40), team_names[0], fill=BLUE, font=constants.BOUR_50)
        draw.text((MARGIN - 35 + lbl_len - name_two_len, base_y - chart_height + 40), team_names[1], fill=ORANGE, font=constants.BOUR_50)
        
        # Timeline line
        ot_gap = 15 * sec_width 
        draw.line([(base_x, base_y - 1), ((sec_width * min(game_len, 300)) + base_x, base_y - 1)], fill=DARK_GREY, width=2)
        if game_len > 300:
            draw.line([((sec_width * 300) + ot_gap + base_x, base_y - 1), ((sec_width * game_len) + ot_gap + base_x, base_y - 1)], fill=DARK_GREY, width=2)
        # Timeline ticks
        for i in range(0, game_len + 1, 10):
            bar_start = (sec_width * i) + base_x
            tick_height = 20 if (i % 60 == 0) else 10
            tick_width = 3 if (i % 60 == 0) else 2
            if i >= 300 and game_len > 300:
                # if i + 10 > game_len + 1:
                #     continue   
                draw.line([(bar_start + ot_gap, base_y - tick_height), (bar_start + ot_gap, base_y + tick_height)], 
                    fill=BLACK, width=tick_width)
                if i % 60 == 0:
                    draw.text((bar_start + ot_gap, base_y + 25), f"+{(i // 60) - 5}:00", fill=LIGHT_GREY, font=constants.BOUR_30, anchor="ma")
                if i == 300:
                    draw.line([(bar_start, base_y - tick_height), (bar_start, base_y + tick_height)], 
                        fill=BLACK, width=tick_width)
                    draw.text((bar_start, base_y + 25), f"{5 - (i // 60)}:00", fill=LIGHT_GREY, font=constants.BOUR_30, anchor="ma")
            else:
                draw.line([(bar_start, base_y - tick_height), (bar_start, base_y + tick_height)], 
                    fill=BLACK, width=tick_width)
                if i % 60 == 0:
                    draw.text((bar_start, base_y + 25), f"{5 - (i // 60)}:00", fill=LIGHT_GREY, font=constants.BOUR_30, anchor="ma")
        
        # xG legend
        for i in np.arange(max_xG, -0.01, -0.5):
            y_pos = base_y - (timeline_height / 2) - (i * one_height)
            xG_label = "{:.1f}".format(i)
            if i == max_xG or i == 0:
                xG_label += " xG"
            draw.text((2 * MARGIN, y_pos), xG_label, fill=LIGHT_GREY, font=constants.BOUR_30, anchor="rm")
            utils.linedashed(draw, LIGHT_GREY, 1, base_x, base_x + (300 * sec_width) + 1, y_pos, y_pos, dashlen=5, ratio=3)
            if game_len > 300:
                utils.linedashed(draw, LIGHT_GREY, 1, base_x + (300 * sec_width) + ot_gap, 
                    base_x + (game_len * sec_width) + ot_gap, y_pos, y_pos, dashlen=5, ratio=3)

        # xG lines
        ellipse_locs = []
        game_min_xG = min(np.sum([shot[1] for shot in data[True]]), np.sum([shot[1] for shot in data[False]]))
        for color in data:
            curr_xG = 0
            line_color = BLUE if color else ORANGE
            curr_y = base_y - (timeline_height / 2)
            curr_points = [(base_x, curr_y)]
            ot_start = False
            for shot in data[color]:
                pos_x = (300 - shot[0]) * sec_width
                if shot[0] < 0:
                    if not ot_start:
                        draw.line(curr_points, fill=line_color, width=5)
                        curr_points = [((300 * sec_width) + ot_gap + base_x, curr_y)]
                        ot_start = True
                    pos_x += ot_gap
                curr_points.append((pos_x + base_x, curr_y))
                curr_y -= shot[1] * one_height
                curr_points.append((pos_x + base_x, curr_y))
                curr_xG += shot[1]
                
                if shot[2]:
                    ellipse_color = constants.TEAM_INFO[team_keys[0]]["c1"] if line_color == BLUE else constants.TEAM_INFO[team_keys[1]]["c3"]
                    ellipse_locs.append([
                        (pos_x - 8 + base_x, curr_y - 8),
                        (pos_x + 8 + base_x, curr_y + 8),
                        ellipse_color
                    ])
            
            text_pad = -10 if curr_xG > game_min_xG else 10
            x_pos = base_x + (game_len * sec_width) + 20
            if game_len > 300:
                x_pos += ot_gap
            draw.line(curr_points, fill=line_color, width=5)
            draw.text((x_pos, curr_y + text_pad), str(round(curr_xG, 2)) + " xG", fill=line_color, font=constants.BOUR_30, anchor="lm")
            

        for loc in ellipse_locs:
            draw.ellipse([loc[0], loc[1]], fill=loc[2], outline=BLACK, width=1)

    return img


def create_image(team_names, game_list, team_keys, config):
    goal_race_img = draw_goal_races(game_list, team_names, team_keys)
    
    IMAGE_X, IMAGE_Y = goal_race_img.width + (2 * MARGIN), goal_race_img.height + 400
    img = Image.new(mode = "RGBA", size = (IMAGE_X, IMAGE_Y), color = WHITE)
    draw = ImageDraw.Draw(img)
    
    # Logo in top left
    logo_width, _ = utils.draw_team_logo(img, MARGIN, config["logo"])

    # Title text
    utils.draw_title_text(draw, logo_width, MARGIN, config, constants.BOUR_80, constants.BOUR_40)

    # Game charts
    img.paste(goal_race_img, (MARGIN, get_y(goal_race_img.height + (3 * MARGIN), IMAGE_Y)))

    # Dotted circle logo
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, (16, 75, 228), (172, 136, 53))
    
    os.makedirs(config["img_path"], exist_ok=True)
    img.save(os.path.join(config["img_path"], "xG_timelines.png"))

def main():
    team_names = ("G2 STRIDE", "FURIA")
    team_keys = ("G2 ESPORTS", "FURIA")
    event = "RL ESPORTS"
    base_path = os.path.join("RLCS 24", "World Championship", "[2] Playoffs", "[3] Lower Quarterfinals", "G2 VS FUR")

    config = {
        "logo": constants.TEAM_INFO[event]["logo"],
        "t1": f"{team_keys[0]} 4 - 3 {team_keys[1]}",
        "t2": "RLCS 24 | WORLDS | PLAYOFFS | LOWER QF",
        "t3": "EXPECTED GOAL TIMELINES",
        "c1": constants.TEAM_INFO[event]["c1"],
        "c2": constants.TEAM_INFO[event]["c2"],
        "img_path": os.path.join("viz", "images", base_path, "xG")
    }

    data_path = os.path.join("replays", base_path)
    game_list = utils.read_series_data(data_path)
    create_image(team_names, game_list, team_keys, config)
    
    return 0
  
if __name__ == "__main__":
    main()