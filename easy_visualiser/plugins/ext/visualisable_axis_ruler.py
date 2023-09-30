from collections import namedtuple
from typing import List

import numpy as np
from vispy.scene import XYZAxis
from vispy.util import keys

from easy_visualiser.helpers import (
    compute_delta_vec_from_canvas_to_visual_coordinate,
    visual_coordinate_to_pixel_coordinate,
)
from easy_visualiser.key_mapping import Mapping, MappingOnlyDisplayText
from easy_visualiser.plugin_capability import ToggleableMixin
from easy_visualiser.plugins import VisualisablePlugin
from easy_visualiser.utils import boolean_to_onoff
from easy_visualiser.visuals.ruler import RulerScale

RulerVisualsMapping = namedtuple("RulerVisualsMapping", "dim bound_slice")


class VisualisableAxisRuler(ToggleableMixin, VisualisablePlugin):
    axis_visual: XYZAxis
    _axis_pos = None
    ruler_visuals: List[RulerScale]

    def __init__(
        self,
        clip_to_bounding_box: bool = False,
    ):
        super().__init__()
        # our target origin in 3d world space
        self.target_origin_visual = np.array([0.0, 0.0, 0.0])
        # our target origin in 2d pixel space
        self.target_pos_canvas = np.array([0, 0])
        self.__initialised = False
        self.clip_to_bounding_box = clip_to_bounding_box

        self.update_pos_timer = app.Timer(
            interval=0.01,
            connect=lambda _: self.move_element_origin_to_pos(),
            start=True,
        )
        self.__ruler_visuals_mapping = [
            RulerVisualsMapping(0, np.s_[0, 0]),
            RulerVisualsMapping(0, np.s_[1, 0]),
            RulerVisualsMapping(1, np.s_[0, 1]),
            RulerVisualsMapping(1, np.s_[1, 1]),
            RulerVisualsMapping(2, np.s_[0, 2]),
            RulerVisualsMapping(2, np.s_[1, 2]),
        ]
        self.add_mappings(
            Mapping(
                "m",
                lambda: f"toggle measurer [{boolean_to_onoff(self.state.is_on())}] origin[{self.target_origin_visual}]",
                self.toggle,
            ),
            MappingOnlyDisplayText(
                "    Note: Hold <Alt> key to drag the measurer origin"
            ),
        )

    def turn_on_plugin(self):
        if not super().turn_on_plugin():
            return False
        # reattach all rulers
        for visual in self.ruler_visuals:
            visual.parent = self.visualiser.visual_parent
        return True

    def turn_off_plugin(self):
        if not super().turn_off_plugin():
            return False
        # deattach all rulers
        for visual in self.ruler_visuals:
            visual.parent = None
        self.update_pos_timer.stop()
        return True

    @property
    def name(self):
        return "axis_ruler"

    def construct_plugin(self) -> None:
        super().construct_plugin()

        self.ruler_visuals = [
            RulerScale(
                color=(0.85, 0.85, 0.85, 1),
                parent=self.visualiser.visual_parent,
                tick_length=10000,
                tick_gap=(200 if mapping.dim == 2 else 10000),
                antialias=True,
                tick_label_formatter=(
                    (lambda num: f"{num:.0f} m")
                    if mapping.dim == 2
                    else (lambda num: f"{num // 1000:.0f} km" if num else "")
                ),
                font_size=10000000,
                scale_factor=(
                    1 / self.other_plugins.zscaler.scaler.scale_factor
                    if mapping.dim == 2
                    else 1
                ),
            )
            for mapping in self.__ruler_visuals_mapping
        ]
        self.move_element_origin_to_pos()

        @self.visualiser.canvas.connect
        def on_mouse_move(event):
            if keys.ALT in event.modifiers:
                self.target_pos_canvas = event.pos
                self.update_pos_timer.start()
            else:
                self.update_pos_timer.stop()

        @self.visualiser.canvas.connect
        def on_key_press(event):
            if keys.ALT is event.key:
                self.update_pos_timer.start()

        @self.visualiser.canvas.connect
        def on_key_release(event):
            if keys.ALT is event.key:
                self.update_pos_timer.stop()

    @property
    def origin_visual_element(self):
        """By default, we will just the first component as our origin element."""
        return self.ruler_visuals[0]

    def move_element_origin_to_pos(self, factor=35):
        """
        Move the axis origin to whever the mous is pointing.
        """
        if any(
            stuff is None
            for stuff in (
                self.target_pos_canvas,
                self.other_plugins.bathymetry.last_min_max_pos,
            )
        ):
            return

        # get current origin
        if self.origin_visual_element.start_end_pos is None:
            _origin = np.zeros(3)
        else:
            _origin = self.origin_visual_element.start_end_pos[0]
        current_canvas_pos = visual_coordinate_to_pixel_coordinate(
            self.origin_visual_element, _origin
        )[:2]

        delta = compute_delta_vec_from_canvas_to_visual_coordinate(
            self.visualiser.view.camera, (self.target_pos_canvas - current_canvas_pos)
        )
        new_target_origin = self.target_origin_visual + factor * delta

        if self.clip_to_bounding_box:
            # clip new pos to boundary box
            new_target_origin = np.clip(
                new_target_origin,
                self.other_plugins.bathymetry.last_min_max_pos[0],
                self.other_plugins.bathymetry.last_min_max_pos[1],
            )

        for i, ruler_visual in enumerate(self.ruler_visuals):
            other_end = new_target_origin.copy()
            # map from ruler visuals into the corresponding slice to index bounds
            mapping = self.__ruler_visuals_mapping[i]
            other_end[mapping.dim] = self.other_plugins.bathymetry.last_min_max_pos[
                mapping.bound_slice
            ]
            ruler_visual.set_data(
                start_end_pos=(new_target_origin, other_end),
                width=5,
            )

        self.target_origin_visual[:] = new_target_origin

        if not self.__initialised:
            self.__initialised = True
            self.update_pos_timer.stop()

        # how far away are we from our desire pos?
        if np.linalg.norm(self.target_pos_canvas - current_canvas_pos) <= 1:
            self.update_pos_timer.stop()
