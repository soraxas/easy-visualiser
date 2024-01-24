from typing import Any

import numpy as np


class Aggregator(dict):
    """Helps you to aggregates data by name"""

    def __init__(self, *args, dtype=float, **kwargs):
        super().__init__(*args, **kwargs)
        self.dtype = dtype

    def __setitem__(self, __key: Any, __value: Any) -> None:
        if isinstance(__value, np.ndarray):
            if len(__value.shape) > 1:
                raise ValueError(f"{self.__class__} only supports 1D input array")
        return super().__setitem__(__key, __value)

    def assemble(self) -> np.ndarray:
        kwargs = dict()
        if self.dtype is not None:
            kwargs["dtype"] = self.dtype
        return np.array(list(self.values()), **kwargs)

    def remove(self, key: Any):
        return self.pop(key, None)


if __name__ == "__main__":
    a = Aggregator()
    a["1"] = [2, 3, 5]
    a["okk"] = [2, 333, 5]
    a["np"] = np.array([1, 2, 4])
    a.remove("1")
    a.remove("no key")
    print(a.assemble())
