from easy_visualiser.plugin_capability import IntervalUpdatableMixin
from easy_visualiser.plugins import VisualisablePrincipleAxis
from easy_visualiser.plugins.ext.visualisable_bathymetry import VisualisableBathy


class VisualisablePrincipleAxisWithBathyOffset(
    IntervalUpdatableMixin, VisualisablePrincipleAxis
):
    def on_update(self) -> None:
        if self.other_plugins.bathymetry.last_min_max_pos is not None:
            offset = self.other_plugins.bathymetry.last_min_max_pos[0, :].copy()
            # offset[2] -= self.args.principle_axis_z_offset
            self._set_origin(origin=offset)
