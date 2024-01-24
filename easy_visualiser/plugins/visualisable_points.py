import numpy as np

from easy_visualiser.key_mapping import Key, Mapping, MappingOnlyDisplayText
from easy_visualiser.modal_control import ModalControl
from easy_visualiser.modded_components import MarkerWithModifiablePos
from easy_visualiser.plugin_capability import TriggerableMixin
from easy_visualiser.plugins import VisualisablePlugin
from easy_visualiser.utils import ScalableFloat
from easy_visualiser.utils.dummy import DUMMY_POINTS


class VisualisablePoints(TriggerableMixin, VisualisablePlugin):
    """
    Visualise 3D points
    """

    points_visual: MarkerWithModifiablePos

    def __init__(self, points: np.ndarray = np.zeros([0, 3]), **kwargs):
        super().__init__(**kwargs)
        self._marker_scale = ScalableFloat(1, upper_bound=50)
        self._antialias = ScalableFloat(0.25, upper_bound=10)
        self._cached_plotting_kwargs = dict()

        # self.add_mappings(
        #     ModalControl(
        #         "m",
        #         [
        #             MappingOnlyDisplayText(
        #                 lambda: f"marker size: {float(self._marker_scale):.2f}"
        #             ),
        #             Mapping(
        #                 Key.Plus,
        #                 "Increase marker size",
        #                 lambda: self._marker_scale.scale(1.25)
        #                 and self.points_visual.update_data(
        #                     size=float(self._marker_scale)
        #                 ),
        #             ),
        #             Mapping(
        #                 Key.Minus,
        #                 "Decrease marker size",
        #                 lambda: self._marker_scale.scale(1 / 1.25)
        #                 and self.points_visual.update_data(
        #                     size=float(self._marker_scale)
        #                 ),
        #             ),
        #         ],
        #         "Marker",
        #     ),
        #     ModalControl(
        #         "a",
        #         [
        #             MappingOnlyDisplayText(
        #                 lambda: f"antialias: {float(self._antialias):.4f}"
        #             ),
        #             Mapping(
        #                 Key.Plus,
        #                 "Increase antialias",
        #                 lambda: self._antialias.scale(1.25)
        #                 and self.set_antialias(self._antialias),
        #             ),
        #             Mapping(
        #                 Key.Minus,
        #                 "Decrease antialias",
        #                 lambda: self._antialias.scale(1 / 1.25)
        #                 and self.set_antialias(self._antialias),
        #             ),
        #         ],
        #         "Anti-alias",
        #     ),
        #     Mapping("z", "reset zoom", lambda: self.set_range()),
        # )
        self.point_data = points

    def set_antialias(self, value):
        self._antialias.set(value)
        self.points_visual.antialias = value

    def construct_plugin(
        self,
        **kwargs,
    ) -> bool:
        super().construct_plugin()
        self.points_visual = MarkerWithModifiablePos(
            parent=self.visualiser.visual_parent,
            antialias=float(self._antialias),
        )
        self._antialias.set(self.points_visual.antialias)
        self.visualiser.grid.add_widget(col=4, row=4)

        default_kwargs = dict(
            edge_width=0,
            face_color="w",
            size=1,
            symbol="o",
        )
        default_kwargs.update(kwargs)

        self.set_points(self.point_data, **default_kwargs)
        return True

    def _reload_pos_data(self, point_data: np.ndarray):
        self.points_visual.update_data(pos=point_data)

    def set_points(self, pos: np.ndarray, *args, **kwargs):
        assert len(pos.shape) == 2
        if pos.shape[0] <= 0:
            return

        kwargs["pos"] = pos

        # self._cached_plotting_kwargs != kwargs
        if self.points_visual.num_points() == pos.shape[0]:
            # self._reload_pos_data(pos)
            # reload with new location
            self.points_visual.update_data(*args, **kwargs)
            self._cached_plotting_kwargs = dict(kwargs)
        else:
            # set new data, as the shape is different
            self.points_visual.set_data(*args, **kwargs)

        if not self.had_set_range:
            self.set_range()
