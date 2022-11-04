from abc import ABC, abstractmethod
import argparse
from types import SimpleNamespace
from typing import Dict, Type, TYPE_CHECKING
from plannerGraphVisualiser.easy_visualiser.plugin_capability import (
    PluginState,
    UpdatableMixin,
    GuardableMixin,
)

if TYPE_CHECKING:
    from plannerGraphVisualiser.easy_visualiser.visualiser import Visualiser


class VisualisablePlugin(ABC):
    def __init__(self, args: argparse.Namespace, name: str = None):
        self.args = args
        self.visualiser: Visualiser = self.args.vis
        self.state = PluginState.EMPTY
        try:
            VisualisablePlugin.__had_set_range
        except AttributeError:
            VisualisablePlugin.__had_set_range = False

        try:
            getattr(self, "name")
        except AttributeError:
            pass
            if name is None:
                name = self.__class__.__name__
            self.name = name

    def on_initialisation_finish(self):
        """
        Can use this time to register hooks on visualiser
        :return:
        """
        pass

    @property
    def other_plugins(self) -> SimpleNamespace:
        return SimpleNamespace(**{p.name: p for p in self.visualiser.plugins})

    def update(self, force=False) -> None:
        """no overriding!"""
        if not force:
            if not isinstance(self, UpdatableMixin):
                return

            if isinstance(self, GuardableMixin):
                if not self.on_update_guard():
                    return

        self.on_update()

    def construct_plugin(self) -> bool:
        self.state = PluginState.ON
        return True

    def set_range(self, *args, **kwargs):
        self.args.view.camera.set_range(*args, **kwargs)
        VisualisablePlugin._had_set_range = True

    @property
    def had_set_range(self) -> bool:
        return VisualisablePlugin.__had_set_range


class VisualisablePluginInitialisationError(Exception):
    def __init__(self, plugin_type: Type[VisualisablePlugin], reason: str = ""):
        self.message = (
            f"Failed to initialise {plugin_type.__name__}"
            f"{f': {reason}' if reason else ''}."
        )
        super().__init__(self.message)
