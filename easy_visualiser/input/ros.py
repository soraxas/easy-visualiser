import os
from typing import Callable

import rosgraph
import rospy

from . import DataSourceSingleton

ros_master_url = os.environ["ROS_MASTER_URI"]

from concurrent.futures import ThreadPoolExecutor

my_print = lambda *args: print("[RosComm]", *args)


class RosComm(DataSourceSingleton):
    initialised = False

    def __init__(self):
        super().__init__()
        # initialise in a background thread
        pool = ThreadPoolExecutor()
        pool.submit(self.__init_node)

        self.subscribers = []
        self.subscribed_topics = []

    def ros_auto_connect(self, event):
        if not rospy.is_shutdown() and rosgraph.is_master_online(ros_master_url):
            return

        # attempt to reconnect
        my_print("master lost ...")
        self.subscribers.clear()
        r = rospy.Rate(1)
        while True:
            my_print("Attempting to re-connect...")
            connected = rosgraph.is_master_online(ros_master_url)

            if connected:
                my_print("Connected.")
                self.__init_node()
                # re-subscribe
                for _subscribe_datapack in self.subscribed_topics:
                    self.__subscribe(_subscribe_datapack)
                break
            r.sleep()

    def __init_node(self):
        # use disable_signals if initialising node in a background thread
        rospy.init_node("listener", anonymous=True, disable_signals=True)
        rospy.Timer(rospy.Duration(1), self.ros_auto_connect)
        self.initialised = True
        my_print("Connected to ROS master")

    def __subscribe(self, datapack):
        # this is the actual subscribe function, without storing things in it
        topic, msg_type, callback = datapack
        self.subscribers.append(rospy.Subscriber(topic, msg_type, callback))

    def subscribe(self, topic: str, msg_type, callback: Callable):
        datapack = (topic, msg_type, callback)
        self.subscribed_topics.append(datapack)
        self.__subscribe(datapack)
