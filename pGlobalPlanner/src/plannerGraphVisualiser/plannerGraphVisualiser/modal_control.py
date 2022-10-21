import abc
import enum
from typing import Callable, Tuple, List, Union


class Modal(enum.Enum):
    pass


class Key:
    def __init__(self, keys: Union[str, List[str]]):
        if isinstance(keys, str):
            keys = [keys]
        self._keys = [k.upper() for k in keys]

    def match(self, key: Union["Key", str]):
        if isinstance(key, Key):
            return any(key.match(_k) for _k in self._keys)
        return key.upper() in self._keys

    def __repr__(self):
        return ",".join(self._keys)


class ModalControl:
    def __init__(
        self,
        key: str,
        mappings: List[Tuple[Union[str, Key], str, Callable]],
        modal_name: str = None,
    ):
        self.key = Key(key)
        self.mappings: List[Tuple[Key, str, Callable]] = [
            (m[0], m[1], m[2]) if isinstance(m[0], Key) else (Key(m[0]), m[1], m[2])
            for m in mappings
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
