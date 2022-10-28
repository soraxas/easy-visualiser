import enum
import os
from abc import ABC, abstractmethod
import argparse
from typing import Optional, Callable, List, Tuple, Dict, Type

from plannerGraphVisualiser.modal_control import ModalControl


class PluginState(enum.Enum):
    EMPTY = 0
    ON = 1
    OFF = 2


class VisualisablePlugin(ABC):
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.state = PluginState.EMPTY
        try:
            VisualisablePlugin.__had_set_range
        except AttributeError:
            VisualisablePlugin.__had_set_range = False

        if self.construct_plugin():
            self.state = PluginState.OFF

    @property
    @abstractmethod
    def name(self):
        pass

    def update(self, force=False) -> None:
        """no overriding!"""
        if not force:
            if not isinstance(self, UpdatableMixin):
                return

            if isinstance(self, GuardableMixin):
                if not self.on_update_guard():
                    return

        self.on_update()

    def construct_plugin(self) -> None:
        self.state = PluginState.ON

    @property
    def other_plugins_mapper(self) -> Dict[str, "VisualisablePlugin"]:
        return {p.name: p for p in self.args.vis.plugins}

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


class ToggleableMixin:
    keys: List[ModalControl]
    state: PluginState
    construct_plugin: Callable

    def toggle(self) -> None:
        if self.state is PluginState.EMPTY:
            self.construct_plugin()
        elif self.state is PluginState.ON:
            self.turn_off_plugin()
        else:
            self.turn_on_plugin()

    @abstractmethod
    def turn_off_plugin(self):
        self.state = PluginState.OFF

    @abstractmethod
    def turn_on_plugin(self):
        self.state = PluginState.ON


class GuardableMixin:
    @abstractmethod
    def on_update_guard(self) -> bool:
        return True


class FileModificationGuardableMixin(GuardableMixin):
    _last_modify_time: Optional[float] = None
    args: argparse.Namespace

    def on_update_guard(self) -> bool:
        if os.path.exists(self.target_file):
            _mtime = os.path.getmtime(self.target_file)
            if self._last_modify_time is None or (self._last_modify_time < _mtime):
                self._last_modify_time = _mtime
                return super().on_update_guard()
        return False

    @property
    @abstractmethod
    def target_file(self) -> str:
        raise NotImplementedError()


class CallableAndFileModificationGuardableMixin(FileModificationGuardableMixin):
    guarding_callable: Callable

    def on_update_guard(self) -> bool:
        if not self.guarding_callable():
            return False
        return super().on_update_guard()


class UpdatableMixin:
    @abstractmethod
    def on_update(self) -> None:
        pass
