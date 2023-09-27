import asyncio
from typing import Callable, List

from msgx.asyncio import MsgXAsyncReceiver

from . import DataSourceSingleton


class MsgX(DataSourceSingleton):
    p_msg_recv: MsgXAsyncReceiver

    def __init__(self):
        super().__init__()
        self.callbacks: List[Callable] = []

    def construct_plugin(self):
        self.p_msg_recv = MsgXAsyncReceiver()
        self.visualiser.add_coroutine_task(self.__collect_msgx())

    async def __collect_msgx(self):
        _loop = asyncio.get_running_loop()
        while True:
            msg = await self.p_msg_recv.just_get_msg()
            for callback in self.callbacks:
                _loop.call_soon(callback, msg)

    def add_callback(self, callback: Callable):
        self.callbacks.append(callback)
