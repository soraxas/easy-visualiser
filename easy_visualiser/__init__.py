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


def spawn_daemon_visualiser():
    """
    Spawn a visualiser in a separate process
    """

    import multiprocessing

    def __daemon_visualiser(port):
        import easy_visualiser as ev
        from easy_visualiser.input.remote_socket import RemoteControlProxyDatasource

        viz = ev.Visualiser()
        viz.register_datasource(RemoteControlProxyDatasource())
        return viz.run()

    p = multiprocessing.Process(target=__daemon_visualiser, args=(1,))
    # the following ensure that this process will gets killed when main process exit
    p.daemon = True
    p.start()
    return p
