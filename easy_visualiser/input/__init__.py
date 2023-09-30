from abc import ABC
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from easy_visualiser.visualiser import VisualisablePluginNameSpace, Visualiser


class DataSource(ABC):
    visualiser: "Visualiser" = None
    name: str

    def __init__(self, name: Optional[str] = None):
        if not hasattr(self, "name"):
            if name is None:
                name = self.__class__.__name__
            self.name = name

    def on_initialisation(self, visualiser: "Visualiser"):
        """
        Can use this time to register hooks on visualiser
        :return:
        """
        self.visualiser = visualiser


class DataSourceSingleton(DataSource):
    __instance: "DataSourceSingleton"

    def __init__(self):
        try:
            self.__class__.__instance
        except AttributeError:
            pass
        else:
            raise RuntimeError(f"An instance of {self.__class__} already exists!")
        super().__init__()

    @classmethod
    def get_instance(cls):
        try:
            return cls.__instance
        except AttributeError:
            cls.__instance = cls()
        return cls.__instance
