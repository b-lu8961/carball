# Goal dimensions
# blue goal -> negative y; orange goal -> positive y
GOAL_X, GOAL_Y, GOAL_Z = 1786, 880, 642.775 
GOAL_X_LIMS = (-GOAL_X / 2, GOAL_X / 2)
GOAL_BOUNDS = [
    [(GOAL_X_LIMS[0], 0), (GOAL_X_LIMS[0], GOAL_Z)],
    [(GOAL_X_LIMS[0], GOAL_Z), (GOAL_X_LIMS[1], GOAL_Z)],
    [(GOAL_X_LIMS[1], 0), (GOAL_X_LIMS[1], GOAL_Z)]
]

# Goal sections
LEFT_THIRD = GOAL_X_LIMS[0] + (GOAL_X / 3)
RIGHT_THIRD = GOAL_X_LIMS[1] - (GOAL_X / 3)
LOWER_THIRD = 0 + (GOAL_Z / 3)
UPPER_THIRD = GOAL_Z - (GOAL_Z / 3)
GOAL_SECTIONS = [
    [
        [(GOAL_X_LIMS[0], UPPER_THIRD), (GOAL_X / 3), (GOAL_Z / 3)],
        [(LEFT_THIRD, UPPER_THIRD), (GOAL_X / 3), (GOAL_Z / 3)],
        [(RIGHT_THIRD, UPPER_THIRD), (GOAL_X / 3), (GOAL_Z / 3)]
    ],
    [
        [(GOAL_X_LIMS[0], LOWER_THIRD), (GOAL_X / 3), (GOAL_Z / 3)],
        [(LEFT_THIRD, LOWER_THIRD), (GOAL_X / 3), (GOAL_Z / 3)],
        [(RIGHT_THIRD, LOWER_THIRD), (GOAL_X / 3), (GOAL_Z / 3)]
    ],
    [
        [(GOAL_X_LIMS[0], 0), (GOAL_X / 3), (GOAL_Z / 3)],
        [(LEFT_THIRD, 0), (GOAL_X / 3), (GOAL_Z / 3)],
        [(RIGHT_THIRD, 0), (GOAL_X / 3), (GOAL_Z / 3)]
    ]
]

# Field dimensions from RL Bot Wiki
SCALE = 6
MAP_X, MAP_Y, MAP_Z = 8192 / SCALE, 10240 / SCALE, 2044 / SCALE
CORNER_SIDE = 1152 / SCALE
MAP_Y_THIRD = MAP_Y / 3
MAP_X_LIMS = (-MAP_X / 2, MAP_X / 2)
MAP_Y_LIMS = (-MAP_Y / 2, MAP_Y / 2)
MAP_Z_LIMS = (0, MAP_Z)

# Field bounds/coordinates from different perspectives
MAP_BOUNDS_TOP = [
    [(MAP_X_LIMS[0], MAP_Y_LIMS[0] + CORNER_SIDE), (MAP_X_LIMS[0], MAP_Y_LIMS[1] - CORNER_SIDE)],
    [(MAP_X_LIMS[0], MAP_Y_LIMS[1] - CORNER_SIDE), (MAP_X_LIMS[0] + CORNER_SIDE, MAP_Y_LIMS[1])],
    [(MAP_X_LIMS[0] + CORNER_SIDE, MAP_Y_LIMS[1]), (GOAL_X_LIMS[0], MAP_Y_LIMS[1])],
    [(GOAL_X_LIMS[0], MAP_Y_LIMS[1]), (GOAL_X_LIMS[1], MAP_Y_LIMS[1])],
    [(GOAL_X_LIMS[1], MAP_Y_LIMS[1]), (MAP_X_LIMS[1] - CORNER_SIDE, MAP_Y_LIMS[1])],
    [(MAP_X_LIMS[1] - CORNER_SIDE, MAP_Y_LIMS[1]), (MAP_X_LIMS[1], MAP_Y_LIMS[1] - CORNER_SIDE)],
    [(MAP_X_LIMS[1], MAP_Y_LIMS[1] - CORNER_SIDE), (MAP_X_LIMS[1], MAP_Y_LIMS[0] + CORNER_SIDE)],
    [(MAP_X_LIMS[1], MAP_Y_LIMS[0] + CORNER_SIDE), (MAP_X_LIMS[1] - CORNER_SIDE, MAP_Y_LIMS[0])],
    [(MAP_X_LIMS[1] - CORNER_SIDE, MAP_Y_LIMS[0]), (GOAL_X_LIMS[1], MAP_Y_LIMS[0])],
    [(GOAL_X_LIMS[1], MAP_Y_LIMS[0]), (GOAL_X_LIMS[0], MAP_Y_LIMS[0])],
    [(GOAL_X_LIMS[0], MAP_Y_LIMS[0]), (MAP_X_LIMS[0] + CORNER_SIDE, MAP_Y_LIMS[0])],
    [(MAP_X_LIMS[0] + CORNER_SIDE, MAP_Y_LIMS[0]), (MAP_X_LIMS[0], MAP_Y_LIMS[0] + CORNER_SIDE)],
]

MAP_BOUNDS_TOP_HORIZ = [[(coord[0][1], coord[0][0]), (coord[1][1], coord[1][0])] for coord in MAP_BOUNDS_TOP]

MAP_BOUNDS_SIDE = [
    [(MAP_Y_LIMS[0], 0), (MAP_Y_LIMS[0], GOAL_Z)],
    [(MAP_Y_LIMS[0], GOAL_Z), (MAP_Y_LIMS[0], MAP_Z)],
    [(MAP_Y_LIMS[0], MAP_Z), (MAP_Y_LIMS[1], MAP_Z)],
    [(MAP_Y_LIMS[1], MAP_Z), (MAP_Y_LIMS[1], GOAL_Z)],
    [(MAP_Y_LIMS[1], GOAL_Z), (MAP_Y_LIMS[1], 0)]
]

# Misc game numbers
BALL_RAD = 92.75
SUPERSONIC_SPEED = 2200
BOOSTING_SPEED = 1410

### Viz constants

# Field line segment colors
TOP_COLORS = ['black', 'black', 'black', 'orange', 'black', 'black', 
              'black', 'black', 'black', 'blue', 'black', 'black']
SIDE_COLORS = ['blue', 'black', 'black', 'black', 'orange']

MARKERS = ['o', 's', 'x']
# From ballchasing charts
BLUE_COLORS = [(32, 156, 238), (21, 101, 192), (122, 64, 236)]
ORANGE_COLORS = [(color[2], color[1], color[0]) for color in BLUE_COLORS]
COLOR_MAP = {'blue': BLUE_COLORS, 'orange': ORANGE_COLORS}

TEAM_INFO = {
    "RL ESPORTS": {
        "logo": "RL_Esports.PNG",
        "c1": (78, 159, 216),
        "c2": (236, 114, 57),
        "c3": (255, 255, 255)
    },
    # EU
    "TEAM VITALITY": {
        "logo": "TEAM_VITALITY.PNG",
        "c1": (0, 0, 0),
        "c2": (250, 225, 0),
        "c3": (255, 255, 255)
    },
    "TEAM BDS": {
        "logo": "Team_BDS.png",
        "c1": (255, 0, 117),
        "c2": (5, 27, 53),
        "c3": (255, 255, 255)
    },
    "KARMINE CORP": {
        "logo": "Karmine_Corp.png",
        "c1": (13, 20, 28),
        "c2": (2, 200, 255),
        "c3": (255, 255, 255)
    },
    "TEAM LIQUID": {
        "logo": "",
        "c1": (),
        "c2": (),
        "c3": ()
    },
    # NA
    "G2 ESPORTS": {
        "logo": "",
        "c1": (),
        "c2": (),
        "c3": ()
    },
    "GENGMOBIL1": {
        "logo": "",
        "c1": (),
        "c2": (),
        "c3": ()
    },
    "SPACESTATION": {
        "logo": "",
        "c1": (),
        "c2": (),
        "c3": ()
    },
    # MENA
    "FALCONS": {
        "logo": "",
        "c1": (),
        "c2": (),
        "c3": ()
    }
}