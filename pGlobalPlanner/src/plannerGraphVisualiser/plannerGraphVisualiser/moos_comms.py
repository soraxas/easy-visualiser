import traceback
from typing import Callable, Dict

import pymoos as moos

from plannerGraphVisualiser.easy_visualiser.plugins.abstract_visualisable_plugin import (
    VisualisablePluginInitialisationError,
)


class pMoosPlannerVisualiser(moos.comms):
    def __init__(self):
        try:
            self.__class__.__instance
        except AttributeError:
            pass
        else:
            raise RuntimeError(f"An instance of {self.__class__} already exists!")
        super().__init__()
        self.connect_to_moos("localhost", 9000)
        self.__class__.__instance = None
        self.__registered_variables: Dict[str, Callable] = dict()

    @classmethod
    def get_instance(cls):
        try:
            return cls.__instance
        except AttributeError:
            cls.__instance = pMoosPlannerVisualiser()
        return cls.__instance

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
        pass
        return True

    def __on_new_mail(self):
        try:
            for msg in self.fetch():
                self.__registered_variables[msg.key()](msg)
        except Exception as e:
            traceback.print_exc()
            return False
        return True
