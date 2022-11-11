from abc import ABC, abstractmethod
from itertools import chain
from typing import Callable, List, Union, TYPE_CHECKING

from plannerGraphVisualiser.easy_visualiser.key_mapping import Mapping, Key
from plannerGraphVisualiser.easy_visualiser.plugin_capability import (
    TriggerableMixin,
)

if TYPE_CHECKING:
    from plannerGraphVisualiser.easy_visualiser.visualiser import Visualiser


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

    def __repr__(self):
        return f"{self.__class__.__name__}<{self.key}:{self.mappings}>"


def mapping_to_one_line_string(mapping: Mapping) -> str:
    return (
        f"Press [{mapping.key}] to {mapping.description}"
        if not mapping.key.is_empty
        else mapping.description
    )


class ModalControl(AbstractModalControl):
    def __init__(
        self,
        key: Union[Key.KeyType],
        mappings: List[Union[Mapping, Mapping.MappingRawType, "ModalControl"]],
        modal_name: str = None,
    ):
        self.key = Key(key)
        self.mappings: List[Mapping] = []
        for data in mappings:
            if isinstance(data, tuple):
                mapping = Mapping(data[0], data[1], data[2])
            elif isinstance(data, Mapping):
                mapping = data
            elif isinstance(data, ModalControl):
                mapping = Mapping(
                    key=data.key,
                    description=f"Press {data.key} to control {data.modal_name}",
                    callback=ModalState.get_instance().create_set_state_callback(data),
                )
            else:
                raise ValueError(f"Unknown data type {type(data)} for {data}")
            self.mappings.append(mapping)
        if any(ModalState.quit_key.match(data.key) for data in mappings):
            raise ValueError("[q] cannot be mapped!")
        self._modal_name = modal_name

    def to_help_msg(self) -> str:
        msg = (
            f">>>>>  {' > '.join(s.modal_name for s in ModalState.states_stack())}\n\n"
        )
        msg += "\n".join(
            mapping_to_one_line_string(mapping) for mapping in self.mappings
        )
        msg += f"\n\n\n\nPress [{ModalState.quit_key}] to exit current modal"
        return msg


class RootModalControl(AbstractModalControl):
    def __init__(self, visualiser: "Visualiser", modal_state):
        self.key = Key("")
        self.visualiser = visualiser
        self.modal_state: ModalState = modal_state
        self.extra_registered_mappings: List[Mapping] = []

    @property
    def mappings(self) -> List[Mapping]:
        return list(
            chain(
                # root mappings
                (
                    Mapping(m.key, mapping_to_one_line_string(m), m.callback)
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
                        callback=ModalState.get_instance().create_set_state_callback(
                            mapping
                        ),
                    )
                    # gather all mappings in each plugin
                    for mapping in chain(
                        *(
                            p.keys
                            for p in self.visualiser.plugins
                            if isinstance(p, TriggerableMixin)
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

    __global_instance: "ModalState" = None

    @classmethod
    def get_instance(cls) -> "ModalState":
        if cls.__global_instance is None:
            raise RuntimeError()
        return cls.__global_instance

    @classmethod
    def states_stack(cls) -> List[ModalControl]:
        return list(cls.get_instance()._states_stack)

    def __init__(self, visualiser: "Visualiser"):
        self.root_state = RootModalControl(visualiser, modal_state=self)
        self.__class__.__global_instance = self

    def create_set_state_callback(self, value_to_be_set: ModalControl) -> Callable:
        """Return a callback that would modify the state of this instance"""

        def cb():
            self.state = value_to_be_set

        return cb

    @property
    def state(self) -> AbstractModalControl:
        if self.at_root:
            return self.root_state
        return self._states_stack[-1]

    @state.setter
    def state(self, value: ModalControl):
        assert isinstance(value, ModalControl)
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
