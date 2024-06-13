from viz import constants, utils

import json
import numpy as np
import os
from PIL import Image, ImageDraw

MARGIN = 40

MARKER_SIZE = 10

WHITE, BLACK = (255,255,255), (0,0,0)
LIGHT_GREY, DARK_GREY = (180,180,180), (70,70,70)

HEADER_HEIGHT = 325
LAYER_1_HEIGHT = 1200 + MARGIN
LAYER_2_HEIGHT = 2000 + MARGIN
PL_LAYER_HEIGHT = 1800 + MARGIN

def get_y(val, img_height):
    return img_height - val
            
def draw_shot_marker(draw, pos, img_height, size=MARKER_SIZE, outline=None, fill=None, width=2):
    MID_X, MID_Y = (constants.MAP_Y + (MARGIN * 4)) / 2, (constants.MAP_X + (MARGIN * 2)) / 2
    base_x = MID_X + (pos[1] / constants.SCALE)
    base_y = MID_Y + (pos[0] / constants.SCALE)
    draw.ellipse([(base_x - size, get_y(base_y + size, img_height)), (base_x + size, get_y(base_y - size, img_height))], 
        outline=outline, fill=fill, width=width)

def draw_fields_alt(shot_data):
    width, height = round(constants.MAP_Y) + (MARGIN * 4), round(constants.MAP_X) + (MARGIN * 2)

    for_img = Image.new(mode="RGBA", size = (width, height), color=WHITE)
    for_draw = ImageDraw.Draw(for_img)
    utils.draw_field_lines(for_draw, MARGIN, height)
    against_img = Image.new(mode="RGBA", size = (width, height), color=WHITE)
    against_draw = ImageDraw.Draw(against_img)
    utils.draw_field_lines(against_draw, MARGIN, height)

    for team in shot_data:
        for shot in shot_data[team]:
            shot_draw = for_draw if team == "for" else against_draw
            color_set = constants.BLUE_COLORS if team == "for" else constants.ORANGE_COLORS
            if shot[2]:
                draw_shot_marker(shot_draw, shot[0], height, shot[1], fill=color_set[0], outline=color_set[1], width=3)
            else:
                draw_shot_marker(shot_draw, shot[0], height, shot[1], outline=color_set[2], width=4)
    
    return for_img, against_img

def draw_header(img: Image.Image, draw: ImageDraw.ImageDraw, config):
    # Logo in top left
    pos = (MARGIN, MARGIN + 20)
    logo_width = None
    with Image.open(os.path.join("viz", "images", "logos", config["logo"])) as logo:
        divisor = max(logo.width / 300, logo.height / 300)
        logo_width, logo_height = round(logo.width / divisor), round(logo.height / divisor)
        logo_small = logo.resize((logo_width, logo_height))
        try:
            img.paste(logo_small, pos, mask = logo_small)
        except ValueError:
            img.paste(logo_small, pos)

    # Title text
    font_one, font_two = constants.BOUR_100, constants.BOUR_60
    draw.text((logo_width + 50 + MARGIN, MARGIN), config["t1"], fill=(0,0,0), font=font_one)
    draw.text((logo_width + 50 + MARGIN, 100 + MARGIN), config["t2"], fill=(70,70,70), font=font_two)
    draw.text((logo_width + 50 + MARGIN, 170 + MARGIN), config["t3"], fill=(70,70,70), font=font_two)

    # Dotted circle logo
    utils.draw_dotted_circle(draw, img.width, MARGIN, config["c1"], config["c2"])

def draw_layer_1(img: Image.Image, draw: ImageDraw.ImageDraw, series_data, player_data, config):
    LAYER_1_TOP = HEADER_HEIGHT
    img_14 = img.width / 4
    series_list = list(series_data.keys())
    gf_series = [s for s in series_list if s[1] == "Grand Final"]
    po_series = [s for s in series_list if s[0] == "Playoffs"]

    # Overview
    ovw_left, ovw_right = (3 * MARGIN), img_14
    if len(po_series) > 0:
       ovw_right += 600
    ovw_base_y, ovw_step = LAYER_1_TOP + 140, 200
    draw.text((((ovw_left + ovw_right) / 2) - 10, LAYER_1_TOP), "Series Results", fill=BLACK, font=constants.BOUR_90, anchor="ma")

    if len(gf_series) > 0:
        gf = gf_series[0]
        series_list.remove(gf)
        series_list.append(gf)
    num_swiss = len([s for s in series_list if s[0] == "Swiss"])
    for i in range(len(series_list)):
        series, res = series_list[i], series_data[series_list[i]]
        series_top = ovw_base_y + (i * ovw_step) if i < num_swiss else ovw_base_y + ((i - num_swiss) * ovw_step)
        series_label = f"{series[0]} | {series[1]}"
        series_result = f"{res[0]} - {res[1]} vs {series[2]}"
        x_pad = 0 if series[0] != "Playoffs" else 750

        draw.text((ovw_left + MARGIN + x_pad, series_top), series_label, fill=DARK_GREY, font=constants.BOUR_60)
        draw.text((ovw_left + (2 * MARGIN) + x_pad, series_top + 80), series_result, fill=BLACK, font=constants.BOUR_60)
        
        line_color = (50,250,50) if res[0] > res[1] else (250,50,50)
        draw.line([(ovw_left + x_pad + 20, series_top + 10), (ovw_left + x_pad + 20, series_top + 130)], fill=line_color, width=4)

    draw.rounded_rectangle([(ovw_left - 30, ovw_base_y - 20), (ovw_right, LAYER_1_TOP + LAYER_1_HEIGHT - 108)], 75,
        outline=constants.REGION_COLORS[config["region"]][0], width=5)
    
    # Scoreboard
    stats_left = ovw_right + (2 * MARGIN)
    if len(po_series) == 0:
        stats_left += 300
    player_list = sorted([pl for pl in player_data.keys() if pl != "against" and pl != "fasi"], key=str.casefold)
    player_list.append("against")

    pl_top, pl_step = LAYER_1_TOP + 140, 150
    draw.text((stats_left + (2 * MARGIN), pl_top - 100), "FOR", fill=DARK_GREY, font=constants.BOUR_80)
    for i in range(len(player_list)):
        y_pad = 90 if i <= 2 else 350 
        pl_base = pl_top + (i * pl_step) + y_pad
        pl_name = player_list[i] if i != 3 else "Total"
        draw.text((stats_left + (1 * MARGIN), pl_base), pl_name, fill=BLACK, font=constants.BOUR_70)

        rect_color = constants.TEAM_INFO["RLCS"]["c1"] if i <= 2 else constants.TEAM_INFO["RLCS"]["c2"]
        draw.rounded_rectangle([(stats_left, pl_base - 20), (stats_left + 2200, pl_base + 95)], 50, outline=rect_color, width=5)

        pl_data = player_data[player_list[i]]
        stat_step = 250
        for j in range(len(pl_data)):
            stat_name = list(pl_data.keys())[j]
            stat_x = stats_left + 600 + (j * stat_step)
            if i == 0:
                draw.text((stat_x, pl_base - 90), stat_name.upper(), fill=DARK_GREY, font=constants.BOUR_60, anchor="ma")
            if i == 3:
                draw.text((stats_left + (2 * MARGIN), pl_base - 180), "AGAINST", fill=DARK_GREY, font=constants.BOUR_80)
                draw.text((stat_x, pl_base - 90), stat_name.upper(), fill=DARK_GREY, font=constants.BOUR_60, anchor="ma")
            stat_val = str(pl_data[stat_name]) if stat_name != "xG" else str(round(pl_data[stat_name], 1))
            draw.text((stat_x, pl_base + 8), stat_val, fill=BLACK, font=constants.BOUR_60, anchor="ma")
                

def get_rot_text(draw, text, font=constants.BOUR_60, height=50, fill=BLACK, rot=90):
    img_len = round(draw.textlength(text, font=font))
    img = Image.new(mode="RGB", size=(img_len, height), color=WHITE)
    img_draw = ImageDraw.Draw(img)
    img_draw.text((0, 0), text, fill=fill, font=font)
    return img.rotate(rot, expand=True), img_len

def draw_layer_2(img: Image.Image, draw: ImageDraw.ImageDraw, config, shot_data, text_data):
    LAYER_2_TOP = HEADER_HEIGHT + LAYER_1_HEIGHT
    img_24 = img.width / 2
    
    for_img, against_img = draw_fields_alt(shot_data)
    # Left field: shots taken
    for_rot = for_img.rotate(90, expand=True)
    for_left = int(1.5 * MARGIN)
    img.paste(for_rot, (for_left, LAYER_2_TOP + 60))
    draw.text((for_left + (for_img.height / 2), LAYER_2_TOP), "Shots", fill=constants.TEAM_INFO["RLCS"]["c1"], font=constants.BOUR_90, anchor="ma")
    att_img, att_len = get_rot_text(draw, "<< Attacking Direction", font=constants.BOUR_50, height=60, fill=DARK_GREY, rot=-90)
    img.paste(att_img, (round(for_left + for_img.height - 35), round(LAYER_2_TOP + 60 - (att_len / 2) + (constants.MAP_Y + (MARGIN * 4)) / 2)))
    for_shots, for_goals = len(shot_data["for"]), len([shot for shot in shot_data["for"] if shot[2]])
    draw.text((for_left + (for_rot.width / 2), LAYER_2_TOP + 60 + for_rot.height - 20), 
        "{} goals | {} shots".format(for_goals, for_shots), 
        fill=DARK_GREY, font=constants.BOUR_70, anchor="ma")
    
    # Right field: shots allowed
    against_rot = against_img.rotate(90, expand=True)
    against_left = img.width - against_img.height - int(1.5 * MARGIN)
    img.paste(against_rot, (against_left, LAYER_2_TOP + 60))
    draw.text((against_left + (against_img.height / 2), LAYER_2_TOP), "Shots Against", fill=constants.TEAM_INFO["RLCS"]["c2"], font=constants.BOUR_90, anchor="ma")
    def_img, def_len = get_rot_text(draw, "<< Defending Direction", font=constants.BOUR_50, height=60, fill=DARK_GREY, rot=90)
    img.paste(def_img, (round(against_left - 25), round(LAYER_2_TOP + 60 - (def_len / 2) + (constants.MAP_Y + (MARGIN * 4)) / 2)))
    against_shots, against_goals = len(shot_data["against"]), len([shot for shot in shot_data["against"] if shot[2]])
    draw.text((against_left + (against_rot.width / 2), LAYER_2_TOP + 60 + against_rot.height - 20), 
        "{} goals | {} shots".format(against_goals, against_shots), 
        fill=DARK_GREY, font=constants.BOUR_70, anchor="ma")

    # Middle space: Game highs
    text_base, step = LAYER_2_TOP + 175, 550
    
    colors = [config["c1"], config["c2"], constants.TEAM_INFO[config["key"]]["c3"]]
    text_headers = ["Fastest Goal", "Highest % Time Supersonic", "Most Demos"]
    for i in range(len(text_data)):
        text_top = text_base + (i * step)
        rect_color = colors[i] if colors[i] != (255, 255, 255) else colors[0]
        draw.rounded_rectangle([(img_24 - 450, text_top - 20), (img_24 + 450, text_top + step - 260)], 50, outline=rect_color, width=4)
        draw.text((img_24, text_top), text_headers[i], fill=BLACK, font=constants.BOUR_80, anchor="ma")
        draw.text((img_24, text_top + 100), text_data[i], fill=DARK_GREY, font=constants.BOUR_60, anchor="ma", align="center")
    
    utils.draw_circle_legend(draw, text_top + 260, MARGIN, img_24 + 430, MARKER_SIZE, constants.BOUR_50, 
        left_x=(img_24 - 370), scaling=(2, 3, 4), labels=(("0 xG", 1), ("1 xG", 8.15)))

def flip_boost_label(label, big):
    if big:
        return 350 - label
    else:
        return 35 - label

def get_goal_desc(game, goal):
    if goal.seconds_remaining < 0:
        secs = -1 * goal.seconds_remaining
        goal_time = f"+{abs(secs // 60)}:{secs % 60:02d}"
    else:
        goal_time = f"{abs(goal.seconds_remaining // 60)}:{goal.seconds_remaining % 60:02d}"
    score_text = f" {goal.blue_score} - [{goal.orange_score + 1}]" if goal.is_orange else f"[{goal.blue_score + 1}] - {goal.orange_score} "
    blue_team = [team for team in game.teams if not team.is_orange][0]
    orange_team = [team for team in game.teams if team.is_orange][0]
    blue_name = "Blue" if blue_team.name == "" else utils.get_team_label(blue_team.name)
    orange_name = "Orange" if orange_team.name == "" else utils.get_team_label(orange_team.name)
    scorer_name = utils.get_player_label(goal.scorer)
    if "Swiss" in game.game_metadata.tag:
        stage = "Swiss"
    else:
        stage = "Playoffs"
    return f"{blue_name} {score_text} {orange_name}", f"{scorer_name} - {goal_time}", stage
    #return f"Extra {score_text} Gen.G Black", f"{scorer_name} - {goal_time}"

def get_team_data(data_path, config):
    player_map = {}
    series_data = {}
    player_data = {"against": {"score": 0, "goals": 0, "assists": 0, "saves": 0, "shots": 0, "xG": 0, "demos": 0}}
    shot_data = {"for": [], "against": []}
    goal_data = {}
    touch_data = {}
    pickups = {}
    locations = {}
    demo_data = {}
    pos_data = {}

    max_speed, max_supersonic, max_demos = 0, 0, 0
    
    game_list = utils.read_group_data(data_path)
    for game in game_list:
        t0, t1 = utils.get_team_label(game.teams[0].name, config["region"]), utils.get_team_label(game.teams[1].name, config["region"])
        
        if config["tn"] not in [t0, t1]:
           continue
        if t0 == config["tn"]:
            for_team, against_team = game.teams[0], game.teams[1]
            for_name, against_name = t0, t1
        else:
            for_team, against_team = game.teams[1], game.teams[0]
            for_name, against_name = t1, t0

        # for_color = [pl.is_orange for pl in game.players if pl.name == "bella"][0]
        # if game.teams[0].is_orange == for_color:
        #     for_team, against_team = game.teams[0], game.teams[1]
            
        # else:
        #     for_team, against_team = game.teams[1], game.teams[0]

        #print(game.game_metadata.tag)
        series_info = game.game_metadata.tag.split("Day")[1]
        if "Swiss" in series_info:
            round_num = series_info.split("/")[1]
            series_key = ("Swiss", round_num, against_name)
        else:
            if ("[" in game.game_metadata.tag and " 3" in series_info) or ("[" not in game.game_metadata.tag and " 4" in series_info):
                stage = "Quarterfinal"
            else:
                stage = "Grand Final" if config["final_team"] in series_info else "Semifinal"
            series_key = ("Playoffs", stage, against_name)

        if series_key not in series_data:
                series_data[series_key] = [0, 0]
        if for_team.score > against_team.score and game.game_metadata.last_second <= 1:
            series_data[series_key][0] += 1
        elif for_team.score < against_team.score and game.game_metadata.last_second <= 1:
            series_data[series_key][1] += 1
        else:
            pass
        
        for player in game.players:
            if player.is_orange == for_team.is_orange:
                pn = utils.get_player_label(player.name)
                player_map[player.id.id] = (pn, player.is_orange)
                if pn not in goal_data:
                    goal_data[pn] = []
                    pickups[pn] = {}
                    demo_data[pn] = []
                    touch_data[pn] = [0, 0, 0]
                    pos_data[pn] = [0, 0, 0]
                    player_data[pn] = {"score": 0, "goals": 0, "assists": 0, "saves": 0, "shots": 0, "xG": 0, "demos": 0}

                player_data[pn]["score"] += player.score
                player_data[pn]["goals"] += player.goals
                player_data[pn]["assists"] += player.assists
                player_data[pn]["saves"] += player.saves
                
                
                touch_data[pn][0] += player.stats.hit_counts.self_next
                touch_data[pn][1] += player.stats.hit_counts.team_next
                touch_data[pn][2] += player.stats.hit_counts.oppo_next
                if game.game_metadata.length <= 0:
                    print(game.game_metadata.tag)

                if game.game_metadata.length > 0 and (player.stats.speed.time_at_super_sonic / game.game_metadata.length) > max_supersonic:
                    max_supersonic = player.stats.speed.time_at_super_sonic / game.game_metadata.length
                    supersonic_player = pn
                    blue_team = [team for team in game.teams if not team.is_orange][0]
                    orange_team = [team for team in game.teams if team.is_orange][0]
                    supersonic_teams = (utils.get_team_label(blue_team.name), utils.get_team_label(orange_team.name))
                    if "Swiss" in game.game_metadata.tag:
                        supersonic_stage = "Swiss"
                    else:
                        supersonic_stage = "Playoffs"
                    supersonic_game = game.game_metadata.tag.split("/")[-1]
                    #supersonic_game = (game.game_metadata.tag, game.game_metadata.name)
                    #print("supersonic", game.game_metadata.tag, game.game_metadata.name)

                pos_data[pn][0] += player.stats.relative_positioning.time_most_back_player
                pos_data[pn][1] += player.stats.relative_positioning.time_between_players
                pos_data[pn][2] += player.stats.relative_positioning.time_most_forward_player
            else:
                player_data["against"]["score"] += player.score
                player_data["against"]["goals"] += player.goals
                player_data["against"]["assists"] += player.assists
                player_data["against"]["saves"] += player.saves
                
        
        for shot in game.game_metadata.shot_details:
            if shot.is_orange == for_team.is_orange:
                shot_key = "for"
                player_key = utils.get_player_label(shot.shooter_name)
                ball_x = -1 * shot.ball_pos.pos_x if for_team.is_orange else shot.ball_pos.pos_x
                ball_y = -1 * shot.ball_pos.pos_y if for_team.is_orange else shot.ball_pos.pos_y
            else:
                shot_key = "against"
                player_key = "against"
                ball_x = -1 * shot.ball_pos.pos_x if not against_team.is_orange else shot.ball_pos.pos_x
                ball_y = -1 * shot.ball_pos.pos_y if not against_team.is_orange else shot.ball_pos.pos_y

            xG_val = utils.get_xG_val(game, shot)
            size = (xG_val * (3 * MARKER_SIZE)) + MARKER_SIZE
            shot_data[shot_key].append([(ball_x, ball_y), size, shot.is_goal])
            player_data[player_key]["shots"] += 1
            player_data[player_key]["xG"] += xG_val

        for goal in game.game_metadata.goals:
            scorer = utils.get_player_label(goal.scorer)
            if scorer in goal_data:
                goal_data[scorer].append((goal.ball_pos, goal.seconds_remaining < 0))

                goal_speed = np.sqrt((goal.ball_vel.pos_x ** 2) + (goal.ball_vel.pos_y ** 2) + (goal.ball_vel.pos_z ** 2)) * (100/2778) #* (1/1.609344)
                if goal_speed > max_speed:
                    max_speed = goal_speed
                    speed_desc = get_goal_desc(game, goal)
                    speed_game = game.game_metadata.tag.split("/")[-1]
                    #speed_game = (game.game_metadata.tag, game.game_metadata.name)
                    #print("goal", game.game_metadata.tag, game.game_metadata.name)

                # if goal.assister != "":
                #     pair = (utils.get_player_label(goal.assister), scorer)
                #     if pair not in combo_data:
                #         combo_data[pair] = 0
                #     combo_data[pair] += 1

        player_demos = {}
        for demo in game.game_metadata.demos:
            an = utils.get_player_label(demo.attacker_name)
            if not demo.is_valid:
                continue

            if an in goal_data:
                if an not in player_demos: 
                    player_demos[an] = 0
                player_demos[an] += 1
                player_data[an]["demos"] += 1

                attacker = [pl for pl in game.players if pl.name == demo.attacker_name][0]
                flip = -1 if attacker.is_orange else 1
                demo_loc = [demo.location.pos_y * flip, demo.location.pos_x * flip]
                next_goal = [goal for goal in game.game_metadata.goals if goal.is_orange == attacker.is_orange and goal.frame_number > demo.frame_number]
                if len(next_goal) > 0 and demo.frame_number > (next_goal[0].frame_number - (30 * 5)):
                    demo_data[an].append((demo_loc, demo.is_behind_ball, True))
                else:
                    demo_data[an].append((demo_loc, demo.is_behind_ball, False))
            else:
                player_data["against"]["demos"] += 1
        for pl in player_demos:
            if player_demos[pl] > max_demos:
                max_demos = player_demos[pl]
                demo_player = pl
                blue_team = [team for team in game.teams if not team.is_orange][0]
                orange_team = [team for team in game.teams if team.is_orange][0]
                demo_teams = (utils.get_team_label(blue_team.name), utils.get_team_label(orange_team.name))
                demo_game = game.game_metadata.tag.split("/")[-1]
                if "Swiss" in game.game_metadata.tag:
                    demo_stage = "Swiss"
                else:
                    demo_stage = "Playoffs"
                #demo_game = (game.game_metadata.tag, game.game_metadata.name)
                #print("demo", game.game_metadata.tag, game.game_metadata.name)

        for pad in game.game_stats.boost_pads:
            if pad.label not in locations:
                locations[pad.label] = {
                    "pos_x": pad.pos_x,
                    "pos_y": pad.pos_y,
                    "big": pad.big
                }
            for pickup in pad.pickups:
                if pickup.player_id.id in player_map:
                    pn, is_orange = player_map[pickup.player_id.id]
                    pad_label = pad.label if not is_orange else flip_boost_label(pad.label, pad.big)
                    
                    if pad_label not in pickups[pn]:
                        pickups[pn][pad_label] = 0
                    pickups[pn][pad_label] += 1

    speed_text = f"{round(max_speed, 2)} kph\n{speed_desc[0]}\n{speed_desc[1]} | {speed_game} | {speed_desc[2]}"
    supersonic_text = f"{round(100 * max_supersonic, 1)}%\n{supersonic_player}\n{supersonic_teams[0]} - {supersonic_teams[1]} | {supersonic_game} | {supersonic_stage}"
    demo_text = f"{max_demos}\n{demo_player}\n{demo_teams[0]} - {demo_teams[1]} | {demo_game} | {demo_stage}"
    # speed_text = f"{round(max_speed, 2)} mph\n{speed_desc[0]}\n{speed_desc[1]} | G4"
    # supersonic_text = f"{round(100 * max_supersonic, 1)}%\n{supersonic_player}\nPulse - Gen.G Black | G1"
    # demo_text = f"{max_demos}\n{demo_player}\n 12 Bricks - Gen.G Black | G1"
    text_data = (speed_text, supersonic_text, demo_text)
    return series_data, player_data, shot_data, goal_data, text_data, touch_data, demo_data, pos_data

def draw_goal_marker(draw, pos, mark_type, img_height, size=MARKER_SIZE, outline=None, fill=None, width=2):
    MID_X = (constants.GOAL_X + (MARGIN * 4)) / 2
    base_x = MID_X + pos.pos_x
    base_y = pos.pos_z
    if mark_type == "C":
        draw.ellipse([(base_x - size, get_y(base_y + size, img_height)), (base_x + size, get_y(base_y - size, img_height))], 
            outline=outline, fill=fill, width=width)
    elif mark_type == "S":
        draw.regular_polygon((base_x, get_y(base_y, img_height), size), 4, 
            outline=outline, fill=fill, width=width, rotation=45)
    else:
        draw.regular_polygon((base_x, get_y(base_y, img_height), size + 5), 3, 
            outline=outline, fill=fill, width=width, rotation=60)

def draw_player_layers(img: Image.Image, draw: ImageDraw.ImageDraw, config, goal_data, touch_data, demo_data, pos_data):
    MID_X, MID_Y = (constants.MAP_Y + (MARGIN * 4)) / 2, (constants.MAP_X + (MARGIN * 2)) / 2
    
    sec_top = HEADER_HEIGHT + LAYER_1_HEIGHT + LAYER_2_HEIGHT
    names = sorted(goal_data.keys(), key=str.casefold)
    for name in names:
        if name == "fasi":
            continue
        draw.text((img.width / 2, sec_top), name, fill=BLACK, font=constants.BOUR_100, anchor="ma")

        # Goal placements
        goal_width, goal_height = constants.GOAL_X + (MARGIN * 4), round(constants.GOAL_Z - 80) + (MARGIN * 2)
        goal_img = Image.new(mode="RGBA", size = (goal_width, goal_height), color=WHITE)
        
        goal_draw = ImageDraw.Draw(goal_img)
        utils.draw_goal_lines(goal_draw, MARGIN, goal_height)
        num_ot = 0
        for goal in goal_data[name]:
            if goal[1]:
                mark = "S"
                color = config["c2"]
                size = MARKER_SIZE + 10
                num_ot += 1
            else:
                mark = "C"
                color = config["c1"]
                size = MARKER_SIZE
            draw_goal_marker(goal_draw, goal[0], mark, goal_height, size=size, fill=color)
        goal_draw.text((goal_img.width / 2, 8), f"{len(goal_data[name])} total | {num_ot} in OT", 
            fill=DARK_GREY, font=constants.BOUR_60, anchor="ma")
        img.paste(goal_img, (2 * MARGIN, sec_top + 200))
        draw.text(((2 * MARGIN) + (goal_img.width / 2), sec_top + 110), "Goal Placements", fill=BLACK, font=constants.BOUR_80, anchor="ma")

        # Boost pickup map
        # boost_width, boost_height = round(constants.MAP_Y) + (MARGIN * 4), round(constants.MAP_X) + (MARGIN * 2)
        # boost_img = Image.new(mode="RGBA", size = (boost_width, boost_height), color=WHITE)
        # boost_draw = ImageDraw.Draw(boost_img)
        # utils.draw_field_lines(boost_draw, MARGIN, boost_height)
        # pickup_map, locations = boost_data
        # num_small, num_big = 0, 0
        # max_pickups = max(pickup_map[name].values())
        # for label in locations.keys():
        #     loc = locations[label]
        #     loc_x, loc_y = MID_X + loc['pos_y'] / constants.SCALE, MID_Y + loc['pos_x'] / constants.SCALE
        #     radius = 35 if loc['big'] else 20
        #     lower = 40 if loc['big'] else 25
        #     if loc['big']:
        #         if label in pickup_map[name]:
        #             num_big += pickup_map[name][label]
        #         else:
        #             pickup_map[name][label] = 0
                    
        #     else:
        #         if label in pickup_map[name]:
        #             num_small += pickup_map[name][label]
        #         else:
        #             pickup_map[name][label] = 0
            
        #     color_str = constants.REGION_COLORS[config["region"]][2].format(100 - (50 * (pickup_map[name][label] / max_pickups)))

        #     boost_draw.ellipse([
        #         (loc_x - radius, get_y(loc_y + radius, boost_height)), (loc_x + radius, get_y(loc_y - radius, boost_height))
        #     ], fill=color_str, outline=DARK_GREY, width=2)
        #     boost_draw.text((loc_x, get_y(loc_y - lower, boost_height)), str(pickup_map[name][label]), fill=BLACK, font=constants.BOUR_50, anchor="ma")

        # boost_left = img.width - boost_img.width - (2 * MARGIN)
        # img.paste(boost_img, (boost_left, sec_top + 230))
        # draw.text((boost_left + (boost_img.width / 2), sec_top + 110), "Boost Pickups", fill=BLACK, font=constants.BOUR_80, anchor="ma")
        # att_len = draw.textlength("Attacking Direction", font=constants.BOUR_60)
        # draw.text((boost_left + (boost_img.width / 2) - (att_len / 2), sec_top + 200), "Attacking Direction >>", 
        #     fill=DARK_GREY, font=constants.BOUR_60)
        # draw.text((boost_left + (boost_img.width / 2), sec_top + 230 + boost_img.height - 20), 
        #     f"{num_big} big pads | {num_small} small pads", fill=DARK_GREY, font=constants.BOUR_60, anchor="ma")

        demo_width, demo_height = round(constants.MAP_Y) + (MARGIN * 4), round(constants.MAP_X) + (MARGIN * 2)
        demo_img = Image.new(mode="RGBA", size = (demo_width, demo_height), color=WHITE)
        demo_draw = ImageDraw.Draw(demo_img)
        utils.draw_field_lines(demo_draw, MARGIN, demo_height)
        
        num_behind, num_ahead, num_precede = 0, 0, 0
        for demo in demo_data[name]:
            radius = 25 if demo[2] else 15
            line = constants.REGION_COLORS[config["region"]][0] if demo[2] else DARK_GREY
            line_width = 5 if demo[2] else 3
            loc_x, loc_y = MID_X + demo[0][0] / constants.SCALE, MID_Y + demo[0][1] / constants.SCALE
            if demo[1]:
                num_behind += 1
                demo_fill = config["c1"]
            else:
                num_ahead += 1
                demo_fill = config["c2"]
            if demo[2]:
                num_precede += 1


            demo_draw.ellipse([
                (loc_x - radius, get_y(loc_y + radius, demo_height)), (loc_x + radius, get_y(loc_y - radius, demo_height))
            ], fill=demo_fill, outline=line, width=3)

        boost_left = img.width - demo_img.width - (2 * MARGIN)
        img.paste(demo_img, (boost_left, sec_top + 230))
        draw.text((boost_left + (demo_img.width / 2), sec_top + 110), "Demo Locations", fill=BLACK, font=constants.BOUR_80, anchor="ma")
        att_len = draw.textlength("Attacking Direction", font=constants.BOUR_60)
        draw.text((boost_left + (demo_img.width / 2) - (att_len / 2), sec_top + 200), "Attacking Direction >>", 
            fill=DARK_GREY, font=constants.BOUR_60)
        draw.text((boost_left + (demo_img.width / 2), sec_top + 230 + demo_img.height - 20), 
            f"{num_behind} behind ball | {num_ahead} ahead of ball | {num_precede} goal-preceding", fill=DARK_GREY, font=constants.BOUR_60, anchor="ma")

        # Touch results
        touch_center, touch_top = (img.width / 6) - 200, sec_top + goal_img.height + 250
        draw.text((touch_center, touch_top), "Touch Results", fill=BLACK, font=constants.BOUR_80, anchor="ma")
        pie_colors = [(50,250,50), (50,50,250), (250,50,50)]
        total = sum(touch_data[name])
        curr_ang = -90
        x_orig, y_orig, radius = touch_center, touch_top + 350, 200
        bbox = [(x_orig - radius, y_orig - radius), (x_orig + radius, y_orig + radius)]
        for j in range(len(touch_data[name])):
            # Pie slice
            pl_val = touch_data[name][j]
            frac = pl_val / total
            deg = (frac * 360)
            draw.pieslice(bbox, curr_ang, curr_ang + deg, fill=pie_colors[j])

            # Slice label
            rad = ((curr_ang + deg + curr_ang) / 2 / 360) * 2 * np.pi 
            if -(np.pi / 2) < rad and rad <= 0:
                x_pad, y_pad = 5, -5
                anc = "ld"
            elif 0 < rad and rad <= (np.pi / 2):
                x_pad, y_pad = 5, 5
                anc = "la"
            elif (np.pi / 2) < rad and rad < np.pi:
                x_pad, y_pad = -5, 5
                anc = "ra"
            else:
                x_pad, y_pad = -5, -5
                anc = "rd"
            point = (x_orig + (radius * np.cos(rad)) + x_pad, y_orig + (radius * np.sin(rad)) + y_pad)
            cat_pct = round(frac * 100, 1)
            if j == 0:
                pie_label = f"{cat_pct}% to Self"
            elif j == 1:
                pie_label = f"{cat_pct}% to Team"
            else:
                pie_label = f"{cat_pct}%\nto Opp."
            draw.text(point, pie_label, fill=DARK_GREY, font=constants.BOUR_60, anchor=anc)
            draw.text((touch_center, y_orig + radius + 30), f"{total} touches", fill=DARK_GREY, font=constants.BOUR_70, anchor="ma")

            curr_ang += deg
        
        # Pos data
        pos_center, pos_top =  (img.width / 2) - 450, touch_top
        draw.text((pos_center, pos_top), "Positioning", fill=BLACK, font=constants.BOUR_80, anchor="ma")
        pie_colors = [(50,250,50), (50,50,250), (250,50,50)]
        total = sum(pos_data[name])
        curr_ang = -90
        x_orig, y_orig, radius = pos_center, pos_top + 350, 200
        bbox = [(x_orig - radius, y_orig - radius), (x_orig + radius, y_orig + radius)]
        for j in range(len(pos_data[name])):
            # Pie slice
            pl_val = pos_data[name][j]
            frac = pl_val / total
            deg = (frac * 360)
            draw.pieslice(bbox, curr_ang, curr_ang + deg, fill=pie_colors[j])

            # Slice label
            rad = ((curr_ang + deg + curr_ang) / 2 / 360) * 2 * np.pi 
            if -(np.pi / 2) < rad and rad <= 0:
                x_pad, y_pad = 5, -5
                anc = "ld"
            elif 0 < rad and rad <= (np.pi / 2):
                x_pad, y_pad = 5, 5
                anc = "la"
            elif (np.pi / 2) < rad and rad < np.pi:
                x_pad, y_pad = -5, 5
                anc = "ra"
            else:
                x_pad, y_pad = -5, -5
                anc = "rd"
            point = (x_orig + (radius * np.cos(rad)) + x_pad, y_orig + (radius * np.sin(rad)) + y_pad)
            cat_pct = round(frac * 100, 1)
            if j == 0:
                pie_label = f"{cat_pct}% Most\nBack"
            elif j == 1:
                pie_label = f"{cat_pct}%\nMiddle"
            else:
                pie_label = f"{cat_pct}% Most\nForward"
            draw.multiline_text(point, pie_label, fill=DARK_GREY, font=constants.BOUR_60, anchor=anc, align="center")

            curr_ang += deg

        sec_top += PL_LAYER_HEIGHT

def create_image(config, team_name, data_path):
    img_width = (2 * round(constants.MAP_X)) + 1200 + (MARGIN * 4)
    img_height = HEADER_HEIGHT + LAYER_1_HEIGHT + LAYER_2_HEIGHT + (3 * PL_LAYER_HEIGHT) + (2 * MARGIN)
    img = Image.new(mode = "RGBA", size = (img_width, img_height), color = WHITE)
    draw = ImageDraw.Draw(img)
    
    series_data, player_data, shot_data, goal_data, text_data, touch_data, demo_data, pos_data = get_team_data(data_path, config)
    if len(config["series_data"]) > 0:
        series_data = config["series_data"]

    draw_header(img, draw, config)
    draw_layer_1(img, draw, series_data, player_data, config)
    draw_layer_2(img, draw, config, shot_data, text_data)
    draw_player_layers(img, draw, config, goal_data, touch_data, demo_data, pos_data)
    
    os.makedirs(config['img_path'], exist_ok=True)
    img.save(os.path.join(config["img_path"], "{}_summary.png".format(team_name.replace(".", "_"))))

def main():
    key, team_name = "NINJAS IN PYJAMAS", "NIP"
    region = "South America"
    rn = utils.get_region_label(region)
    base_path = os.path.join("RLCS 24", "Major 2", region, "Open Qualifier 5")
    data_path = os.path.join("replays", base_path)
    series_data = {
        # ("Group A", "Round 1", "Pulse"): [4, 0],
        # ("Group A", "Round 2", "Extra"): [4, 0],
        # ("Group A", "Round 3", "12 Bricks"): [4, 0]
    }

    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": key,
        "t2": "AZTRØ | NXGHTT | SWIFTT | C: FASI",
        "t3": f"RLCS 24 {rn} | MAJOR 2 | OQ 5 SUMMARY",
        "key": key,
        "tn": team_name,
        "final_team": "FUR",
        "series_data": series_data,
        "region": rn,
        "c1": constants.TEAM_INFO[key]["c1"],
        "c2": constants.TEAM_INFO[key]["c2"],
        "img_path": os.path.join("viz", "images", base_path)
    }
    create_image(config, key, data_path)
    
    return 0
  
if __name__ == "__main__":
    main()