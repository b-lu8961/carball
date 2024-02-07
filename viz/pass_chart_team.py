from viz import constants, utils

import os
from PIL import Image, ImageDraw, ImageFont

IMAGE_X, IMAGE_Y = 2550, 1800
MARGIN = 40

MARKER_SIZE = 20
MID_X, MID_Y = (constants.MAP_Y + (MARGIN * 4)) / 2, (constants.MAP_X + (MARGIN * 2)) / 2

WHITE, BLACK = (255,255,255), (0,0,0)
LIGHT_GREY, DARK_GREY = (140,140,140), (70,70,70)

def get_y(val, img_height):
    return img_height - val

def draw_marker(draw, pos, mark_type, img_height, size=MARKER_SIZE, outline=None, fill=None, width=2):
    base_x = MID_X + (pos[0] / constants.SCALE)
    base_y = MID_Y + (pos[1] / constants.SCALE)
    if mark_type == "C":
        draw.ellipse([(base_x - size, get_y(base_y + size, img_height)), (base_x + size, get_y(base_y - size, img_height))], 
            outline=outline, fill=fill, width=width)
    elif mark_type == "ahead":
        draw.chord([(base_x - size, get_y(base_y + size, img_height)), (base_x + size, get_y(base_y - size, img_height))], 
            -90, 90, fill=BLACK)
    else:
        draw.chord([(base_x - size, get_y(base_y + size, img_height)), (base_x + size, get_y(base_y - size, img_height))], 
            90, 270, fill=BLACK)
        
def draw_line(image, p1, p2, img_height, colors):
    x1, x2 = MID_X + (p1[0] / constants.SCALE), MID_X + (p2[0] / constants.SCALE)
    y1, y2 = get_y(MID_Y + (p1[1] / constants.SCALE), img_height), get_y(MID_Y + (p2[1] / constants.SCALE), img_height)
    slope = (y2 - y1) / (x2 - x1)
    if abs(slope) <= 1:
        poly = [(x1, y1 - 2), (x2, y2 - 2), (x2, y2 + 2), (x1, y1 + 2)]
    else:
        poly = [(x1 - 2, y1), (x2 - 2, y2), (x2 + 2, y2), (x1 + 2, y1)]
    
    utils.linear_gradient(image, poly, (x1, y1), (x2, y2), colors[0], colors[1])

def draw_field(team_name, game_list):
    width, height = round(constants.MAP_Y) + (MARGIN * 4), round(constants.MAP_X) + (MARGIN * 2)
    img = Image.new(mode="RGBA", size = (width, height), color=WHITE)

    draw = ImageDraw.Draw(img)
    utils.draw_field_lines(draw, MARGIN, height)
    
    gp = 0
    passes, dribbles, turnovers = {}, {}, {}
    for game in game_list:
        active_teams = [team.name for team in game.teams]
        if team_name not in active_teams:
            continue

        team_is_orange = [team.is_orange for team in game.teams if team.name == team_name][0]
        colors = [(255, 251, 243), (255, 128, 0)] if team_is_orange else [(243, 251, 255), (0, 128, 255)]

        gp += 1
        team_ids = [player.id.id for player in game.players if player.is_orange == team_is_orange]
        player_names = [player.name for player in game.players if player.is_orange == team_is_orange]
        for i in range(len(game.game_stats.hits) - 1):
            curr_hit = game.game_stats.hits[i]
            next_hit = game.game_stats.hits[i + 1]

            if curr_hit.player_id.id not in team_ids:
                continue

            curr_pos = (curr_hit.ball_data.pos_y, curr_hit.ball_data.pos_x)
            next_pos = (next_hit.ball_data.pos_y, next_hit.ball_data.pos_x)
            if team_is_orange:
                curr_pos = (curr_pos[0] * -1, curr_pos[1] * -1)
                next_pos = (next_pos[0] * -1, next_pos[1] * -1)

            if curr_hit.match_goal or not curr_hit.HasField("next_hit_frame_number"):
                continue

            curr_pl = [pl for pl in game.players if pl.id.id == curr_hit.player_id.id][0]
            next_pl = [pl for pl in game.players if pl.id.id == next_hit.player_id.id][0]
            if (curr_pl.is_orange == next_pl.is_orange): 
                if (curr_pl.name != next_pl.name):
                    # Pass
                    if curr_pl.name not in passes:
                        passes[curr_pl.name] = []
                    passes[curr_pl.name].append((curr_hit.frame_number, next_pl.name))
                    # if curr_hit.match_assist:
                    #     if next_hit.match_goal:
                    #         draw_marker(draw, curr_pos, "C", height, size=20, fill=touch_colors[0])
                    #     else:
                    #         draw_marker(draw, curr_pos, "C", height, size=15, fill=touch_colors[1])
                    # else:
                    #draw_marker(draw, curr_pos, "C", height, size=10, outline=touch_colors[2])
                    
                    draw_marker(draw, next_pos, "C", height, size=5, fill=colors[1])
                    draw_line(img, curr_pos, next_pos, height, colors)
            #     else:
            #         # Dribble
            #         key = (curr_pl.is_orange, curr_pl.name)
            #         if key not in dribbles:
            #             dribbles[key] = []
            #         dribbles[key].append(curr_hit.frame_number)
            #         #draw_marker(draw, curr_hit.ball_data, "C", height, size=5, outline=touch_colors[2])
            # else:
            #     # Turnover
            #     key = (curr_pl.is_orange, curr_pl.name)
            #     if key not in turnovers:
            #         turnovers[key] = []
            #     turnovers[key].append(curr_hit.frame_number)
            #     #draw_marker(draw, curr_hit.ball_data, "C", height, size=7, fill=BLACK)
            

    return img, sorted(player_names), passes, colors


def create_image(team_name: str, game_list, config):
    img = Image.new(mode = "RGBA", size = (IMAGE_X, IMAGE_Y), color = WHITE)
    draw = ImageDraw.Draw(img)
    
    # Logo in top left
    logo_width, _ = utils.draw_team_logo(img, MARGIN, config["logo"])

    # Title text
    utils.draw_title_text(draw, logo_width, MARGIN, config, constants.BOUR_80, constants.BOUR_40)

    # Main field image
    field_img, names, passes, colors = draw_field(team_name, game_list)
    img.paste(field_img, (MARGIN, get_y(field_img.height + MARGIN, IMAGE_Y)))

    # Attack direction text
    attack_text = "Attacking Direction"
    attack_len = draw.textlength(attack_text, font=constants.BOUR_50)
    draw.text((MID_X - (attack_len / 2) + MARGIN, get_y(field_img.height + (1.5 * MARGIN), IMAGE_Y)), 
        f"{attack_text} >>", fill=DARK_GREY, font=constants.BOUR_50)
    
    # Between-player pass data
    name_x, name_y = (field_img.width + IMAGE_X) / 2, get_y(field_img.height - (4 * MARGIN), IMAGE_Y)
    draw.multiline_text((name_x, name_y), 
        f"{names[0]}\n\n\n\n{names[1]}\n\n\n{names[0]}\n\n\n\n{names[2]}\n\n\n{names[1]}\n\n\n\n{names[2]}",
        fill=BLACK, font=constants.BOUR_60, align="center", anchor="ma"
    )
    left_base, right_base = name_x - 40, name_x + 40
    pairs = [(0, 1), (0, 2), (1, 2)]
    for i in range(len(pairs)):
        pair = pairs[i]
        line_top, line_bot = name_y + 70 + (i * 365), name_y + 200 + (i * 365)
        utils.linear_gradient(img, [(left_base - 2, line_top), (left_base - 2, line_bot), (left_base + 2, line_bot), (left_base + 2, line_top)], 
            (left_base, line_top), (left_base, line_bot), colors[0], colors[1])
        draw.ellipse([(left_base - 5, line_bot - 5), (left_base + 5, line_bot + 5)], fill=colors[1])
        left_num = len([p for p in passes[names[pair[0]]] if p[1] == names[pair[1]]])
        draw.text((left_base - 30, line_top + 40), str(left_num), font=constants.BOUR_50, fill=DARK_GREY, anchor="ra")

        utils.linear_gradient(img, [(right_base - 2, line_top), (right_base - 2, line_bot), (right_base + 2, line_bot), (right_base + 2, line_top)], 
            (right_base, line_bot), (right_base, line_top), colors[0], colors[1])
        draw.ellipse([(right_base - 5, line_top - 5), (right_base + 5, line_top + 5)], fill=colors[1])
        right_num = len([p for p in passes[names[pair[1]]] if p[1] == names[pair[0]]])
        draw.text((right_base + 30, line_top + 40), str(right_num), font=constants.BOUR_50, fill=DARK_GREY, anchor="la")

    # Pass legend
    draw.line([(field_img.width + (4 * MARGIN), IMAGE_Y - (5.5 * MARGIN)), (IMAGE_X - (4 * MARGIN), IMAGE_Y - (5.5 * MARGIN))], 
        fill=LIGHT_GREY, width=4)
    utils.linear_gradient(img, [(name_x - 75, IMAGE_Y - (3.5 * MARGIN) - 2), (name_x + 75, IMAGE_Y - (3.5 * MARGIN) - 2), (name_x + 75, IMAGE_Y - (3.5 * MARGIN) + 2), (name_x - 75, IMAGE_Y - (3.5 * MARGIN) + 2)], 
        (name_x - 75, IMAGE_Y - (3.5 * MARGIN)), (name_x + 75, IMAGE_Y - (3.5 * MARGIN)), colors[0], colors[1])
    draw.ellipse([(name_x + 75 - 5, IMAGE_Y - (3.5 * MARGIN) - 5), (name_x + 75 + 5, IMAGE_Y - (3.5 * MARGIN) + 5)], fill=colors[1])
    draw.multiline_text((name_x - 100, IMAGE_Y - (3.5 * MARGIN)), "Pass\nstart", font=constants.BOUR_40, fill=DARK_GREY, align="center", anchor="rm")
    draw.multiline_text((name_x + 100, IMAGE_Y - (3.5 * MARGIN)), "Pass\nend", font=constants.BOUR_40, fill=DARK_GREY, align="center", anchor="lm")
    
    # Dotted circle logo
    utils.draw_dotted_circle(draw, IMAGE_X, MARGIN, config["c1"], config["c2"])
    
    img.save(os.path.join("viz", "images", config["img_name"]))


def main():
    team_name = "DIGNITAS"
    key = "DIGNITAS"
    config = {
        "logo": constants.TEAM_INFO[key]["logo"],
        "t1": key,
        "t2": "BANDITS ON WHEELS: FALL SHOWDOWN #6 | GRAND FINAL",
        "t3": "PASS MAP",
        "c1": constants.TEAM_INFO[key]["c1"],
        "c2": constants.TEAM_INFO[key]["c2"],
        "img_name": os.path.join("BOW Showdown", "touches", f"{team_name.lower()}_passes.png")
    }

    data_path = os.path.join("replays", "BoW FS", "Event 6", "GF")
    game_iter = utils.read_series_data(data_path)
    create_image(team_name, game_iter, config)
    
    return 1
  
if __name__ == "__main__":
    main()