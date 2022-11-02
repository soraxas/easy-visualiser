import numpy as np
from plannerGraphVisualiser import get_latest_pdata, mean_confidence_interval
from vispy import scene

from plannerGraphVisualiser.easy_visualiser.plugins.abstract_visualisable_plugin import (
    VisualisablePlugin,
)
from .easy_visualiser.plugin_capability import (
    ToggleableMixin,
    UpdatableMixin,
    CallableAndFileModificationGuardableMixin,
    WidgetsMixin,
)
from plannerGraphVisualiser.easy_visualiser.dummy import (
    DUMMY_LINE,
    DUMMY_CONNECT,
    DUMMY_COLOUR,
)
from plannerGraphVisualiser.easy_visualiser.modal_control import ModalControl


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
                _path[:, -1] -= self.offset
        self.line_visual.set_data(pos=_path)


class VisualisablePlannerGraph(
    CallableAndFileModificationGuardableMixin,
    WidgetsMixin,
    ToggleableMixin,
    UpdatableMixin,
    VisualisablePlugin,
):
    lines = None
    cbar_widget: scene.ColorBarWidget
    __had_set_range: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.guarding_callable = lambda: True

        self.keys = [
            ModalControl(
                "p",
                [
                    ("g", "toggle planner graph", self.__toggle_graph_cb),
                    ("s", "toggle planner solution", self.__toggle_solution_cb),
                    ("c", "switch cost index", self.__switch_cost_cb),
                ],
                modal_name="global planner graph",
            )
        ]
        self.sol_lines = SolutionLine(self.args.view.scene)
        # if self.args.extra_sol:
        self.fake_sol_lines = SolutionLine(self.args.view.scene, offset=200000)

    def __toggle_graph_cb(self):
        self.args.graph = not self.args.graph
        self.args.extra_sol = not self.args.graph
        self.toggle()

    def __toggle_solution_cb(self):
        self.args.graph_solution = not self.args.graph_solution
        self.on_update()

    def get_constructed_widgets(self):
        cbar_widget = scene.ColorBarWidget(
            label="Cost",
            clim=(0, 99),
            cmap=self.args.colormap,
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
        return self.args.datapath

    def construct_plugin(self) -> None:
        super().construct_plugin()
        self.args.extra_sol = not self.args.graph
        self.lines = scene.Line(
            antialias=False, method="gl", parent=self.args.view.scene, width=3
        )
        self.lines.set_data(pos=DUMMY_LINE, connect=DUMMY_CONNECT, color=DUMMY_COLOUR)
        self.cbar_widget.clim = (np.nan, np.nan)

    def __switch_cost_cb(self) -> None:
        if self.args.cost_index is None:
            self.args.cost_index = 0
        else:
            self.args.cost_index += 1
        self._last_modify_time = None
        self.update()

    def __construct_graph(self, pos, edges, costs) -> None:
        #################################################
        #################################################

        if self.args.use_ci:
            _mean, _min, _max = mean_confidence_interval(costs)
        else:
            _min = costs.min()
            _max = costs.max()

        _min = 0
        if self.args.min is not None:
            _min = self.args.min
        if self.args.max is not None:
            _max = self.args.max

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

        colors = self.args.colormap.map(costs)  # [:-2]

        self.lines.set_data(pos=pos, connect=edges, color=colors)
        self.cbar_widget.clim = (_min, _max)

    def __construct_solution(self, solution_path) -> None:
        if not self.args.graph_solution:
            solution_path = []
        self.sol_lines.set_path(solution_path)
        if self.args.extra_sol and self.args.graph:
            fake_solution_path = solution_path.copy()
            self.fake_sol_lines.set_path(fake_solution_path)
        else:
            self.fake_sol_lines.set_path([])

    def turn_on_plugin(self):
        super().turn_on_plugin()
        pos, edges, solution_path, costs = get_latest_pdata(self.args)

        if self.args.graph:
            self.__construct_graph(pos, edges, costs)
        self.__construct_solution(solution_path)

    def turn_off_plugin(self):
        super().turn_off_plugin()
        self.lines.set_data(pos=DUMMY_LINE, connect=DUMMY_CONNECT, color=DUMMY_COLOUR)
        self.cbar_widget.clim = (np.nan, np.nan)

        self.fake_sol_lines.set_path([])

    def on_update(self):
        self.turn_on_plugin()
        if not self.had_set_range:
            self.set_range()
