import threading

from loguru import logger

from easy_visualiser import Visualiser

from ..input import DataSourceSingleton
from ..input.remote_control_proxy import (
    RemoteControlProxyDatasource,
    RemoteControlProxyQueue,
)


class VisualiserThread(threading.Thread):
    def __init__(
        self,
        queue_io: RemoteControlProxyQueue,
        #   data_source: RemoteControlProxyDatasource,
    ):
        super().__init__()

        self.queue_io = queue_io
        self.started = threading.Event()
        self.daemon = True

    def run(self):
        self.viz = Visualiser()

        data_source = RemoteControlProxyDatasource(queue_io=self.queue_io)

        self.viz.register_datasource(data_source)

        self.started.set()

        self.viz.run()


# class RemoteControlProxyDatasource(DataSourceSingleton):
#     # p_msg_recv: MsgXAsyncReceiver

#     def __init__(self, uri_return):
#         super().__init__()
#         self.callbacks: List[Callable] = []
#         self.queue_io = PyroDaemonIO()

#         self.uri_return = uri_return  # multiprocessing queue

#     def construct_plugin(self):
#         # create a pyro daemon with object, running in its own worker thread
#         pyro_thread = VisualiserThread(self.queue_io)
#         pyro_thread.daemon = True
#         pyro_thread.start()
#         pyro_thread.started.wait()

#         # report the uri for this process
#         self.uri_return.put(str(pyro_thread.uri))

#         self.visualiser.add_coroutine_task(self.__collect_msg())

#     async def __collect_msg(self):
#         from .hehe import VisualiserServerIO

#         while self.visualiser:
#             logger.trace("retrieving request")
#             call_type, msg = await self.queue_io.input_queue.coro_get()
#             logger.trace("got request: {} ({})", msg, call_type)

#             if call_type is VisualiserServerIO.RemoteCallType.method_call:
#                 method_name, args, kwargs = msg
#                 out = getattr(self.visualiser, method_name)(*args, **kwargs)
#             elif call_type is VisualiserServerIO.RemoteCallType.attribute_access:
#                 out = getattr(self.visualiser, msg)

#             await self.queue_io.output_queue.coro_put(out)
