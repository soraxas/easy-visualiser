from .visualiser import Visualiser

GLOBAL_visualiser = None


def gcv() -> Visualiser:
    """
    Get current global instance of visualiser
    """

    global GLOBAL_visualiser
    if GLOBAL_visualiser is None:
        GLOBAL_visualiser = Visualiser()
    return GLOBAL_visualiser
