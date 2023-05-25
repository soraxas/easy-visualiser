from typing import Optional
from vispy import scene

from plannerGraphVisualiser.easy_visualiser.plugins.abstract_visualisable_plugin import (
    VisualisablePlugin,
)

from plannerGraphVisualiser.easy_visualiser.plugin_capability import (
    WidgetsMixin,
    WidgetOption,
)


class VisualisableStatusBar(WidgetsMixin, VisualisablePlugin):
    status_bar: scene.Label

    def __init__(self, widget_option: Optional[WidgetOption] = None):
        super().__init__()
        if widget_option is None:
            widget_option = WidgetOption(
                col=0,
                row=0,
                row_span=1,
            )
        self.widget_option = widget_option

    def on_initialisation(self, *args, **kwargs):
        super().on_initialisation(*args, **kwargs)
        self.visualiser.hooks.on_initialisation_finish.append(self.update_status)
        self.visualiser.hooks.on_keypress_finish.append(self.update_status)

    def update_status(self):
        self.status_bar.text = self.visualiser.current_modal.state.to_help_msg()

    def get_constructed_widgets(self):
        # noinspection PyTypeChecker
        self.status_bar = scene.Label(
            "",
            color="white",
            anchor_x="left",
            anchor_y="bottom",
            pos=[0, 0],
        )
        return (
            self.status_bar,
            self.widget_option,
        )
