from vispy import scene

import numpy as np
import scipy

import os


def mean_confidence_interval(data, confidence=0.95):
    a = 1.0 * np.array(data)
    n = len(a)
    m, se = np.mean(a), scipy.stats.sem(a)
    h = se * scipy.stats.t.ppf((1 + confidence) / 2.0, n - 1)
    return m, m - h, m + h


start_markers = None
goal_markers = None


def get_latest_pdata(args, cost_idx="all"):
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

    # apply z scale
    def apply_z_scale(array):
        array[:, 2] = (array[:, 2] - _min) * args.z_scale_factor + _min

    apply_z_scale(pos)
    if len(solution_path) > 0:
        apply_z_scale(solution_path)

    edges = pdata["edges"]

    if cost_idx == "all":
        _target_costs = pdata["vertices_costs"].copy().sum(1)
    else:
        _target_costs = pdata["vertices_costs"][:, cost_idx].copy()

    global start_markers, goal_markers

    # if start_markers is None:
    #     start_coor = []
    #     for idx in pdata["start_vertices_id"]:
    #         start_coor.append(pos[idx])
    #     start_coor = np.array(start_coor)
    #
    #     goal_coor = []
    #     for idx in pdata["goal_vertices_id"]:
    #         goal_coor.append(pos[idx])
    #     goal_coor = np.array(goal_coor)
    #     start_markers = scene.Markers(
    #         pos=start_coor, face_color="green", symbol="o", parent=args.view.scene, size=20
    #     )
    #     goal_markers = scene.Markers(
    #         pos=goal_coor, face_color="red", symbol="o", parent=args.view.scene, size=20
    #     )
    # else:
    #     start_markers.set_data(pos=start_coor)
    #     goal_markers.set_data(pos=goal_coor)

    # print(_min, _max)

    # colors = np.ones((len(_target_costs), 3)) * .1
    # colors[:,0] = (_target_costs - _min) / (_max - _min)

    return pos, edges, solution_path, _target_costs  # , _min, _max


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
