import enum
import functools
import inspect
import os
import stat
import threading
from dataclasses import dataclass
from typing import Callable, List

import aioprocessing
import Pyro5.api
from loguru import logger

from easy_visualiser import Visualiser

from . import DataSourceSingleton


@dataclass
class PyroDaemonIO:
    input_queue = aioprocessing.AioQueue()
    output_queue = aioprocessing.AioQueue()

    # output_queue = queue.Queue()


class PyroRemoteCallType(enum.Enum):
    method_call = enum.auto()
    attribute_access = enum.auto()


class MyPyroDaemon(threading.Thread):
    def __init__(self, queue_io: PyroDaemonIO):
        super().__init__()
        self.queue_io = queue_io

        self.started = threading.Event()

    def run(self, socket_name: str = "/tmp/easy_visualiser_remote-soc"):
        # remove any existing stale socket
        try:
            if stat.S_ISSOCK(os.stat(socket_name).st_mode):
                os.remove(socket_name)
        except FileNotFoundError:
            pass
        except OSError as err:
            # Directory may have permissions only to create socket.
            logger.error(
                "Unable to check or remove stale UNIX socket %r: %r", socket_name, err
            )
        try:
            if stat.S_ISSOCK(os.stat(socket_name).st_mode):
                os.remove(socket_name)
        except FileNotFoundError:
            pass

        daemon = Pyro5.api.Daemon(
            # port=9413,
            unixsocket=socket_name,
        )

        @Pyro5.api.expose
        class PyroAdapter:
            def method_call(__self, method_name, args=tuple(), kwargs={}):
                __self.method_call_nowait(method_name, args, kwargs)
                ok = self.queue_io.output_queue.get()
                logger.trace("got {}", ok)
                return ok

            def method_call_nowait(__self, method_name, args=tuple(), kwargs={}):
                logger.trace("requesting {}", method_name)
                self.queue_io.input_queue.put(
                    (PyroRemoteCallType.method_call, (method_name, args, kwargs))
                )

            def attribute_access(__self, attribute_name):
                logger.trace("requesting attr {}", attribute_name)
                self.queue_io.input_queue.put(
                    (PyroRemoteCallType.attribute_access, attribute_name)
                )
                ok = self.queue_io.output_queue.get()
                logger.trace("got {}", ok)
                return ok

            def __bool__(__self):
                return __self.method_call("__bool__")

        self.uri = daemon.register(PyroAdapter, "easy_visualiser.Visualiser")
        print(self.uri)

        self.started.set()
        daemon.requestLoop()


class RemoteControlProxyDatasource(DataSourceSingleton):
    # p_msg_recv: MsgXAsyncReceiver

    def __init__(self, uri_return):
        super().__init__()
        self.callbacks: List[Callable] = []
        self.queue_io = PyroDaemonIO()

        self.uri_return = uri_return  # multiprocessing queue

    def construct_plugin(self):
        # create a pyro daemon with object, running in its own worker thread
        pyro_thread = MyPyroDaemon(self.queue_io)
        pyro_thread.daemon = True
        pyro_thread.start()
        pyro_thread.started.wait()

        # report the uri for this process
        self.uri_return.put(str(pyro_thread.uri))

        self.visualiser.add_coroutine_task(self.__collect_msg())

    async def __collect_msg(self):
        # asyncio.get_running_loop()
        while self.visualiser:
            logger.trace("retrieving request")
            call_type, msg = await self.queue_io.input_queue.coro_get()
            logger.trace("got request: {} ({})", msg, call_type)

            if call_type is PyroRemoteCallType.method_call:
                method_name, args, kwargs = msg
                out = getattr(self.visualiser, method_name)(*args, **kwargs)
            elif call_type is PyroRemoteCallType.attribute_access:
                out = getattr(self.visualiser, msg)

            await self.queue_io.output_queue.coro_put(out)
            # break


def as_proxy(target_func):
    def intermediate_functor(_):
        # this better handle the docstring.
        @functools.wraps(target_func)
        def _wrapped(self: "EasyVisualiserClientProxy", *args, **kwargs):
            try:
                return self.visualiser_server.method_call(
                    target_func.__name__, args, kwargs
                )
            except Pyro5.errors.PyroError:
                pass

        return _wrapped

    return intermediate_functor


@functools.wraps(Visualiser, updated=())
class EasyVisualiserClientProxy:
    """
    Proxy client for visualiser
    """

    def __init__(self, port: int = 9413, uri: str = None):
        if uri is None:
            uri = f"PYRO:easy_visualiser.Visualiser@localhost:{port}"

        self.uri = uri

        self.visualiser_server = Pyro5.api.Proxy(self.uri)

    @as_proxy(Visualiser.scatter)
    def scatter(self):
        ...

    @as_proxy(Visualiser.plot)
    def plot(self):
        ...

    def __getattr__(self, name):
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
