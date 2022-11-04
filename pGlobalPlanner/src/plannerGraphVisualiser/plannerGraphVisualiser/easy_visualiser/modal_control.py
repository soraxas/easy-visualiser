import enum
from typing import Callable, Tuple, List, Union


class Modal(enum.Enum):
    pass


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


class ModalControl:
    def __init__(
        self,
        key: Key.KeyType,
        mappings: List[Union[Mapping, Mapping.MappingRawType]],
        modal_name: str = None,
    ):
        self.key = Key(key)
        self.mappings: List[Mapping] = [
            Mapping(m[0], m[1], m[2]) if isinstance(m, tuple) else m for m in mappings
        ]
        if any(ModalState.quit_key.match(data[0]) for data in mappings):
            raise ValueError("[q] cannot be mapped!")
        self.__modal_name = modal_name

    @property
    def modal_name(self):
        return self.__modal_name if self.__modal_name else f"[{self.key}]"

    def to_help_msg(self):
        return f"Press [{self.key}] to enter {self.modal_name}"

    def __repr__(self):
        return f"{ModalControl.__name__}<{self.key}:{self.mappings}>"


class CoreModal(Modal):
    default = 0


class ModalState:
    state: ModalControl = None
    quit_key: Key = Key("q")

    # state: ModalControl #= CoreModal.default

    def set_s(self, modal: Modal):
        pass
