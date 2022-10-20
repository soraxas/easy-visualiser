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

    def __call__(self, z_vals):
        return (z_vals - self.min) * self.z_scale_factor + self.min


def get_latest_pdata(args):
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
    # z_scaler.set_min(_min)

    # apply z scale

    pos[:, 2] = args.z_scaler(pos[:, 2])
    if len(solution_path) > 0:
        solution_path[:, 2] = args.z_scaler(solution_path[:, 2])

    edges = pdata["edges"]

    if (
        args.cost_index is not None
        and args.cost_index >= pdata["vertices_costs"].shape[1]
    ):
        args.cost_index = None

    if args.cost_index is None:
        _target_costs = pdata["vertices_costs"].copy().sum(1)
    else:
        _target_costs = pdata["vertices_costs"][:, args.cost_index].copy()

    args.cbar_widget.label = (
        f"Cost {'all' if args.cost_index is None else args.cost_index}"
    )

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
    def __init__(self, xy_start, xy_goal, depth, bathy_interp):
        self.xy_start = xy_start
        self.xy_goal = xy_goal
        self.depth = depth
        self.start_idx = 0
        self.bathy_interp = bathy_interp

    def get_vertices(self):
        depth1 = -self.depth
        depth2 = -self.depth

        if self.bathy_interp is not None:
            # cut it off at the bathymetry
            depth1 = max(self.bathy_interp(*self.xy_start), -self.depth)
            depth2 = max(self.bathy_interp(*self.xy_goal), -self.depth)

        return (
            (*self.xy_start, 0),
            (*self.xy_start, depth1),
            (*self.xy_goal, 0),
            (*self.xy_goal, depth2),
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
    def __init__(self, depth, points, bathy_interp) -> None:
        self.walls = []
        self.depth = depth

        _start_idx = 0
        for i in range(len(points)):
            w = Wall(
                points[i],
                points[(i + 1) % len(points)],
                depth=self.depth,
                bathy_interp=bathy_interp,
            )
            w.start_idx = _start_idx
            _start_idx += len(w.get_vertices())
            self.walls.append(w)

    @property
    def vertices(self):
        for w in self.walls:
            yield from w.get_vertices()

    @property
    def faces(self):
        for w in self.walls:
            yield from w.get_faces()

    @property
    def depth(self):
        return self.__depth

    @depth.setter
    def depth(self, value):
        self.__depth = value
        for w in self.walls:
            w.depth = value

    def __repr__(self) -> str:
        return f"{np.array([w.xy_start for w in self.walls])}"


def get_keepout_zones(args, bathy_interp):
    pdata = np.load(args.datapath)

    return [
        KeepoutZone(
            depth=args.z_scaler(pdata["keepout_zones_depths"][i]),
            points=pdata[f"keepout_zones_{i}"],
            bathy_interp=bathy_interp,
        )
        for i in range(len(pdata["keepout_zones_depths"]))
    ]


# bar.canvas = view.scene

last_modify_time = None


def update(args, ev):
    args.vis.update()
