from .easy_visualiser.plugin_capability import UpdatableMixin
from .easy_visualiser.plugins.visualisable_axis import VisualisablePrincipleAxis
from .visualisable_bathymetry import VisualisableBathy


class VisualisablePrincipleAxisWithBathyOffset(
    UpdatableMixin, VisualisablePrincipleAxis
):
    def on_update(self) -> None:
        if self.other_plugins.bathymetry.last_min_pos is not None:
            offset = self.other_plugins.bathymetry.last_min_pos.copy()
            offset[2] -= self.args.principle_axis_z_offset
            self._set_origin(origin=offset)
