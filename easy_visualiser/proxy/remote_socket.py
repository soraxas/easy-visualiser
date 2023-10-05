import os
import stat
import threading
from dataclasses import dataclass

import aioprocessing
import Pyro5.api
from loguru import logger

from easy_visualiser import Visualiser
from easy_visualiser.input.remote_control_proxy import (
    RemoteControlProxyDatasource,
    RemoteControlProxyQueue,
)

from ..input import DataSourceSingleton


@dataclass
class PyroDaemonIO:
    input_queue = aioprocessing.AioQueue()
    output_queue = aioprocessing.AioQueue()
    # output_queue = queue.Queue()


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

        from .visualiser_proxy import VisualiserServerIO

        pyro_server = Pyro5.api.expose(VisualiserServerIO)(
            self.queue_io.input_queue, self.queue_io.output_queue
        )

        self.uri = daemon.register(pyro_server, "easy_visualiser.Visualiser")
        print(self.uri)

        self.started.set()
        daemon.requestLoop()


def build_remote_datasource(uri_return_queue):
    queue = RemoteControlProxyQueue()

    def construct_callback(plugin):
        # create a pyro daemon with object, running in its own worker thread
        pyro_thread = MyPyroDaemon(queue)
        pyro_thread.daemon = True
        pyro_thread.start()
        pyro_thread.started.wait()

        # report the uri for this process
        uri_return_queue.put(str(pyro_thread.uri))

    data_source = RemoteControlProxyDatasource(
        queue_io=queue, construct_callback=construct_callback
    )
    return data_source
