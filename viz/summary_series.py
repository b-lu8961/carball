from viz import constants, utils

import os
from PIL import Image, ImageDraw

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
    gp, shots, goals, xG, saves, demos, boost = 0, 0, 0, 0, 0, 0, 0
    
    for game in game_list:
        active_teams = [team.name for team in game.teams]
        #print(active_teams)
        if team_name not in active_teams:
          return 1    
        
        if team is None:
            team = [team for team in game.teams if team.name == team_name][0]
            color_set = constants.ORANGE_COLORS if team.is_orange else constants.BLUE_COLORS
        gp += 1
        for player in game.players:
            if player.is_orange == team.is_orange:
                saves += player.saves
                boost += player.stats.boost.boost_usage

        for demo in game.game_metadata.demos:
            if not demo.is_valid:
                continue
            
            attacker = [player for player in game.players if player.id.id == demo.attacker_id.id][0]
            if attacker.is_orange == team.is_orange:
                demos += 1

        for shot in game.game_metadata.shot_details:
            corr_hit = [hit for hit in game.game_stats.hits if hit.frame_number == shot.frame_number][0]
            corr_player = [player for player in game.players if player.id.id == corr_hit.player_id.id][0]
            if corr_player.is_orange != team.is_orange:
                continue
                
            shots += 1
            xG_val = utils.get_xG_val(game, shot)
            size = (xG_val * (3 * MARKER_SIZE)) + MARKER_SIZE
            xG += xG_val
            if shot.is_goal:
                goals += 1
                draw_marker(draw, shot.ball_pos, "C", height, size, fill=color_set[0], outline=color_set[1], width=3)
            else:
                draw_marker(draw, shot.ball_pos, "C", height, size, outline=color_set[2], width=4)
    
    return img, (goals, xG, shots, saves, demos, int(boost)), color_set

def create_image(team_one, team_two, team_keys, wins, game_list, config):
    img_width, img_height = (2 * round(constants.MAP_X)) + 1200 + (MARGIN * 4), round(constants.MAP_Y) + 500 + (MARGIN * 2)
    img = Image.new(mode = "RGBA", size = (img_width, img_height), color = WHITE)
    draw = ImageDraw.Draw(img)
    
    # Logo in top left
    logo_width, _ = utils.draw_team_logo(img, MARGIN, file_name=config["logo"])

    # Title text
    utils.draw_title_text(draw, logo_width, MARGIN, config, constants.BOUR_80, constants.BOUR_40)

    # Main field images
    blue_img, blue_counts, blue_colors = draw_field(team_one, game_list)
    blue_rot = blue_img.rotate(90, expand=True)
    blue_left = int(1.5 * MARGIN)
    field_top = get_y(blue_img.width + MARGIN, img_height)
    img.paste(blue_rot, (blue_left, field_top))

    orange_img, orange_counts, orange_colors = draw_field(team_two, game_list)
    orange_rot = orange_img.rotate(90, expand=True)
    orange_left = img_width - orange_img.height - int(1.5 * MARGIN)
    img.paste(orange_rot, (orange_left, field_top))

    # Team info
    draw.text((blue_left + (blue_img.height / 2), field_top), team_keys[0], 
            fill=constants.TEAM_INFO["RL ESPORTS"]["c1"], font=constants.BOUR_100, anchor="md")
    t1_pos = (int(img_width / 2) - 475, field_top - 175)
    t1t_pos = (int(img_width / 2) - 120, field_top - 125)
    _, _ = utils.draw_team_logo(img, MARGIN, file_name=constants.TEAM_INFO[team_keys[0]]["logo"], pos=(t1_pos[0], t1_pos[1] - 20))
    draw.text(t1t_pos, str(wins[0]), font=constants.BOUR_100, fill=constants.TEAM_INFO[team_keys[0]]["c2"], anchor="ma")
    draw.rounded_rectangle([
        (t1_pos[0] + 375 - 80, t1_pos[1] + 50 - 10), (t1_pos[0] + 375 + 35, t1_pos[1] + 50 + 115)
    ], 20, outline=constants.TEAM_INFO[team_keys[0]]["c1"], width=5)

    draw.text((orange_left + (blue_img.height / 2), field_top), team_keys[1], 
            fill=constants.TEAM_INFO["RL ESPORTS"]["c2"], font=constants.BOUR_100, anchor="md")
    t2_pos = (int(img_width / 2) + 275, field_top - 175)
    t2t_pos = (int(img_width / 2) + 123, field_top - 125)
    _, _ = utils.draw_team_logo(img, MARGIN, file_name=constants.TEAM_INFO[team_keys[1]]["logo"], pos=(t2_pos[0], t2_pos[1]))
    draw.text(t2t_pos, str(wins[1]), font=constants.BOUR_100, fill=constants.TEAM_INFO[team_keys[1]]["c1"], anchor="ma")
    draw.rounded_rectangle([
        (t2_pos[0] - 175 - 35, t2_pos[1] + 50 - 10), (t2_pos[0] - 175 + 80, t2_pos[1] + 50 + 115)
    ], 20, outline=constants.TEAM_INFO[team_keys[1]]["c2"], width=5)
    
    # Summary metrics
    img_mid = img_width / 2
    blue_x, orange_x = img_mid - 375, img_mid + 375
    y_pad = [275, 500, 725, 950, 1175, 1400]
    labels = ["Goals", "xG", "Shots", "Saves", "Demos", "Boost Usage"]
    for i in range(len(labels)):
        if i == 0:
            draw.ellipse([
                (blue_x - 60, field_top + y_pad[i] - 30), (blue_x + 60, field_top + y_pad[i] + 90)
            ], fill=blue_colors[0], outline=blue_colors[1], width=3)
            draw.ellipse([
                (orange_x - 60, field_top + y_pad[i] - 30), (orange_x + 60, field_top + y_pad[i] + 90)
            ], fill=orange_colors[0], outline=orange_colors[1], width=3)
        if i == 2:
            draw.ellipse([
                (blue_x - 60, field_top + y_pad[i] - 30), (blue_x + 60, field_top + y_pad[i] + 90)
            ], outline=blue_colors[2], width=4)
            draw.ellipse([
                (orange_x - 60, field_top + y_pad[i] - 30), (orange_x + 60, field_top + y_pad[i] + 90)
            ], outline=orange_colors[2], width=4)

        split = int(550 * (blue_counts[i] / (blue_counts[i] + orange_counts[i])))
        draw.rectangle([
            (img_mid - 275, field_top + y_pad[i] - 20), (img_mid - 275 + split, field_top + y_pad[i] + 80)
        ], fill=constants.TEAM_INFO["RL ESPORTS"]["c1"])
        draw.rectangle([
            (img_mid - 275 + split, field_top + y_pad[i] - 20), (img_mid + 275, field_top + y_pad[i] + 80)
        ], fill=constants.TEAM_INFO["RL ESPORTS"]["c2"])
        
        blue_text = str(blue_counts[i]) if i != 1 else "{:.2f}".format(blue_counts[i])
        orange_text = str(orange_counts[i]) if i != 1 else "{:.2f}".format(orange_counts[i])
        draw.text((img_mid, field_top + y_pad[i]), labels[i], fill=BLACK, stroke_fill=WHITE, stroke_width=3, font=constants.BOUR_60, anchor="ma")
        draw.text((blue_x, field_top + y_pad[i]), blue_text, fill=BLACK, font=constants.BOUR_60, anchor="ma")
        draw.text((orange_x, field_top + y_pad[i]), orange_text, fill=BLACK, font=constants.BOUR_60, anchor="ma")

    # # Legend below detail text
    utils.draw_circle_legend(draw, field_top + y_pad[-1] + 75, MARGIN, img_mid + 430, MARKER_SIZE, constants.BOUR_40, 
        left_x=(img_mid - 370), scaling=(2, 3, 4), labels=(("0 xG", 1), ("1 xG", 8.25)))
    
    # Dotted circle logo
    utils.draw_dotted_circle(draw, img_width, MARGIN, config["c1"], config["c2"])
    
    img.save(os.path.join("viz", "images", config["img_name"]))

def main():
    team_one, team_two = "FALCONS", "FEARLESS"
    team_keys = ["FALCONS", "FEARLESS"]
    wins = [3, 0]
    key = "RL ESPORTS"
    data_path = os.path.join("replays", "RLCS 24", "Major 1", "MENA", "OQ 1", "Swiss", "Round 3", "FEAR vs FLCN")
    game_list = utils.read_series_data(data_path)
    
    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": f"{team_keys[0]} {wins[0]} - {wins[1]} {team_keys[1]}",
        "t2": "RLCS 24 MAJOR 1 | MENA OQ 1 | SWISS R3",
        "t3": "SERIES SUMMARY",
        "c1": constants.TEAM_INFO[key]["c1"],
        "c2": constants.TEAM_INFO[key]["c2"],
        "img_name": os.path.join("RLCS 24", "MENA", "summary", f"{team_keys[0]}_{wins[0]}-{wins[1]}_{team_keys[1]}_summary.png")
    }
    create_image(team_one, team_two, team_keys, wins, game_list, config)
    
    return 0
  
if __name__ == "__main__":
    main()