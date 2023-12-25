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

def calculate_touch_groups(game_list, team_names):
    id_map = {}
    hit_times = {}
    labels = []
    goals = []
    saves = []
    for idx in range(len(game_list)):
        game = game_list[idx]

        blue_team = [team for team in game.teams if not team.is_orange][0]
        orange_team = [team for team in game.teams if team.is_orange][0]
        labels.append(f"Game {idx + 1} | {team_names[0]} {blue_team.score} - {orange_team.score} {team_names[1]}")

        for player in game.players:
            id_map[player.id.id] = player.is_orange

        goal_list = [(goal.is_orange, goal.seconds_remaining) for goal in game.game_metadata.goals]
        goals.append(goal_list)

        save_list = [(id_map[hit.player_id.id], hit.seconds_remaining) for hit in game.game_stats.hits if hit.match_save]
        saves.append(save_list)

        hit_times[idx] = {}
        for hit in game.game_stats.hits:
            secs = hit.seconds_remaining
            sec_grp = secs if (secs % 10) == 0 else secs + (10 - (secs % 10))
            is_orange = id_map[hit.player_id.id]
            if sec_grp not in hit_times[idx]:
                hit_times[idx][sec_grp] = { 'diff': 0}
                for val in id_map.values():
                    hit_times[idx][sec_grp][val] = 0
            hit_times[idx][sec_grp][is_orange] += 1

            diff = -1 if is_orange else 1
            hit_times[idx][sec_grp]['diff'] += diff

    return hit_times, labels, goals, saves

def draw_timelines(game_list, team_names):
    hit_data, labels, goals, saves = calculate_touch_groups(game_list, team_names)
    num_games = len(hit_data)
    max_game_len = max([len(game_data.keys()) for game_data in hit_data.values()])
    max_diff = max([max([abs(group['diff']) for group in game_data.values()]) for game_data in hit_data.values()])

    bar_width, bar_height = 80, 15
    middle_height = 110
    chart_height = ((2 * max_diff) * bar_height) + middle_height + 80
    width, height = (max_game_len * bar_width) + (MARGIN * 2), (num_games * chart_height) + (MARGIN * (num_games + 1))
    img = Image.new(mode="RGBA", size = (width, height), color=WHITE)
    draw = ImageDraw.Draw(img)

    BLUE = constants.TEAM_INFO["RL ESPORTS"]["c1"]
    ORANGE = constants.TEAM_INFO["RL ESPORTS"]["c2"]
    for idx in range(num_games):
        data = hit_data[idx]
        base_y = (idx * (chart_height + MARGIN)) + (chart_height / 2) + MARGIN
        keys = list(data.keys())

        # Per chart elements
        # Game label
        game_num_text = labels[idx].split(' | ')[0]
        lbl_len = draw.textlength(labels[idx], font=constants.BOUR_50)
        lbl_one_len = draw.textlength(game_num_text + " | ", font=constants.BOUR_50)
        name_two_len = draw.textlength(team_names[1], font=constants.BOUR_50)
        draw.text((MARGIN, base_y - (chart_height / 2) - 40), labels[idx], fill=DARK_GREY, font=constants.BOUR_50)
        draw.text((MARGIN + lbl_one_len, base_y - (chart_height / 2) - 40), team_names[0], fill=BLUE, font=constants.BOUR_50)
        draw.text((MARGIN + lbl_len - name_two_len, base_y - (chart_height / 2) - 40), team_names[1], fill=ORANGE, font=constants.BOUR_50)
        
        # Middle timeline line
        draw.line([(MARGIN, base_y - 1), ((bar_width * min(len(keys), 30)) + MARGIN, base_y - 1)], fill=DARK_GREY, width=2)
        if len(keys) > 30:
            draw.line([((bar_width * 31) + MARGIN, base_y - 1), ((bar_width * len(keys)) + MARGIN, base_y - 1)], fill=DARK_GREY, width=2)
        
        # Per group elements 
        for i in range(len(keys)):
            group = data[keys[i]]
            bar_start = (bar_width * i) + MARGIN

            # Middle timeline ticks
            tick_height = 20 if (i % 6 == 0) or (i == 31) else 10
            tick_width = 3 if (i % 6 == 0) or (i == 31) else 2
            draw.line([(bar_start, base_y - tick_height), (bar_start, base_y + tick_height)], 
                fill=BLACK, width=tick_width)
            if keys[i] == 10 and i == (len(keys) - 1):
                draw.line([(bar_start + bar_width, base_y - 20), (bar_start + bar_width, base_y + 20)], 
                    fill=BLACK, width=3)

            # Timeline bars and hit counts
            blue_len = draw.textlength(str(group[False]), font=constants.BOUR_30) / 2
            orange_len = draw.textlength(str(group[True]), font=constants.BOUR_30) / 2
            blue_coords = (bar_start + (bar_width / 2) - blue_len, base_y - (middle_height / 2) - 30)
            orange_coords = (bar_start + (bar_width / 2) - orange_len, base_y + (middle_height / 2))
            if group['diff'] > 0:
                bar_coords = [
                    (bar_start + 2, blue_coords[1] - (group['diff'] * bar_height)),
                    ((bar_width * (i + 1)) - 2 + MARGIN, blue_coords[1])
                ]
                fill = BLUE
            else:
                bar_coords = [
                    (bar_start + 2, orange_coords[1] + 30),
                    ((bar_width * (i + 1)) - 2 + MARGIN, orange_coords[1] - (group['diff'] * bar_height) + 30)
                ]
                fill = ORANGE

            draw.text(blue_coords, str(group[False]), 
                fill=BLUE, font=constants.BOUR_30)
            draw.text(orange_coords, str(group[True]), 
                fill=ORANGE, font=constants.BOUR_30)

            if group['diff'] == 0:
                continue
            draw.rectangle(bar_coords, fill=fill)

        # Goal circles on middle timeline
        game_goals = goals[idx]
        for goal in game_goals:
            goal_color = ORANGE if goal[0] else BLUE
            pos_y = base_y + 35 if goal[0] else base_y - 35
            pos_x = (300 - goal[1]) * (bar_width / 10)
            # with Image.open(os.path.join("viz", "images", "logos", "goal_3.png")) as logo:
            #     divisor = logo.width / 30
            #     logo_width, logo_height = round(logo.width / divisor), round(logo.height / divisor)
            #     logo_small = logo.resize((logo_width, logo_height))
            #     color_img = Image.new(mode="RGBA", size=(logo_width, logo_height), color=goal_color)
            #     img.paste(color_img, (int(pos_x), int(pos_y)), mask = logo_small)
            draw.ellipse([
                (MARGIN + pos_x - 10, pos_y - 10), 
                (MARGIN + pos_x + 10, pos_y + 10)], 
            fill=goal_color, outline=BLACK, width=1)

        # game_saves = saves[idx]
        # for save in game_saves:
        #     save_color = ORANGE if save[0] else BLUE
        #     pos_y = base_y + 25 if save[0] else base_y - 50
        #     pos_x = (300 - save[1]) * (bar_width / 10)
        #     with Image.open(os.path.join("viz", "images", "logos", "save_3.png")) as logo:
        #         divisor = logo.width / 30
        #         logo_width, logo_height = round(logo.width / divisor), round(logo.height / divisor)
        #         logo_small = logo.resize((logo_width, logo_height))
        #         color_img = Image.new(mode="RGBA", size=(logo_width, logo_height), color=save_color)
        #         img.paste(color_img, (int(pos_x), int(pos_y)), mask = logo_small)
            # draw.ellipse([
            #     (MARGIN + pos_x - 10, pos_y - 10), 
            #     (MARGIN + pos_x + 10, pos_y + 10)], 
            # fill=save_color, outline=save_outline, width=1)
            # ×

    return img

def create_image(team_names, game_list, config):
    timeline_img = draw_timelines(game_list, team_names)
    
    IMAGE_X, IMAGE_Y = timeline_img.width + (2 * MARGIN), timeline_img.height + 400
    img = Image.new(mode = "RGBA", size = (IMAGE_X, IMAGE_Y), color = WHITE)
    draw = ImageDraw.Draw(img)
    
    # Logo in top left
    logo_width, _ = utils.draw_team_logo(img, MARGIN, config["logo"])

    # Title text
    utils.draw_title_text(draw, logo_width, MARGIN, config, constants.BOUR_80, constants.BOUR_40)

    # Timelines
    img.paste(timeline_img, (MARGIN, get_y(timeline_img.height + MARGIN, IMAGE_Y)))

    # Dotted circle logo
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    
    img.save(os.path.join("viz", "images", config["img_name"]))

def main():
    team_names = ("HEY BRO", "SHOPIFY REBELLION")
    key = "OXG HOLIDAY INV"
    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": f"{team_names[0]} 3 - 1 {team_names[1]}",
        "t2": "OXG HOLIDAY INVITATIONAL | UPPER BRACKET QUARTERFINAL",
        "t3": "TOUCH TIMELINES",
        "c1": constants.TEAM_INFO[key]["c1"],
        "c2": constants.TEAM_INFO[key]["c2"],
        "img_name": os.path.join("OXG Holiday Inv", "touches", f"{team_names[0].lower()}_{team_names[1].lower()}_touch_timeline.png")
    }

    data_path = os.path.join("replays", "OXG Inv", "R2 - HB vs SR")
    game_list = utils.read_series_data(data_path)
    create_image(team_names, game_list, config)
    
    return 1
  
if __name__ == "__main__":
    main()