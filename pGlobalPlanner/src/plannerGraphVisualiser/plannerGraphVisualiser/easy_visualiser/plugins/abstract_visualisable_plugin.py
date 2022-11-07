from abc import ABC, abstractmethod
from types import SimpleNamespace
from typing import Dict, Type, TYPE_CHECKING
from plannerGraphVisualiser.easy_visualiser.plugin_capability import (
    PluginState,
    IntervalUpdatableMixin,
    GuardableMixin,
)

if TYPE_CHECKING:
    from plannerGraphVisualiser.easy_visualiser.visualiser import Visualiser


class VisualisablePlugin(ABC):
    visualiser: "Visualiser"
    __had_set_range: bool = False

    def __init__(self, name: str = None):
        self.state = PluginState.EMPTY

        try:
            getattr(self, "name")
        except AttributeError:
            pass
            if name is None:
                name = self.__class__.__name__
            self.name = name

    def on_initialisation(self, visualiser: "Visualiser"):
        """
        Can use this time to register hooks on visualiser
        :return:
        """
        self.visualiser = visualiser

    @property
    def other_plugins(self) -> SimpleNamespace:
        return self.visualiser.registered_plugins_mappings

    def update(self, force=False) -> None:
        """no overriding!"""
        if not force:
            if not isinstance(self, IntervalUpdatableMixin):
                return

            if isinstance(self, GuardableMixin):
                if not self.on_update_guard():
                    return

        self.on_update()

    def construct_plugin(self) -> bool:
        self.state = PluginState.ON
        return True

    def set_range(self, *args, **kwargs):
        self.visualiser.view.camera.set_range(*args, **kwargs)
        self.__class__.__had_set_range = True

    @property
    def had_set_range(self) -> bool:
        return self.__class__.__had_set_range


class VisualisablePluginInitialisationError(Exception):
    def __init__(self, plugin_type: Type[VisualisablePlugin], reason: str = ""):
        self.message = (
            f"Failed to initialise {plugin_type.__name__}"
            f"{f': {reason}' if reason else ''}."
        )
        super().__init__(self.message)
