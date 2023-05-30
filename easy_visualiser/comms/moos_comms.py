import traceback
from typing import Callable, Dict

import pymoos as moos

from easy_visualiser.plugins import VisualisablePluginInitialisationError

from . import Singleton


class MoosComm(Singleton, moos.comms):
    def __init__(self):
        super().__init__()
        self.connect_to_moos("localhost", 9000)
        self.__registered_variables: Dict[str, Callable] = dict()

    def connect_to_moos(self, moos_host, moos_port):
        self.set_on_connect_callback(self.__on_connect)
        self.set_on_mail_callback(self.__on_new_mail)
        self.run(moos_host, moos_port, self.__class__.__name__)
        if not self.wait_until_connected(2000):
            self.close(True)
            raise VisualisablePluginInitialisationError(
                self.__class__, "Failed to connect to local MOOSDB"
            )

    def register_variable(
        self, variable_name: str, callback: Callable, interval: float = 0
    ):
        if variable_name in self.__registered_variables:
            raise ValueError(f"Variable {variable_name} had already been registered!")
        self.__registered_variables[variable_name] = callback
        self.register(variable_name, interval)

    def __on_connect(self):
        return True

    def __on_new_mail(self):
        try:
            for msg in self.fetch():
                self.__registered_variables[msg.key()](msg)
        except Exception:
            traceback.print_exc()
            return False
        return True
