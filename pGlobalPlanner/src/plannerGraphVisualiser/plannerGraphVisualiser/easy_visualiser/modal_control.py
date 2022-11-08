import enum
from abc import ABC, abstractmethod
from itertools import chain
from typing import Callable, Tuple, List, Union, TYPE_CHECKING, Iterable

from plannerGraphVisualiser.easy_visualiser.plugin_capability import (
    ToggleableMixin,
)

if TYPE_CHECKING:
    from plannerGraphVisualiser.easy_visualiser.visualiser import Visualiser


class Key:
    KeyType = Union[Union[str, List[str]], "Key"]

    def __init__(self, keys: KeyType):
        if isinstance(keys, Key):
            self._keys = list(keys._keys)
            return

        if isinstance(keys, str):
            keys = [keys]
        self._keys = [k.upper() for k in keys]

    def match(self, key: Union["Key", str]):
        if isinstance(key, Key):
            return any(key.match(_k) for _k in self._keys)
        return key.upper() in self._keys

    def __repr__(self):
        return ",".join(self._keys)


class Mapping:
    MappingRawType = Tuple[Key.KeyType, str, Callable]

    def __init__(
        self, key: Key.KeyType, description: Union[str, Callable], callback: Callable
    ):
        self.key = Key(key)
        self._description = description
        self.callback = callback

    @property
    def description(self):
        if isinstance(self._description, Callable):
            return self._description()
        return self._description


class AbstractModalControl(ABC):
    key: Key
    _modal_name: str = None
    mappings: List[Mapping]

    @property
    def modal_name(self):
        return self._modal_name if self._modal_name else f"[{self.key}]"

    @abstractmethod
    def to_help_msg(self) -> str:
        pass


class ModalControl(AbstractModalControl):
    def __init__(
        self,
        key: Union[Key.KeyType],
        mappings: List[Union[Mapping, Mapping.MappingRawType]],
        modal_name: str = None,
    ):
        self.key = Key(key)
        self.mappings: List[Mapping] = [
            Mapping(m[0], m[1], m[2]) if isinstance(m, tuple) else m for m in mappings
        ]
        if any(ModalState.quit_key.match(data[0]) for data in mappings):
            raise ValueError("[q] cannot be mapped!")
        self._modal_name = modal_name

    def to_help_msg(self) -> str:
        msg = f">>>>>  {self.modal_name}\n\n"
        msg += "\n".join(
            f"Press [{mapping.key}] to {mapping.description}"
            for mapping in self.mappings
        )
        msg += f"\n\n\n\nPress [{ModalState.quit_key}] to exit current modal"
        return msg

    def __repr__(self):
        return f"{ModalControl.__name__}<{self.key}:{self.mappings}>"


class RootModalControl(AbstractModalControl):
    def __init__(self, visualiser: "Visualiser", modal_state):
        self.visualiser = visualiser
        self.modal_state = modal_state
        self.extra_registered_mappings: List[Mapping] = []

    @property
    def mappings(self) -> List[Mapping]:
        def enter_modal_cb(modal: ModalControl):
            self.modal_state.state = modal

        return list(
            chain(
                # root mappings
                (
                    Mapping(m.key, f"Press [{m.key}] to {m.description}", m.callback)
                    for m in self.extra_registered_mappings
                ),
                # empty line to separate
                [Mapping("", "", lambda: None)],
                # modal level mappings
                (
                    Mapping(
                        mapping.key,
                        description=f"Press [{mapping.key}] to "
                        f"control Modal <{mapping.modal_name}>",
                        callback=lambda: enter_modal_cb(mapping),
                    )
                    # gather all mappings in each plugin
                    for mapping in chain(
                        *(
                            p.keys
                            for p in self.visualiser.plugins
                            if isinstance(p, ToggleableMixin)
                        )
                    )
                ),
            )
        )

    def to_help_msg(self) -> str:
        msg = "~~~~~~~~~~ Root Directory ~~~~~~~~~\n\n"
        msg += "\n".join(cb.description for cb in self.mappings)
        return msg


class ModalState:
    root_state: RootModalControl
    _states_stack: List[ModalControl] = []
    quit_key: Key = Key("q")

    def __init__(self, visualiser: "Visualiser"):
        self.root_state = RootModalControl(visualiser, modal_state=self)

    @property
    def state(self) -> AbstractModalControl:
        if self.at_root:
            return self.root_state
        return self._states_stack[-1]

    @state.setter
    def state(self, value: ModalControl):
        if value in self._states_stack:
            raise ValueError(
                f"The given modal control {value} already exist in the current stack!"
            )
        self._states_stack.append(value)

    def add_root_mapping(self, mapping: Mapping):
        self.root_state.extra_registered_mappings.append(mapping)

    @property
    def at_root(self) -> bool:
        return len(self._states_stack) == 0

    def quit_modal(self) -> None:
        self._states_stack.pop(-1)
