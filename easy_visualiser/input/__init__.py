from abc import ABC


class Singleton(ABC):
    __instance: "Singleton"

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
