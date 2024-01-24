from abc import ABC
from typing import TYPE_CHECKING, Iterable, Type, Union

from .plugin_capability import (
    PluginState,
    ToggleableMixin,
    TriggerableMixin,
    WidgetsMixin,
)
from .plugins import VisualisablePlugin

if TYPE_CHECKING:
    from easy_visualiser.visualiser import VisualisablePluginNameSpace, Visualiser


class VisualiserMiscsMixin(ABC):
    def get_existing_or_construct(
        self: "Visualiser",
        *args,
        name: str = None,
        plugin_type: Type["VisualisablePlugin"] = None,
        **kwargs,
    ) -> VisualisablePlugin:
        if plugin_type is None:
            raise ValueError("Argument 'plugin_type' must be provided.")
        name = name or f"_default__{plugin_type.__name__}"

        if name not in self.plugins:
            self.register_plugin(plugin_type(*args, **kwargs), name=name)
        return self.plugins[name]


class VisualiserEasyAccesserMixin(ABC):
    @property
    def initialised(
        self: "Visualiser",
    ):
        return self._registered_plugins_mappings is not None

    @property
    def triggerable_plugins(
        self,
    ) -> Iterable[Union[VisualisablePlugin, TriggerableMixin]]:
        yield from (p for p in self.active_plugins if isinstance(p, TriggerableMixin))

    @property
    def plugins(self) -> "VisualisablePluginNameSpace":
        if not self.initialised:
            self.initialise()
            # raise RuntimeError("Visualiser has not been initialised yet!")
        return self._registered_plugins_mappings

    @property
    def active_plugins(self) -> Iterable[VisualisablePlugin]:
        for p in self.plugins:
            if isinstance(p, ToggleableMixin) and p.state is PluginState.OFF:
                continue
            yield p

    @property
    def visual_parent(
        self: "Visualiser",
    ):
        """An easy way to reference the parent of all visual elements."""
        return self.view.scene
