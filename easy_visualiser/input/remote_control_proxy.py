import enum
from dataclasses import dataclass
from typing import Any, Callable

import aioprocessing
import Pyro5.api
from loguru import logger

from easy_visualiser import Visualiser

from . import DataSource


@dataclass
class RemoteControlProxyQueue:
    input_queue: Any = aioprocessing.AioQueue()
    output_queue: Any = aioprocessing.AioQueue()


class RemoteControlProxyRetType(enum.Enum):
    exiting = enum.auto()


class RemoteControlProxyDatasource(DataSource):
    def __init__(
        self,
        queue_io: RemoteControlProxyQueue,
        construct_callback: Callable = lambda x: x,
    ):
        super().__init__()
        self.queue_io: RemoteControlProxyQueue = queue_io

        self.construct_callback = construct_callback

        # self.uri_return = uri_return  # multiprocessing queue

    def construct_plugin(self):
        self.construct_callback(self)
        self.visualiser.add_coroutine_task(self.__collect_msg())

    async def __collect_msg(self):
        from ..proxy.visualiser_proxy import VisualiserServerIO

        self.visualiser.hooks.on_visualiser_close.add_hook(
            lambda: self.queue_io.output_queue.put(RemoteControlProxyRetType.exiting)
        )
        self.visualiser.hooks.on_visualiser_close.add_hook(lambda: print(".."))
        self.visualiser.hooks.on_visualiser_close.add_hook(
            lambda: self.queue_io.output_queue.put(RemoteControlProxyRetType.exiting)
        )

        while self.visualiser:
            logger.trace("retrieving request")
            call_type, msg = await self.queue_io.input_queue.coro_get()
            logger.trace("got request: {} ({})", msg, call_type)

            try:
                if call_type is VisualiserServerIO.RemoteCallType.method_call:
                    method_name, args, kwargs = msg
                    out = getattr(self.visualiser, method_name)(*args, **kwargs)
                elif call_type is VisualiserServerIO.RemoteCallType.attribute_access:
                    out = getattr(self.visualiser, msg)

                await self.queue_io.output_queue.coro_put(out)
            except Exception as e:
                await self.queue_io.output_queue.coro_put(e)
