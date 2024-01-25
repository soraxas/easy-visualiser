from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Type

import rclpy
import numpy as np
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node

from easy_visualiser.utils import throttle

from . import DataSourceSingleton


class Ros2Comm(DataSourceSingleton):
    _process_n_messages_every_tick: int = None

    @property
    def process_n_messages_every_tick(self):
        """
        If this attribute is not set, we auto scale it based on currently
        subscribed topics.
        When there are more subscripted topics, we often needs to process more
        as there are more queued messages.
        """
        if self._process_n_messages_every_tick is None:
            return np.clip(len(self.subscribers), a_min=10, a_max=100)
        return self._process_n_messages_every_tick

    @process_n_messages_every_tick.setter
    def process_n_messages_every_tick(self, val: int):
        self._process_n_messages_every_tick = val

    def __init__(self):
        super().__init__()
        self.subscribers = []
        self.subscribed_topics = []
        ######################################
        self.callbacks_on_new_topics = []
        self.seen_topics = None
        ######################################

    def construct_plugin(self):
        # # initialise in a background thread
        rclpy.init()
        self.ros_interface = Node("easy_visualiser_ros2_comm")

        async def async_processing():
            while self:
                for i in range(self.process_n_messages_every_tick):
                    rclpy.spin_once(
                        self.ros_interface,
                        timeout_sec=self.visualiser.async_yield_sleep_time,
                    )
                await self.visualiser.async_yield()

        self.visualiser.async_loop.create_task(async_processing())
        self.visualiser.hooks.on_visualiser_close.add_hook(rclpy.shutdown)

    def __subscribe(self, datapack):
        # this is the actual subscribe function, without storing things in it
        args, kwargs = datapack
        self.subscribers.append(self.ros_interface.create_subscription(*args, **kwargs))

    def subscribe(
        self,
        msg_type: Type,
        topic: str,
        callback: Callable,
        qos_profile: int = 10,
        **kwargs,
    ):
        datapack = ((msg_type, topic, callback, qos_profile), kwargs)
        self.subscribed_topics.append(datapack)
        self.__subscribe(datapack)

    def add_callback_on_new_topics(self, callback: Callable[[str, str], None]):
        if self.seen_topics is None:
            # ONLY initialise this feature on-demand.
            self.seen_topics = set()

            @throttle(seconds=3)
            def check():
                for (
                    topic_name,
                    msg_type,
                ) in self.ros_interface.get_topic_names_and_types():
                    if topic_name not in self.seen_topics:
                        # New topic!
                        self.seen_topics.add(topic_name)
                        for cb in self.callbacks_on_new_topics:
                            cb(topic_name, msg_type)

            self.visualiser.hooks.on_interval_update.add_hook(check)

        self.callbacks_on_new_topics.append(callback)
