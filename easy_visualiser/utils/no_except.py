import abc
import contextlib
import warnings
from typing import Type


class ContextManager(metaclass=abc.ABCMeta):
    """
    Class which can be used as `contextmanager`.
    Following patterns from: https://stackoverflow.com/questions/8720179/nesting-python-context-managers
    """

    def __init__(self):
        self.__cm = None

    @abc.abstractmethod
    @contextlib.contextmanager
    def contextmanager(self):
        raise NotImplementedError("Abstract method")

    def __enter__(self):
        self.__cm = self.contextmanager()
        return self.__cm.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        return self.__cm.__exit__(exc_type, exc_value, traceback)


class ExceptionAsWarning(UserWarning):
    pass


class NoAllException(ContextManager):
    def __init__(self):
        super().__init__()

    @contextlib.contextmanager
    def contextmanager(self):
        try:
            yield
        except ModuleNotFoundError as e:
            warnings.warn(str(e), ExceptionAsWarning)


class NoMyException(ContextManager):
    def __init__(self, ExceptionType: Type):
        super().__init__()
        self.ExceptionType = ExceptionType

    @contextlib.contextmanager
    def contextmanager(self):
        try:
            yield
        except self.ExceptionType as e:
            warnings.warn(str(e), ExceptionAsWarning)
