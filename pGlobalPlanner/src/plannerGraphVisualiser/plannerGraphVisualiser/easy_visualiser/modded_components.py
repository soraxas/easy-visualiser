from collections import defaultdict
from copy import copy

from vispy.plot import PlotWidget
from vispy.scene import PanZoomCamera


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

        # self.view.scene.transform.changed.connect(lambda ev: rienst)

    def view_changed(self):
        super().view_changed()
        if self._viewbox is None:
            return

        # ic(self.__class__.__sync_registry[self.__sync_id])
        for instance in self.__class__.__sync_registry[self.__sync_id]:
            # ic(self.rect, instance.rect)
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
