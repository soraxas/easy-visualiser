import asyncio
import inspect
import os
import stat
import threading
from typing import Callable, List

import Pyro5.api
from loguru import logger

from easy_visualiser import Visualiser

from . import DataSourceSingleton


class MyPyroDaemon(threading.Thread):
    def __init__(self, msg_queue: asyncio.Queue):
        super().__init__()
        self.msg_queue = msg_queue
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
            def message(_, messagetext, args, kwargs):
                self.msg_queue.put_nowait((messagetext, args, kwargs))

        self.uri = daemon.register(PyroAdapter, "easy_visualiser.Visualiser")
        print(self.uri)

        self.started.set()
        daemon.requestLoop()

    def send_message(self, messagetext, *args, **kwargs):
        self.msg_queue.put_nowait((messagetext, args, kwargs))


class RemoteControlProxyDatasource(DataSourceSingleton):
    # p_msg_recv: MsgXAsyncReceiver

    def __init__(self, uri_return):
        super().__init__()
        self.callbacks: List[Callable] = []
        self.msg_queue = asyncio.Queue()

        self.uri_return = uri_return  # multiprocessing queue

    def construct_plugin(self):
        # create a pyro daemon with object, running in its own worker thread
        pyro_thread = MyPyroDaemon(self.msg_queue)
        pyro_thread.daemon = True
        pyro_thread.start()
        pyro_thread.started.wait()

        # report the uri for this process
        self.uri_return.put(str(pyro_thread.uri))

        self.visualiser.add_coroutine_task(self.__collect_msg())

    async def __collect_msg(self):
        asyncio.get_running_loop()

        while self.visualiser:
            msg = await self.msg_queue.get()
            print(msg)

            method_name, args, kwargs = msg

            getattr(self.visualiser, method_name)(*args, **kwargs)


class EasyVisualiserClientProxy:
    """
    Proxy client for visualiser
    """

    def __init__(self, port: int = 9413, uri: str = None):
        if uri is None:
            uri = f"PYRO:easy_visualiser.Visualiser@localhost:{port}"

        self.uri = uri

        self.visualiser_server = Pyro5.api.Proxy(self.uri)

    def __getattr__(self, name):
        datapack = dict()
        try:
            _attribute = getattr(Visualiser, name)
        except AttributeError:
            # maybe it's an object variable that only exists after initialisation?
            raise NotImplementedError(f"{name}")
            return None
        else:
            logger.debug("Got attr: {}", _attribute)
            logger.opt(lazy=True).debug(
                "Type isdatadescriptor[{}] ismethod[{}] isfunction[{}]",
                lambda: inspect.isdatadescriptor(_attribute),
                lambda: inspect.ismethod(_attribute),
                lambda: inspect.isfunction(_attribute),
            )

            if inspect.isfunction(_attribute):
                datapack["callable"] = _attribute
            else:
                print(type(_attribute))
                print(_attribute)

            return lambda *args, **kwargs: self.visualiser_server.message(
                name, args, kwargs
            )

        return super().__getattr__(name)
