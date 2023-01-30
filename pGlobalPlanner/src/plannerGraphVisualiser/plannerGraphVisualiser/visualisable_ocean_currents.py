from typing import Dict
from vispy.scene.visuals import Arrow
from vispy import app

import numpy as np
from vispy.color import get_colormap

from plannerGraphVisualiser.easy_visualiser.plugins.abstract_visualisable_plugin import (
    VisualisablePlugin,
)
from .easy_visualiser.plugin_capability import (
    ToggleableMixin,
    CallableAndFileModificationGuardableMixin,
    IntervalUpdatableMixin,
    PluginState,
)
from plannerGraphVisualiser.easy_visualiser.dummy import (
    DUMMY_COLOUR,
    DUMMY_LINE,
    DUMMY_ARROW,
)
from plannerGraphVisualiser.easy_visualiser.modal_control import ModalControl
from .easy_visualiser.key_mapping import Key
from .easy_visualiser.utils import ToggleableBool


class VisualisableOceanCurrent(
    CallableAndFileModificationGuardableMixin,
    ToggleableMixin,
    IntervalUpdatableMixin,
    VisualisablePlugin,
):
    currents = None

    def __init__(
        self,
        ocean_current_toggle: ToggleableBool,
        ocean_current_datapath: str,
        colormap: str = "plasma",
    ):
        super().__init__()
        self.ocean_current_toggle = ocean_current_toggle
        self.ocean_current_datapath = ocean_current_datapath
        self.colormap = colormap
        self.keys = [
            ModalControl(
                "o",
                [
                    ("o", "toggle ocean current", self.__toggle_currents_cb),
                    (
                        "a",
                        "toggle ocean current animate",
                        self.__toggle_currents_animate_cb,
                    ),
                    (
                        Key(["+", "="]),
                        "increase scale",
                        lambda: self.__change_currents_scale_cb(1.5),
                    ),
                    (
                        Key(["-", "_"]),
                        "decrease scale",
                        lambda: self.__change_currents_scale_cb(0.5),
                    ),
                ],
                modal_name="ocean current",
            )
        ]
        self.guarding_callable = lambda: self.ocean_current_toggle
        self.ocean_current_max_scale = 60000
        self.ocean_current_scale = self.ocean_current_max_scale

        self.animate_timer = app.Timer(
            interval=0.01,
            connect=lambda ev: self.update(True),
            iterations=-1,
        )

        self.__choices = slice(None)
        self.__choices_size = None
        self.__last_current_size = None

    def __toggle_currents_cb(self):
        self.ocean_current_toggle.toggle()
        self.toggle()

    def __change_currents_scale_cb(self, scale):
        if self.__choices_size is None:
            self.__choices_size = 1000

        self.__choices_size = int(self.__choices_size * scale)
        if self.__choices_size > self.__last_current_size:
            self.__choices_size = self.__last_current_size
        if self.__choices_size <= 1:
            self.__choices_size = 1

        self.__choices = np.random.choice(self.__last_current_size, self.__choices_size)
        self.on_update()

    def on_update_guard(self) -> bool:
        if not self.ocean_current_toggle:
            return False
        return super().on_update_guard()

    def __toggle_currents_animate_cb(self):
        if not self.ocean_current_toggle:
            return

        if self.animate_timer.running:
            self.animate_timer.stop()
        else:
            self.animate_timer.start()

    @property
    def target_file(self) -> str:
        return self.ocean_current_datapath

    @property
    def name(self):
        return "ocean_currents"

    def construct_plugin(self) -> None:
        super().construct_plugin()
        self.currents = Arrow(
            # pos=DUMMY_LINE,
            # color=DUMMY_COLOUR,
            antialias=True,
            arrow_size=3,
            arrow_type="angle_90",
            parent=self.visualiser.view.scene,
        )

    def __get_data(self) -> Dict:
        currents_data: Dict = np.load(self.target_file, allow_pickle=True).item()

        if self.animate_timer.running:
            self.ocean_current_scale += 500
            if self.ocean_current_scale >= self.ocean_current_max_scale:
                self.ocean_current_scale = 0

        currents_data["z"] = self.other_plugins.zscaler.scaler(currents_data["z"])

        self.__last_current_size = currents_data["x"].shape[0]
        if self.__choices_size is None:
            self.__change_currents_scale_cb(1)

        currents_data["x"] = np.array(currents_data["x"])[self.__choices]
        currents_data["y"] = np.array(currents_data["y"])[self.__choices]
        currents_data["z"] = np.array(currents_data["z"])[self.__choices]
        currents_data["u"] = np.array(currents_data["u"])[self.__choices]
        currents_data["v"] = np.array(currents_data["v"])[self.__choices]

        pos = np.empty([currents_data["x"].shape[0] * 2, 3])
        pos[::2, 0] = currents_data["x"]
        pos[::2, 1] = currents_data["y"]
        pos[::2, 2] = currents_data["z"]

        pos[1::2, 0] = (
            currents_data["x"] + self.ocean_current_scale * currents_data["u"]
        )
        pos[1::2, 1] = (
            currents_data["y"] + self.ocean_current_scale * currents_data["v"]
        )
        pos[1::2, 2] = currents_data[
            "z"
        ]  # + self.ocean_current_scale * currents_data['w']

        cmap = get_colormap(self.colormap)

        norm = np.sqrt(currents_data["u"] ** 2 + currents_data["v"] ** 2)

        norm = (norm - norm.min()) / (norm.max() - norm.min())

        # scale color depending on the maximum scale
        norm = (self.ocean_current_scale / self.ocean_current_max_scale) * norm

        colors = np.empty([currents_data["x"].shape[0] * 2, 4])
        colors[::2, :] = cmap.map(norm)
        colors[1::2, :] = colors[::2, :]

        data = dict(
            pos=pos,
            connect="segments",
            color=colors,
            # width=5,
            # size=.1,
            arrows=np.hstack([pos[::2, ...], pos[1::2, ...]]),
            # arrows=_pos,
            width=5,
            # method='agg',
            arrow_color=colors[::2, ...],
        )
        return data

    def turn_on_plugin(self):
        if not super().turn_on_plugin():
            return False
        _data = self.__get_data()
        arrow_color = _data.pop("arrow_color")
        self.currents.set_data(**_data)
        self.currents.arrow_color = arrow_color
        self.currents.visible = True
        self.animate_timer.start()
        return True

    def turn_off_plugin(self):
        if not super().turn_off_plugin():
            return False
        # self.currents.set_data(
        #     pos=DUMMY_LINE,
        #     color=DUMMY_COLOUR,
        #     arrows=DUMMY_ARROW,
        # )
        # self.currents.arrow_color = DUMMY_COLOUR
        self.currents.visible = False
        self.animate_timer.stop()
        return True

    def on_update(self):
        self.turn_on_plugin()
