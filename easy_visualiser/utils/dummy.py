import numpy as np

FAR_AWAY_LOCATION = 0

DUMMY_LINE = np.array(
    [
        [FAR_AWAY_LOCATION, FAR_AWAY_LOCATION, FAR_AWAY_LOCATION],
        [FAR_AWAY_LOCATION, FAR_AWAY_LOCATION + 0.1, FAR_AWAY_LOCATION],
    ]
)
DUMMY_ARROW = np.array(
    [
        [
            FAR_AWAY_LOCATION,
            FAR_AWAY_LOCATION,
            FAR_AWAY_LOCATION,
            FAR_AWAY_LOCATION,
            FAR_AWAY_LOCATION,
            FAR_AWAY_LOCATION,
        ],
        [
            FAR_AWAY_LOCATION,
            FAR_AWAY_LOCATION + 0.1,
            FAR_AWAY_LOCATION,
            FAR_AWAY_LOCATION,
            FAR_AWAY_LOCATION,
            FAR_AWAY_LOCATION,
        ],
    ]
)
DUMMY_AXIS_VAL = np.array([[0]])
DUMMY_CONNECT = np.array([[0, 1]])
DUMMY_COLOUR = np.array([[0, 0, 0], [0, 0, 0]])
DUMMY_POINTS = np.zeros([1, 3])
