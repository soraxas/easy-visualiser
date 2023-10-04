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


def get_remote_visualiser(uri=None) -> Visualiser:
    from .input.remote_socket import EasyVisualiserClientProxy

    viz = EasyVisualiserClientProxy(uri=uri)

    return viz


def spawn_daemon_visualiser() -> str:
    """
    Spawn a visualiser in a separate process
    """

    import multiprocessing

    def __daemon_visualiser(uri_return_queue):
        import easy_visualiser as ev
        from easy_visualiser.input.remote_socket import RemoteControlProxyDatasource

        viz = ev.Visualiser()
        viz.register_datasource(RemoteControlProxyDatasource(uri_return_queue))
        print("ok-<<-")
        viz.run()
        print("ok")
        exit()

    import multiprocessing

    uri_return_queue = multiprocessing.Queue()
    p = multiprocessing.Process(target=__daemon_visualiser, args=(uri_return_queue,))
    # the following ensure that this process will gets killed when main process exit
    p.daemon = True
    p.start()
    return uri_return_queue.get()


def spawn_local_visualiser() -> Visualiser:
    from .input.remote_socket import EasyVisualiserClientProxy

    return EasyVisualiserClientProxy(uri=spawn_daemon_visualiser())
