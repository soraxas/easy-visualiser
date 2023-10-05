import contextlib
import enum
import functools
import inspect
from abc import ABC

import Pyro5.api
from loguru import logger

from easy_visualiser import Visualiser

from ..input import DataSourceSingleton
from ..input.remote_control_proxy import RemoteControlProxyRetType


class EasyVisualiserQuitting(Exception):
    pass


def as_proxy(target_func):
    def intermediate_functor(_):
        # this better handle the docstring.
        @functools.wraps(target_func)
        def _wrapped(self: "EasyVisualiserClientProxy", *args, **kwargs):
            if self.visualiser_server.exited:
                raise EasyVisualiserQuitting()
            try:
                return self.visualiser_server.method_call(
                    target_func.__name__, args, kwargs
                )
            except Pyro5.errors.PyroError:
                pass

        return _wrapped

    return intermediate_functor


class VisualiserServerIO:
    """
    Remote protocol for easy visualiser
    """

    exited: bool = False

    class RemoteCallType(enum.Enum):
        method_call = enum.auto()
        attribute_access = enum.auto()

    def __init__(self, queue_input, queue_output) -> None:
        self.queue_input = queue_input
        self.queue_output = queue_output

    def __get_output(self):
        ret = self.queue_output.get()
        logger.trace("got {}", ret)
        if ret is RemoteControlProxyRetType.exiting:
            self.exited = True
            return None
        elif isinstance(ret, Exception):
            raise ret
        return ret

    def method_call(self, method_name: str, args=tuple(), kwargs={}):
        self.method_call_nowait(method_name, args, kwargs)
        return self.__get_output()

    def method_call_nowait(self, method_name, args=tuple(), kwargs={}):
        logger.trace("requesting {}", method_name)
        self.queue_input.put(
            (VisualiserServerIO.RemoteCallType.method_call, (method_name, args, kwargs))
        )

    def attribute_access(self, attribute_name: str):
        logger.trace("requesting attr {}", attribute_name)
        self.queue_input.put(
            (VisualiserServerIO.RemoteCallType.attribute_access, attribute_name)
        )
        return self.__get_output()

    def __bool__(self):
        return self.method_call("__bool__")


@functools.wraps(Visualiser, updated=())
class EasyVisualiserClientProxy(ABC):
    """
    Proxy client for visualiser
    """

    def __init__(self, visualiser_server: VisualiserServerIO):
        self.visualiser_server = visualiser_server

    @as_proxy(Visualiser.scatter)
    def scatter(self):
        ...

    @as_proxy(Visualiser.plot)
    def plot(self):
        ...

    def __bool__(self):
        if self.visualiser_server.exited:
            return False
        return bool(self.visualiser_server.attribute_access("alive"))

    def __getattr__(self, name):
        if self.visualiser_server.exited:
            raise EasyVisualiserQuitting()
        try:
            _attribute = getattr(Visualiser, name)
        except AttributeError:
            # maybe it's an object variable that only exists after initialisation?
            return self.visualiser_server.attribute_access(name)
            # raise NotImplementedError(f"{name}")
            # return None

        logger.trace("Got attr: {}", _attribute)
        logger.opt(lazy=True).trace(
            "Type isdatadescriptor[{}] ismethod[{}] isfunction[{}]",
            lambda: inspect.isdatadescriptor(_attribute),
            lambda: inspect.ismethod(_attribute),
            lambda: inspect.isfunction(_attribute),
        )

        try:
            if inspect.isfunction(_attribute):
                return lambda *args, **kwargs: self.visualiser_server.method_call(
                    name, args, kwargs
                )
            elif inspect.isdatadescriptor(_attribute):
                return self.visualiser_server.attribute_access(name)
            else:
                # print(type(_attribute))
                # print(_attribute)
                raise NotImplementedError(f"{_attribute}")
        except (Pyro5.errors.PyroError, ConnectionRefusedError):
            return None

    @contextlib.contextmanager
    def contextmanager(self):
        try:
            yield self
        except EasyVisualiserQuitting:
            pass

    def is_running(self):
        return self

    def __enter__(self):
        self.__cm = self.contextmanager()
        return self.__cm.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        return self.__cm.__exit__(exc_type, exc_value, traceback)
