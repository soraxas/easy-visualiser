import sys
from typing import Callable, List

from . import DataSourceSingleton

sys.path.insert(0, "/home/tin/git-repos/PlotMsg-cpp/built_python_pkg/")


from plotmsg_dash import PlotMsgReciever

# while True:
#     p_msg.spin_once()
#     for k in p_msg.figs:
#         print(f"Displaying figure {k}...")
#         p_msg.figs.pop(k).show()


class PlotMsg(DataSourceSingleton):
    def __init__(self):
        super().__init__()
        self.callbacks: List[Callable] = []

    def construct_plugin(self):
        self.p_msg_recv = PlotMsgReciever()
        self.visualiser.run_in_background_thread(self.__collect_plotmsg, 0.1)

    def __collect_plotmsg(self):
        msg = self.p_msg_recv.get_msg()
        for callback in self.callbacks:
            callback(msg)

    def add_callback(self, callable: Callable):
        self.callbacks.append(callable)
