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


def get_remote_visualiser() -> Visualiser:
    from .input.remote_socket import EasyVisualiserClientProxy

    viz = EasyVisualiserClientProxy()

    return viz
