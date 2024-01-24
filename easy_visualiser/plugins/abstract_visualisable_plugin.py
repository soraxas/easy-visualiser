from abc import ABC
from typing import TYPE_CHECKING, Callable, List, Optional, Type

import overrides
from vispy.visuals import Visual

from easy_visualiser.plugin_capability import (
    GuardableMixin,
    IntervalUpdatableMixin,
    PluginState,
)
from easy_visualiser.utils import no_except

if TYPE_CHECKING:
    from easy_visualiser.visualiser import VisualisablePluginNameSpace, Visualiser


class VisualisablePlugin(ABC):
    visualiser: "Visualiser" = None
    name: str
    auto_add_visual_parent: bool = True
    assign_visual_parent_on_init: List[Callable] = []
    __had_set_range: bool = False

    def __init__(
        self,
        name: Optional[str] = None,
        auto_add_visual_parent: bool = True,
    ):
        super().__init__()

        self.state = PluginState.EMPTY
        self.auto_add_visual_parent = auto_add_visual_parent

        if not hasattr(self, "name"):
            if name is None:
                name = self.__class__.__name__
            self.name = name

    def __setattr__(self, key, value):
        # auto add our visualiser's parent as the visual's parent.
        if self.auto_add_visual_parent and isinstance(value, Visual):
            assert hasattr(value, "parent")

            if value.parent is None:
                if self.visualiser is None:
                    # assign it later.
                    self.assign_visual_parent_on_init.append(value)
                else:
                    value.parent = self.visualiser.visual_parent

        return super().__setattr__(key, value)

    def on_initialisation(self, visualiser: "Visualiser"):
        """
        Can use this time to register hooks on visualiser
        :return:
        """
        self.visualiser = visualiser
        # process callback on init.
        for visual in self.assign_visual_parent_on_init:
            visual.parent = self.visualiser.visual_parent
        self.assign_visual_parent_on_init.clear()

    @property
    def other_plugins(self) -> "VisualisablePluginNameSpace":
        return self.visualiser.plugins

    @overrides.final
    def update(self, force=False) -> None:
        """no overriding!"""
        if not isinstance(self, IntervalUpdatableMixin):
            return
        if not force and isinstance(self, GuardableMixin):
            if not self.on_update_guard():
                return

        self.on_update()

    def construct_plugin(self) -> bool:
        self.state = PluginState.ON
        return True

    def set_range(self, *args, **kwargs):
        with no_except.NoMyException(TypeError):
            self.visualiser.view.camera.set_range(*args, **kwargs)
            self.__class__.__had_set_range = True

    @property
    def had_set_range(self) -> bool:
        return self.__class__.__had_set_range

    def __repr__(self) -> str:
        return f"{self.name}<...>"


class VisualisablePluginInitialisationError(Exception):
    def __init__(self, plugin_type: Type[VisualisablePlugin], reason: str = ""):
        self.message = (
            f"Failed to initialise {plugin_type.__name__}"
            f"{f': {reason}' if reason else ''}."
        )
        super().__init__(self.message)
