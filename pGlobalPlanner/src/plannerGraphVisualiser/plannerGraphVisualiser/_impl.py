from vispy import scene

import numpy as np
import scipy
import scipy.stats

import os


def mean_confidence_interval(data, confidence=0.95):
    a = 1.0 * np.array(data)
    n = len(a)
    m, se = np.mean(a), scipy.stats.sem(a)
    h = se * scipy.stats.t.ppf((1 + confidence) / 2.0, n - 1)
    return m, m - h, m + h


start_markers = None
goal_markers = None


class Zscaler:
    def __init__(self, z_scale_factor) -> None:
        self.min = 0
        self.z_scale_factor = z_scale_factor

    def set_min(self, min):
        self.min = min

    def __call__(self, array):
        array[:, 2] = (array[:, 2] - self.min) * self.z_scale_factor + self.min


def get_latest_pdata(args, z_scaler: Zscaler, cost_idx="all"):
    pdata = np.load(args.datapath)
    # pdata["vertices_id"]
    # pdata["edges"]
    # # pdata['start_coordinate']
    # # pdata['goal_coordinate']
    # pdata["edges_costs"]
    # pdata["vertices_coordinate"]

    pos = pdata["vertices_coordinate"]
    solution_path = pdata["solution_coordinate"]

    _min = pos[:, 2].min()
    z_scaler.set_min(_min)

    # apply z scale

    z_scaler(pos)
    if len(solution_path) > 0:
        z_scaler(solution_path)

    edges = pdata["edges"]

    if cost_idx == "all":
        _target_costs = pdata["vertices_costs"].copy().sum(1)
    else:
        _target_costs = pdata["vertices_costs"][:, cost_idx].copy()

    global start_markers, goal_markers

    if start_markers is None:
        start_coor = []
        for idx in pdata["start_vertices_id"]:
            start_coor.append(pos[idx])
        start_coor = np.array(start_coor)

        goal_coor = []
        for idx in pdata["goal_vertices_id"]:
            goal_coor.append(pos[idx])
        goal_coor = np.array(goal_coor)
        start_markers = scene.Markers(
            pos=start_coor,
            face_color="green",
            symbol="o",
            parent=args.view.scene,
            size=20,
        )
        goal_markers = scene.Markers(
            pos=goal_coor, face_color="red", symbol="o", parent=args.view.scene, size=20
        )
    # else:
    #     start_markers.set_data(pos=start_coor)
    #     goal_markers.set_data(pos=goal_coor)

    # print(_min, _max)

    # colors = np.ones((len(_target_costs), 3)) * .1
    # colors[:,0] = (_target_costs - _min) / (_max - _min)

    return pos, edges, solution_path, _target_costs  # , _min, _max


class Wall:
    def __init__(self, xy_start, xy_goal, depth):
        self.xy_start = xy_start
        self.xy_goal = xy_goal
        self.depth = depth
        self.start_idx = 0

    def get_vertices(self):
        return (
            (*self.xy_start, 0),
            (*self.xy_start, -self.depth),
            (*self.xy_goal, 0),
            (*self.xy_goal, -self.depth),
        )

    def at(self, idx):
        return self.start_idx + idx

    def get_faces(self):
        return (self.at(0), self.at(1), self.at(2)), (
            self.at(1),
            self.at(2),
            self.at(3),
        )


class KeepoutZone:
    def __init__(self, depth, points) -> None:
        self.depth = depth
        self.walls = []
        self.vertices = []
        self.faces = []

        for i in range(len(points)):

            w = Wall(points[i], points[(i + 1) % len(points)], depth=self.depth)
            w.start_idx = len(self.vertices)
            self.vertices.extend(w.get_vertices())
            self.faces.extend(w.get_faces())
            self.walls.append(w)

    def __repr__(self) -> str:
        return f"{np.array([w.xy_start for w in self.walls])}"


def get_keepout_zones(args):
    pdata = np.load(args.datapath)

    return [
        KeepoutZone(
            depth=pdata["keepout_zones_depths"][i], points=pdata[f"keepout_zones_{i}"]
        )
        for i in range(len(pdata["keepout_zones_depths"]))
    ]


# bar.canvas = view.scene

last_modify_time = None


def update(args, ev):
    global last_modify_time

    _mtime = os.path.getmtime(args.datapath)
    # print(_mtime)
    if last_modify_time is None or (last_modify_time < _mtime):

        for v in args.vis:
            v.update()
        last_modify_time = _mtime
