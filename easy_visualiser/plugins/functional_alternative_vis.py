from typing import Callable

from easy_visualiser.key_mapping import Mapping
from easy_visualiser.plugin_capability import TriggerableMixin
from easy_visualiser.plugins import VisualisablePlugin


class AlternativeVisTrigger(TriggerableMixin, VisualisablePlugin):
    callbackType = Callable[["AlternativeVisTrigger"], None]

    def __init__(self, construct_callback: callbackType, toggle_callback: callbackType):
        super().__init__()
        self.add_mapping(Mapping("t", "toggle", self.__toggle))
        self.construct_callback = construct_callback
        self.toggle_callback = toggle_callback

    def construct_plugin(self):
        try:
            self.construct_callback(self)
        except Exception as e:
            print(e)

    def __toggle(self):
        self.toggle_callback(self)
