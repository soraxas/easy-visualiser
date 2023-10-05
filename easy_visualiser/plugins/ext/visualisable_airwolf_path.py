import numpy as np
from nav_msgs.msg import Path
from vispy import scene
from vispy.color import get_colormap

from easy_visualiser.input.ros import RosComm
from easy_visualiser.modal_control import ModalControl
from easy_visualiser.plugin_capability import ToggleableMixin, WidgetsMixin
from easy_visualiser.plugins import VisualisablePlugin
from easy_visualiser.plugins.visualisable_lineplot import Visualisable2DLinePlot
from easy_visualiser.utils import ToggleableBool, boolean_to_onoff
from easy_visualiser.utils.dummy import DUMMY_COLOUR, DUMMY_CONNECT, DUMMY_LINE


class SolutionLine:
    def __init__(self, _scene, offset=None, color="red"):
        self.path = None
        self.line_visual = scene.Line(
            connect="strip",
            antialias=False,
            method="gl",
            # method='agg',
            parent=_scene,
            width=5,
            color=color,
        )

    def set_path(self, _path):
        if len(_path) <= 0:
            _path = DUMMY_LINE
        self.line_visual.set_data(pos=_path)


class VisualisablePlannerGraph(
    Visualisable2DLinePlot,
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def name(self):
        return "my_plot"

    def construct_plugin(self) -> None:
        super().construct_plugin()
        self.sol_lines = SolutionLine(self.visualiser.visual_parent)
        self.fake_sol_lines = SolutionLine(self.visualiser.visual_parent, offset=200000)

        self.lines = scene.Line(
            antialias=False, method="gl", parent=self.visualiser.visual_parent, width=3
        )
        self.lines.set_data(pos=DUMMY_LINE)

        RosComm.get_instance().subscribe(
            topic="/vulcan/aircraft_manager/lidar_avoidance",
            msg_type=Path,
            callback=self.callback,
        )

    def callback(self, data):
        # import rospy

        # rospy.loginfo(rospy.get_caller_id() + "I heard %s", len(data.poses))
        # print
        # rospy.loginfo(rospy.get_caller_id() + "I heard %s", data)
        poses = np.array(
            [
                [p.pose.position.x, p.pose.position.y, p.pose.position.z]
                for p in data.poses
            ]
        )

        self.lines.set_data(poses)

        print(poses.shape)
        self.plot(data=poses[:, :2], auto_range=True)
        return

        step_size = 0.1

        all_points = []
        for i in range(poses.shape[0] - 1):
            num = np.linalg.norm(poses[i + 1, :] - poses[i, :]) / step_size

            # FIXME this is missing some value
            _pts = np.linspace(poses[i, :], poses[i + 1, :], int(num))
            all_points.append(_pts)

        all_points = np.vstack(all_points)
        print(all_points.shape)

        # import scipy
        # from scipy.interpolate import LinearNDInterpolator
        # # f = interpolate.interp(x, y, z, kind='linear')
        #
        # # print(poses.shape)
        # pos_diff = poses[1:, :]-poses[:-1, :]
        # dist_norm = np.linalg.norm(pos_diff, axis=1)
        # dist_norm = np.cumsum(np.hstack([[0], dist_norm]))
        # # # print(poses.shape, dist_norm, )
        # # f = LinearNDInterpolator(poses, dist_norm)
        #
        # print(poses.shape, dist_norm.shape)
        #
        # from scipy import interpolate
        # x = np.arange(0, 10)
        # y = np.exp(-x / 3.0)
        # f = interpolate.interp1d(dist_norm, poses)

        speed = 10  # m/s
        speed = speed * step_size  # m/s

        velocity_unit_vec = all_points[1:, :] - all_points[:-1, :]
        velocity_unit_vec = (
            velocity_unit_vec / np.linalg.norm(velocity_unit_vec, axis=1)[:, None]
        )

        velocity_vec = velocity_unit_vec * speed

        # speed = np.linalg.norm(velocity_unit_vec * speed, axis=1)
        # print(velocity_vec.shape, all_points.shape)
        # print(velocity_vec)
        print(all_points)

        ahah = [all_points[0]]
        for i in range(velocity_vec.shape[0]):
            _vec = velocity_vec[i]
            if np.any(np.isnan(_vec)):
                _vec = 0
            ahah.append(ahah[-1] + _vec)

        print(np.array(ahah))

        # print(vec_unit_vec * speed)

        self.lines.set_data(all_points)
        # self.lines.set_data(poses)
        if not self.had_set_range:
            self.set_range()

    # run simultaneously.

    def __switch_cost_cb(self) -> None:
        if self.cost_index is None:
            self.cost_index = 0
        else:
            self.cost_index += 1
        self._last_modify_time = None
        self.update()

    def __construct_graph(self, pos, edges, costs) -> None:
        #################################################
        #################################################

        _min = costs.min()
        _max = costs.max()

        _min = 0
        if self.cost_min is not None:
            _min = self.cost_min
        if self.cost_max is not None:
            _max = self.cost_max

        if np.isnan(_max):
            _max = np.nanmax(costs[costs != np.inf])
        if np.isnan(_min):
            _min = np.nanmin(costs[costs != -np.inf])

        costs = np.clip(costs, _min, _max)
        if _max == _min:
            costs[:] = np.nan
        else:
            costs = (costs - _min) / (_max - _min)

        # costs = costs - _min
        #################################################
        #################################################

        colors = self.colormap.map(costs)  # [:-2]

        self.lines.set_data(pos=pos, connect=edges, color=colors)
        self.cbar_widget.clim = (_min, _max)

    def __construct_solution(self, solution_path) -> None:
        if not self.graph_solution_toggle:
            solution_path = []
        self.sol_lines.set_path(solution_path)
        if self.graph_solution_toggle and self.graph_toggle:
            fake_solution_path = solution_path.copy()
            self.fake_sol_lines.set_path(fake_solution_path)
        else:
            self.fake_sol_lines.set_path([])

    def turn_on_plugin(self):
        if not super().turn_on_plugin():
            return False
        pos, edges, solution_path, costs = self.get_latest_pdata()
        if self.graph_toggle:
            self.__construct_graph(pos, edges, costs)
        self.__construct_solution(solution_path)
        return True

    def turn_off_plugin(self):
        if not super().turn_off_plugin():
            return False
        self.lines.set_data(pos=DUMMY_LINE, connect=DUMMY_CONNECT, color=DUMMY_COLOUR)
        self.cbar_widget.clim = (np.nan, np.nan)

        self.fake_sol_lines.set_path([])
        return True

    def on_update(self):
        self.turn_on_plugin()
        if not self.had_set_range:
            self.set_range()

    def get_latest_pdata(self):
        pdata = np.load(self.target_file)

        pos = pdata["vertices_coordinate"]
        solution_path = pdata["solution_coordinate"]

        _min = pos[:, 2].min()
        # z_scaler.set_min(_min)

        # apply z scale

        pos[:, 2] = self.other_plugins.zscaler.scaler(pos[:, 2])
        if len(solution_path) > 0:
            solution_path[:, 2] = self.other_plugins.zscaler.scaler(solution_path[:, 2])

        edges = pdata["edges"]

        if (
            self.cost_index is not None
            and self.cost_index >= pdata["vertices_costs"].shape[1]
        ):
            self.cost_index = None

        if self.cost_index is None:
            _target_costs = pdata["vertices_costs"].copy().sum(1)
        else:
            _target_costs = pdata["vertices_costs"][:, self.cost_index].copy()

        self.cbar_widget.label = (
            f"Cost {'all' if self.cost_index is None else self.cost_index}"
        )

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
        #         pos=start_coor,
        #         face_color="green",
        #         symbol="o",
        #         parent=args.view.scene,
        #         size=20,
        #     )
        #     goal_markers = scene.Markers(
        #         pos=goal_coor, face_color="red", symbol="o", parent=args.view.scene,
        #         size=20
        #     )

        # print(_min, _max)

        # colors = np.ones((len(_target_costs), 3)) * .1
        # colors[:,0] = (_target_costs - _min) / (_max - _min)

        return pos, edges, solution_path, _target_costs  # , _min, _max
