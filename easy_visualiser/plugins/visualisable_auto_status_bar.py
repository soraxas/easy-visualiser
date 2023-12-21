from vispy import scene

from easy_visualiser.plugin_capability import WidgetOption, WidgetsMixin
from easy_visualiser.plugins import VisualisableMessageBoard


class VisualisableAutoStatusBar(VisualisableMessageBoard):
    def on_initialisation(self, *args, **kwargs):
        super().on_initialisation(*args, **kwargs)
        self.visualiser.hooks.on_initialisation_finish.add_hook(self.update_status)
        self.visualiser.hooks.on_keypress_finish.add_hook(self.update_status)

    def update_status(self):
        self.set_message(self.visualiser.current_modal.state.to_help_msg())
