import enum
import os
from abc import ABC, abstractmethod
import argparse
from typing import Optional, Callable, List, Dict, Type, Tuple, TYPE_CHECKING, Union
import sys
from vispy.scene import Widget

if sys.version_info >= (3, 8):
    from typing import TypedDict, Literal, overload  # pylint: disable=no-name-in-module
else:
    from typing_extensions import TypedDict, Literal, overload

if TYPE_CHECKING:
    from .modal_control import ModalControl
    from .key_mapping import Mapping


class PluginState(enum.Enum):
    EMPTY = 0
    ON = 1
    OFF = 2

    def __bool__(self):
        raise ValueError("Deprecated. Use the dedicated function to test for state.")

    def is_built(self):
        return self in (PluginState.ON, PluginState.OFF)

    def is_off(self):
        return self is PluginState.OFF


class TriggerableMixin:
    keys: List[Union["ModalControl", "Mapping.MappingRawType"]]

    def get_root_mappings(self) -> List["Mapping"]:
        from .modal_control import ModalControl

        return [item for item in self.keys if not isinstance(item, ModalControl)]

    def get_modal_control(self) -> List["ModalControl"]:
        from .modal_control import ModalControl

        return [item for item in self.keys if isinstance(item, ModalControl)]


class ToggleableMixin(TriggerableMixin):
    state: PluginState
    construct_plugin: Callable

    def toggle(self):
        if self.state is PluginState.EMPTY:
            self.construct_plugin()
        elif self.state is PluginState.ON:
            self.turn_off_plugin()
        else:
            self.turn_on_plugin()

    @abstractmethod
    def turn_off_plugin(self) -> bool:
        self.state = PluginState.OFF
        return True

    @abstractmethod
    def turn_on_plugin(self) -> bool:
        if isinstance(self, FileModificationGuardableMixin):
            if not os.path.exists(self.target_file):
                return False
        self.state = PluginState.ON
        return True

    def get_root_mappings(self) -> List["Mapping"]:
        if self.state.is_built():
            return super().get_root_mappings()
        return []

    def get_modal_control(self) -> List["ModalControl"]:
        if self.state.is_built():
            return super().get_modal_control()
        return []


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


class CallableAndFileModificationGuardableMixin(FileModificationGuardableMixin, ABC):
    guarding_callable: Callable

    def on_update_guard(self) -> bool:
        if not self.guarding_callable():
            return False
        return super().on_update_guard()


class IntervalUpdatableMixin:
    @abstractmethod
    def on_update(self) -> None:
        pass


class WidgetOption(TypedDict, total=False):
    widget: Widget
    row: int
    col: int
    row_span: int
    col_span: int


OneWidgetData = Union[Widget, Tuple[Widget, WidgetOption]]


class WidgetsMixin:
    @abstractmethod
    def get_constructed_widgets(self) -> Union[OneWidgetData, List[OneWidgetData]]:
        pass
