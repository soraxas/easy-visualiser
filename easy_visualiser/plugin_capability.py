import argparse
import enum
import os
import sys
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple, Union

import numpy as np
from vispy.scene import Widget

if sys.version_info >= (3, 8):
    from typing import Literal  # pylint: disable=no-name-in-module
    from typing import TypedDict, overload
else:
    from typing_extensions import Literal, TypedDict, overload

if TYPE_CHECKING:
    from easy_visualiser.plugins import VisualisablePlugin

    from .key_mapping import Key, Mapping
    from .modal_control import ModalControl


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

    def is_on(self):
        return self is PluginState.ON


class TriggerableMixin:
    __keys: List[Union["ModalControl", "Mapping.MappingRawType"]] = []

    @property
    def keys(self):
        raise ValueError("Not accessible. Use self.add_mapping(...)")

    def add_mapping(
        self,
        mapping: Union["ModalControl", "Mapping.MappingRawType"],
        /,
        *,
        front: bool = False,
    ):
        from .modal_control import ensure_mapping

        mapping = ensure_mapping(mapping)
        if front:
            self.__keys.insert(0, mapping)
        else:
            self.__keys.append(mapping)

    def add_mappings(
        self,
        *mappings: Union["ModalControl", "Mapping.MappingRawType"],
        front: bool = False,
    ):
        if front:
            # reverse the mapping, so that we will add all mappings to the front
            # in the correct order
            mappings = reversed(mappings)
        for mapping in mappings:
            self.add_mapping(mapping, front=front)

    def get_root_mappings(self) -> List["Mapping"]:
        from .modal_control import ModalControl

        return [item for item in self.__keys if not isinstance(item, ModalControl)]

    def get_modal_control(self) -> List["ModalControl"]:
        from .modal_control import ModalControl

        return [item for item in self.__keys if isinstance(item, ModalControl)]

    def replace_mappings_with(
        self,
        *mappings: Union["ModalControl", "Mapping.MappingRawType"],
        front: bool = False,
    ):
        self.__keys.clear()
        self.add_mappings(*mappings, front=front)

    def get_copied_mapping_list(self):
        return list(self.__keys)


class ZoomableMixin(TriggerableMixin):
    __bounds = None

    def __init__(self):
        super().__init__()
        from .key_mapping import Key, Mapping

        self.add_mapping(
            Mapping(
                Key(["z"]),
                f"zoom to [{self.__class__.__name__}]",
                self.__zoom_cb,
            ),
            front=True,
        )

    def __zoom_cb(self):
        if self.__bounds is None:
            self.set_range()
        else:
            self.set_range(*self.__bounds)

    def set_bounds(self, bounds: np.ndarray):
        self.__bounds = bounds


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

        self.visualiser.hooks.on_plugins_state_change.on_event()
        return True

    def construct_plugin(self) -> bool:
        if not super().construct_plugin():
            return False
        self.turn_on_plugin()
        return True

    @abstractmethod
    def turn_on_plugin(self) -> bool:
        self.state = PluginState.ON

        self.visualiser.hooks.on_plugins_state_change.on_event()
        return True

    def get_root_mappings(self) -> List["Mapping"]:
        if self.state.is_built():
            return super().get_root_mappings()
        return []

    def get_modal_control(self) -> List["ModalControl"]:
        if self.state.is_built():
            return super().get_modal_control()
        return []

    def __enter__(self):
        self.turn_on_plugin()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.turn_off_plugin()


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

    @abstractmethod
    def turn_on_plugin(self) -> bool:
        if not os.path.exists(self.target_file):
            return False
        return super().turn_on_plugin()


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
