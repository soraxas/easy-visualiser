import enum
import os
from abc import ABC, abstractmethod
import argparse
from typing import Optional, Callable, List, Tuple, Dict


class PluginState(enum.Enum):
    EMPTY = 0
    ON = 1
    OFF = 2


class VisualisablePlugin(ABC):
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.state = PluginState.EMPTY
        if self.construct_plugin():
            self.state = PluginState.OFF

    @property
    @abstractmethod
    def name(self):
        pass

    def register_on_press_hook(
        self,
        key: str,
    ):
        pass

    def update(self) -> None:
        """no overriding!"""
        if not isinstance(self, UpdatableMixin):
            return

        if isinstance(self, GuardableMixin):
            if not self.on_update_guard():
                return

        self.on_update()

    @abstractmethod
    def construct_plugin(self) -> None:
        self.state = PluginState.ON

    @property
    def other_plugins_mapper(self) -> Dict[str, "VisualisablePlugin"]:
        return {p.name: p for p in self.args.vis.plugins}


class ToggleableMixin:
    keys: List[Tuple[str, str, Callable]]
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
        pass


class FileModificationGuardableMixin(GuardableMixin):
    _last_modify_time: Optional[float] = None
    args: argparse.Namespace

    def on_update_guard(self) -> bool:
        if os.path.exists(self.target_file):
            _mtime = os.path.getmtime(self.target_file)
            if self._last_modify_time is None or (self._last_modify_time < _mtime):
                self._last_modify_time = _mtime
                return True
        return False

    @property
    @abstractmethod
    def target_file(self) -> str:
        raise NotImplementedError()


class UpdatableMixin:
    key: str

    @abstractmethod
    def on_update(self) -> None:
        pass
