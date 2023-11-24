from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Type

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node

from . import DataSourceSingleton


class Ros2Comm(DataSourceSingleton):
    initialised = False

    def __init__(self):
        super().__init__()

    def construct_plugin(self):
        # # initialise in a background thread
        pool = ThreadPoolExecutor()
        pool.submit(self._init_node)

        self.subscribers = []
        self.subscribed_topics = []

    def _init_node(self):
        # use disable_signals if initialising node in a background thread
        rclpy.init()
        try:
            self.ros_interface = Node("easy_visualiser_ros2_comm")
        finally:
            executor = SingleThreadedExecutor()
            executor.add_node(self.ros_interface)
            executor.spin()
            executor.shutdown()
            self.ros_interface.destroy_node()
            rclpy.shutdown()

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
