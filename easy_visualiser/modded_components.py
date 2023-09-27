from collections import defaultdict
from copy import copy
from typing import overload

import numpy as np
from vispy.plot import PlotWidget
from vispy.scene import PanZoomCamera, visuals


class SyncedPanZoomCamera(PanZoomCamera):
    """A pan zoom camera that sync view box"""

    __sync_registry = defaultdict(list)

    def __init__(
        self,
        sync_id: str,
        sync_xaxis: bool = True,
        sync_yaxis: bool = True,
        *args,
        **kwargs,
    ):
        self.__sync_id = sync_id
        self.__sync_xaxis = sync_xaxis
        self.__sync_yaxis = sync_yaxis
        container = self.__class__.__sync_registry[self.__sync_id]
        container.append(self)
        super().__init__(*args, **kwargs)

    def view_changed(self):
        super().view_changed()
        if self._viewbox is None:
            return

        for instance in self.__class__.__sync_registry[self.__sync_id]:
            if instance is self:
                continue

            new_rect = copy(instance.rect)
            if self.__sync_xaxis:
                new_rect.left = self.rect.left
                new_rect.right = self.rect.right
            if self.__sync_yaxis:
                new_rect.top = self.rect.top
                new_rect.bottom = self.rect.bottom
            instance.rect = new_rect


class PlotWidgetWithSyncedCamera(PlotWidget):
    """A modified plot widget that fixes axes not syncing due to not being linked."""

    def __init__(self, custom_camera: SyncedPanZoomCamera, *args, **kwargs):
        self.__camera = custom_camera
        super().__init__(*args, **kwargs)

    def _configure_2d(self, *args, **kwargs):
        super()._configure_2d(*args, **kwargs)
        self.view.camera = self.__camera
        self.camera = self.view.camera

        # ### hacks to force re-link
        _v = self.grid.add_view()
        self.xaxis.link_view(_v)
        self.yaxis.link_view(_v)
        _v.parent = None
        _v.view = None
        #
        self.xaxis.link_view(self.view)
        self.yaxis.link_view(self.view)


class LockedPanZoomCamera(PanZoomCamera):
    """PanZoomCamera that do not react to mouse event"""

    def viewbox_mouse_event(self, event):
        return


class MarkerWithModifiablePos(visuals.Markers):
    """
    This visual marker can speed-up / avoid overhead from set_data via only
    updating the necessary components.
    """

    _had_set_data = False

    @overload
    def __init__(
        self,
        symbol="o",
        scaling=False,
        alpha=1,
        antialias=1,
        spherical=False,
        light_color="white",
        light_position=(1, -1, 1),
        light_ambient=0.3,
        **kwargs,
    ):
        ...

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @overload
    def set_data(
        self,
        pos=None,
        size=10.0,
        edge_width=1.0,
        edge_width_rel=None,
        edge_color="black",
        face_color="white",
        symbol=None,
        scaling=None,
    ):
        ...

    def set_data(self, *args, **kwargs):
        super().set_data(*args, **kwargs)
        self._had_set_data = True

    @property
    def had_set_data(self) -> bool:
        return self._had_set_data

    def num_points(self):
        if self._data is None:
            return 0
        return self._data["a_position"].shape[0]

    def update_data(
        self,
        *,
        pos: np.ndarray = None,
        colors: np.ndarray = None,
        size: float = None,
    ):
        self.__update_guard()
        if pos is not None:
            self._data["a_position"][:, : pos.shape[1]] = pos
        if colors is not None:
            self._data["a_bg_color"][:] = colors
        if size is not None:
            self._data["a_size"] = size
        self.__update()

    def __update_guard(self):
        """Must have an initial set_data before first usage"""
        if not self.had_set_data:
            raise RuntimeError("marker data had not been set yet!")

    def __update(self):
        """Trigger update on opengl"""
        self._vbo.set_data(self._data)
        # self.shared_program.bind(self.points._vbo)
        self.update()
