import enum
import os
from abc import ABC, abstractmethod
import argparse
from typing import Optional, Callable, List, Dict, Type, Tuple
import sys
from vispy.scene import Widget

from .modal_control import ModalControl

if sys.version_info >= (3, 8):
    from typing import TypedDict, Literal, overload  # pylint: disable=no-name-in-module
else:
    from typing_extensions import TypedDict, Literal, overload


class PluginState(enum.Enum):
    EMPTY = 0
    ON = 1
    OFF = 2


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


class WidgetOption(TypedDict, total=False):
    widget: Widget
    row: int
    col: int
    row_span: int
    col_span: int


class WidgetsMixin:
    @abstractmethod
    def get_constructed_widgets(self) -> List[Tuple[Widget, WidgetOption]]:
        pass
