from typing import Any, Dict, Optional

from vispy import scene

from easy_visualiser.plugin_capability import WidgetOption, WidgetsMixin
from easy_visualiser.plugins import VisualisablePlugin


class VisualisableMessageBoard(WidgetsMixin, VisualisablePlugin):
    msg_board: scene.Label

    def __init__(self, widget_option: Optional[WidgetOption] = None):
        super().__init__()
        if widget_option is None:
            widget_option = WidgetOption(
                col=0,
                row=0,
                row_span=1,
            )
        self.widget_option = widget_option

    def set_message(self, message: str):
        self.msg_board.text = message

    def get_constructed_widgets(self):
        # noinspection PyTypeChecker
        self.msg_board = scene.Label(
            "",
            color="white",
            anchor_x="left",
            anchor_y="bottom",
            pos=[0, 0],
        )
        return (
            self.msg_board,
            self.widget_option,
        )


class VisualisableStatusBar(VisualisableMessageBoard):
    lines: Dict[Any, str]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lines = {}

    def update_status(self):
        self.set_message("\n".join(self.lines.values()))

    def add_line(self, token: Any, line: str):
        self.lines[token] = line
        self.update_status()

    def remove_line(self, token: Any) -> str:
        self.lines.pop(token, None)
        self.update_status()

    def clear_lines(self):
        self.lines.clear()
        self.update_status()


class VisualisableAutoStatusBar(VisualisableMessageBoard):
    def on_initialisation(self, *args, **kwargs):
        super().on_initialisation(*args, **kwargs)
        self.visualiser.hooks.on_initialisation_finish.add_hook(self.update_status)
        self.visualiser.hooks.on_keypress_finish.add_hook(self.update_status)

    def update_status(self):
        self.set_message(self.visualiser.current_modal.state.to_help_msg())
