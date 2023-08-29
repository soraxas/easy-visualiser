from typing import Optional

import numpy as np
from vispy import scene
from vispy.color import get_colormap

from easy_visualiser.maths import mean_confidence_interval
from easy_visualiser.modal_control import ModalControl
from easy_visualiser.plugin_capability import (
    CallableAndFileModificationGuardableMixin,
    IntervalUpdatableMixin,
    ToggleableMixin,
    WidgetsMixin,
)
from easy_visualiser.plugins import VisualisablePlugin
from easy_visualiser.utils import ToggleableBool, boolean_to_onoff
from easy_visualiser.utils.dummy import DUMMY_COLOUR, DUMMY_CONNECT, DUMMY_LINE


class SolutionLine:
    def __init__(self, _scene, offset=None, color="red"):
        self.path = None
        self.offset = offset
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
        else:
            if self.offset:
                _path[:, -1] += self.offset
        self.line_visual.set_data(pos=_path)


class VisualisablePlannerGraph(
    CallableAndFileModificationGuardableMixin,
    WidgetsMixin,
    ToggleableMixin,
    IntervalUpdatableMixin,
    VisualisablePlugin,
):
    lines = None
    cbar_widget: scene.ColorBarWidget
    __had_set_range: bool = False
    sol_lines: SolutionLine
    fake_sol_lines: SolutionLine

    def __init__(
        self,
        graph_data_path: str,
        graph_toggle: ToggleableBool,
        graph_solution_toggle: ToggleableBool,
        graph_solution_extra_toggle: ToggleableBool,
        use_ci: bool = True,
        cost_min: Optional[float] = None,
        cost_max: Optional[float] = None,
        colormap: str = "plasma",
    ):
        super().__init__()
        self.guarding_callable = lambda: True
        self.graph_data_path = graph_data_path
        self.graph_toggle = graph_toggle
        self.graph_solution_toggle = graph_solution_toggle
        self.graph_solution_extra_toggle = graph_solution_extra_toggle
        self.use_ci = use_ci
        self.colormap = get_colormap(colormap)
        self.cost_min = cost_min
        self.cost_max = cost_max

        self.cost_index: Optional[int] = None

        self.add_mappings(
            ModalControl(
                "p",
                [
                    (
                        "g",
                        lambda: f"toggle planner graph [{boolean_to_onoff(self.graph_toggle)}]",
                        self.__toggle_graph_cb,
                    ),
                    (
                        "s",
                        lambda: f"toggle planner solution [{boolean_to_onoff(self.graph_solution_toggle)}]",
                        self.__toggle_solution_cb,
                    ),
                    (
                        "c",
                        lambda: f"switch cost index [{'all' if self.cost_index is None else self.cost_index}]",
                        self.__switch_cost_cb,
                    ),
                ],
                modal_name="global planner graph",
            )
        )

    def __toggle_graph_cb(self):
        self.graph_toggle.toggle()
        self.graph_solution_extra_toggle.set(not self.graph_toggle.get())
        if self.graph_toggle:
            self.turn_on_plugin()
        else:
            self.turn_off_plugin()

    def __toggle_solution_cb(self):
        self.graph_solution_toggle.toggle()
        self.on_update()

    def get_constructed_widgets(self):
        cbar_widget = scene.ColorBarWidget(
            label="Cost",
            clim=(0, 99),
            cmap=self.colormap,
            orientation="right",
            border_width=1,
            label_color="#ffffff",
        )
        cbar_widget.border_color = "#212121"
        self.cbar_widget = cbar_widget
        return [(cbar_widget, dict(col=10, row_span=9))]

    @property
    def name(self):
        return "gplanner graph"

    @property
    def target_file(self):
        return self.graph_data_path

    def construct_plugin(self) -> None:
        super().construct_plugin()
        self.sol_lines = SolutionLine(self.visualiser.visual_parent)
        self.fake_sol_lines = SolutionLine(self.visualiser.visual_parent, offset=200000)
        self.graph_solution_extra_toggle.set(not self.graph_toggle.get())
        self.lines = scene.Line(
            antialias=False, method="gl", parent=self.visualiser.visual_parent, width=3
        )
        self.lines.set_data(pos=DUMMY_LINE, connect=DUMMY_CONNECT, color=DUMMY_COLOUR)
        self.cbar_widget.clim = (np.nan, np.nan)

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

        if self.use_ci:
            _mean, _min, _max = mean_confidence_interval(costs)
        else:
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
