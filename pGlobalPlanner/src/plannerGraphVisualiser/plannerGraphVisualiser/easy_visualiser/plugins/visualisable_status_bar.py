from itertools import chain
from tkinter import Widget

from typing import List, Tuple
from vispy import scene

from plannerGraphVisualiser.easy_visualiser.plugins.abstract_visualisable_plugin import (
    VisualisablePlugin,
)

from plannerGraphVisualiser.easy_visualiser.modal_control import ModalState
from plannerGraphVisualiser.easy_visualiser.plugin_capability import (
    ToggleableMixin,
    WidgetsMixin,
    WidgetOption,
)


class VisualisableStatusBar(WidgetsMixin, VisualisablePlugin):
    status_bar: scene.Label

    def on_initialisation_finish(self):
        self.visualiser.hooks.on_initialisation_finish.append(self.update_status)
        self.visualiser.hooks.on_keypress_finish.append(self.update_status)

    def update_status(self):
        if self.visualiser.current_modal.state is not None:
            msg = f">>>>>  {self.visualiser.current_modal.state.modal_name}\n\n"

            msg += "\n".join(
                f"Press [{mapping.key}] to {mapping.description}"
                for mapping in self.visualiser.current_modal.state.mappings
            )

            msg += f"\n\n\n\nPress [{ModalState.quit_key}] to exit current modal"

            self.status_bar.text = msg

        else:
            msg = "~~~~~~~~~~ Directory ~~~~~~~~~\n\n"
            msg += "\n".join(
                "Press [{key}] to {functionality}".format(
                    key=cb.key, functionality=f"control {cb.modal_name}"
                )
                for cb in chain(
                    *(
                        p.keys
                        for p in self.visualiser.plugins
                        if isinstance(p, ToggleableMixin)
                    )
                )
            )

            self.status_bar.text = msg

    def get_constructed_widgets(self) -> List[Tuple[Widget, WidgetOption]]:
        self.status_bar = scene.Label(
            "",
            color="white",
            anchor_x="left",
            anchor_y="bottom",
            pos=[0, 0],
        )
        return [
            (
                self.status_bar,
                WidgetOption(
                    col=0,
                    row=0,
                    row_span=1,
                ),
            )
        ]
