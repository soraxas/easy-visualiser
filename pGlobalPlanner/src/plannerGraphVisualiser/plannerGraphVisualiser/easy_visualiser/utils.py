from typing import Union


class AxisScaler:
    def __init__(self, scale_factor: float) -> None:
        self.min = 0
        self.scale_factor = scale_factor

    def set_min(self, value: float) -> None:
        self.min = value

    def __call__(self, value: float) -> float:
        return (value - self.min) * self.scale_factor + self.min


class ToggleableBool:
    def __init__(self, value: bool = True):
        self.value: bool = value

    def toggle(self) -> "ToggleableBool":
        self.value = not self.value
        return self

    def set(self, value: bool) -> "ToggleableBool":
        self.value = bool(value)
        return self

    def get(self) -> bool:
        return bool(self)

    def __bool__(self) -> bool:
        return self.value

    def __repr__(self):
        return repr(bool(self))


def boolean_to_onoff(boolean: Union[bool, ToggleableBool]):
    return "ON" if boolean else "OFF"
