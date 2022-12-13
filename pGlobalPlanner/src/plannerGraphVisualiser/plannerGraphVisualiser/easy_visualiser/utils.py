from typing import Union, List, Tuple, Set, Iterator, TypeVar

import numpy as np


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


class ScalableFloat:
    def __init__(
        self, value: float, upper_bound: float = np.inf, lower_bound: float = -np.inf
    ):
        self.value = value
        self.upper_bound = upper_bound
        self.lower_bound = lower_bound

    def scale(self, scale_factor: float) -> bool:
        self.value *= scale_factor
        self.value = min(max(self.value, self.lower_bound), self.upper_bound)
        return True

    def set(self, value: float):
        value = float(value)
        assert type(value) == float, f"{type(value)}: {value}"
        self.value = value

    def __float__(self):
        return self.value.__float__()

    def __repr__(self):
        return repr(float(self))


class IncrementableInt:
    def __init__(
        self, value: int, upper_bound: int = np.inf, lower_bound: int = -np.inf
    ):
        self.value = value
        self.upper_bound = upper_bound
        self.lower_bound = lower_bound

    def increment(self, amount: int = 1):
        return self._update_value(amount)

    def decrement(self, amount: int = -1):
        return self._update_value(amount)

    def _update_value(self, amount: int) -> bool:
        self.value += amount
        self.value = min(max(self.value, self.lower_bound), self.upper_bound)
        return True

    def set(self, value: int):
        value = int(value)
        assert type(value) == int, f"{type(value)}: {value}"
        self.value = value

    def __int__(self):
        return self.value.__int__()

    def __repr__(self):
        return repr(int(self))


def map_array_to_0_1(array: np.ndarray) -> np.ndarray:
    return (array - array.min()) / (array.max() - array.min())


U = TypeVar("U")


def topological_sort(source: List[Tuple[U, Set[U]]]) -> Iterator[U]:
    """perform topo sort on elements.

    :arg source: list of ``(name, [list of dependancies])`` pairs
    :returns: list of names, with dependancies listed first
    """
    pending = [
        (name, set(deps)) for name, deps in source
    ]  # copy deps so we can modify set in-place
    emitted = []
    while pending:
        next_pending = []
        next_emitted = []
        for entry in pending:
            name, deps = entry
            deps.difference_update(emitted)  # remove deps we emitted last pass
            if deps:  # still has deps? recheck during next pass
                next_pending.append(entry)
            else:  # no more deps? time to emit
                yield name
                emitted.append(
                    name
                )  # <-- not required, but helps preserve original ordering
                next_emitted.append(
                    name
                )  # remember what we emitted for difference_update() in next pass
        if (
            not next_emitted
        ):  # all entries have unmet deps, one of two things is wrong...
            raise ValueError(
                "cyclic or missing dependency detected: %r" % (next_pending,)
            )
        pending = next_pending
        emitted = next_emitted
