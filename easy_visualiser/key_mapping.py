from typing import Callable, List, Optional, Tuple, Union


class Key:
    KeyType = Union[Union[str, List[str]], "Key"]
    Plus: "Key"
    Minus: "Key"
    _keys: List[str]

    def __init__(self, keys: KeyType, custom_repr: Optional[str] = None):
        self.is_empty = False
        self.custom_repr = custom_repr
        if isinstance(keys, Key):
            # copy construct
            self._keys = list(keys._keys)
            self.custom_repr = keys.custom_repr
            return

        if isinstance(keys, str):
            self.is_empty = keys == ""
            keys = [keys]
        self._keys = [k.upper() for k in keys]

    def match(self, key: Union["Key", str]):
        if isinstance(key, Key):
            return any(key.match(_k) for _k in self._keys)
        return key.upper() in self._keys

    def __repr__(self):
        if self.custom_repr is not None:
            return self.custom_repr
        return ",".join(self._keys)


######################################
Key.Plus = Key(["+", "="], custom_repr="+")
Key.Minus = Key(["-", "_"], custom_repr="-")
######################################


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

    def __repr__(self):
        return f"{self.__class__.__name__}<{self.key}|'{self.description}|{self.callback}'>"


class MappingOnlyDisplayText(Mapping):
    def __init__(self, description: Union[str, Callable]):
        super().__init__("", description, lambda: None)
