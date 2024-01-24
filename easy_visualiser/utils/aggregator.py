from abc import ABC, abstractstaticmethod
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class AggregatorItem:
    _value: Any
    dirty: bool = True
    row_slice: slice = None

    def set_row_slice(self, *args):
        """
        This allow us to store, e.g., 100 rows, but only display some slice of it.
        For example, we might want to store history, but skip recently store ones,
        and only displays them later.
        """
        self.row_slice = slice(*args)

    def retrieve_for_build(self):
        self.dirty = False
        peeked = self.peek()
        if self.row_slice is not None:
            peeked = peeked[self.row_slice, :]
        return peeked

    def peek(self):
        return self._value

    def update_value(self, val: Any):
        self.dirty = True
        self._value = val


def infer_num_rows(item):
    if isinstance(item, AggregatorItem):
        item = item.peek()
    if isinstance(item, np.ndarray):
        if len(item.shape) == 1:
            return 1
        elif len(item.shape) == 2:
            return item.shape[0]
        raise ValueError("Only support 1 or 2D ndarray")
    return 1


class AbstractAggregatorBackend(ABC):
    @abstractstaticmethod
    def concat_items(aggregator: "Aggregator"):
        raise NotImplementedError()

    @abstractstaticmethod
    def needs_full_rebuild(aggregator: "Aggregator"):
        raise NotImplementedError()

    @abstractstaticmethod
    def partial_build(aggregator: "Aggregator"):
        raise NotImplementedError()

    @classmethod
    def full_build(cls, aggregator: "Aggregator"):
        kwargs = dict()
        if aggregator.dtype is not None:
            kwargs["dtype"] = aggregator.dtype
        return np.array(cls.concat_items(aggregator), **kwargs)


class AggregatorBackendUnity(AbstractAggregatorBackend):
    """
    Fast specialisaton that works for aggregator with
    items that are of size nrow == 1
    """

    @staticmethod
    def concat_items(aggregator: "Aggregator"):
        return list(v.retrieve_for_build() for v in aggregator.values())

    @staticmethod
    def needs_full_rebuild(aggregator: "Aggregator"):
        if aggregator._cached_container is None:
            return True
        return aggregator._cached_container.shape[0] != len(aggregator.values())

    @staticmethod
    def partial_build(aggregator: "Aggregator"):
        for i, item in enumerate(aggregator.values()):
            if item.dirty:
                aggregator._cached_container[i, :] = item.retrieve_for_build()


class AggregatorBackendComposite(AbstractAggregatorBackend):
    """
    Slower specialisaton that works for aggregator with
    items that are of variable size
    """

    @staticmethod
    def concat_items(aggregator: "Aggregator"):
        values = []
        for v in aggregator.values():
            v = v.retrieve_for_build()
            if infer_num_rows(v) == 1:
                values.append(v)
            else:
                values.extend(v)
        return values

    @staticmethod
    def needs_full_rebuild(aggregator: "Aggregator"):
        if aggregator._cached_container is None:
            return True
        full_length = sum(infer_num_rows(v) for v in aggregator.values())
        return aggregator._cached_container.shape[0] != full_length

    @staticmethod
    def partial_build(aggregator: "Aggregator"):
        i = 0
        for item in aggregator.values():
            nrow = infer_num_rows(item)
            if item.dirty:
                aggregator._cached_container[
                    i : i + nrow, :
                ] = item.retrieve_for_build()
            i += nrow


class Aggregator(OrderedDict):
    """
    Helps you to aggregates data by hash tag.

    This aggregator keeps tracks of stored values, and assmbles them into
    a continuous array later when called. This class stored cached array,
    and only update items at the corresponding row index if that row is
    dirty (updated).

    It also auto detect if any stored items are composite (> 1 rows).
    If so, it auto switch backend.
    """

    processor: AbstractAggregatorBackend = AggregatorBackendUnity

    def __init__(self, *args, dtype=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.dtype = dtype
        self._cached_container = None

    def __setitem__(self, __key: Any, __value: Any) -> None:
        # quick check to auto switck backend
        if self.processor != AggregatorBackendComposite and infer_num_rows(__value) > 1:
            # needs to use composite processor (slower code path)
            self.processor = AggregatorBackendComposite

        # store item
        item = self.get(__key, None)
        if item is None:
            item = AggregatorItem(__value)
            super().__setitem__(__key, item)
        else:
            item.update_value(__value)

    def __getitem__(self, __key: Any) -> Any:
        # return the wrapped value
        return super().__getitem__(__key).peek()

    def get_stored_item(self, __key: Any) -> AggregatorItem:
        return super().__getitem__(__key)

    def assemble(self) -> np.ndarray:
        """
        Main entry point. This auto decide if it needs partial or full rebuild.
        """
        if self.processor.needs_full_rebuild(self) or self.dtype is None:
            self._cached_container = self.processor.full_build(self)
        else:
            # This is: self._cached_container.shape[0] == len(self.values())
            self.processor.partial_build(self)
        return self._cached_container

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
