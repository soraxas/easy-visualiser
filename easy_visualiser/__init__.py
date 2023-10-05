from .visualiser import Visualiser

GLOBAL_visualiser = None


def gcv(process_type: str = None) -> Visualiser:
    """
    Get current global instance of visualiser
    """

    global GLOBAL_visualiser
    if GLOBAL_visualiser is None:
        GLOBAL_visualiser = get_visualiser_with_process_type(process_type=process_type)
    return GLOBAL_visualiser


def get_visualiser_with_process_type(process_type: str):
    process_type = process_type.lower()
    if process_type is None:
        return Visualiser()
    if process_type == "thread":
        import queue
        from dataclasses import dataclass

        from easy_visualiser.input.remote_control_proxy import (
            RemoteControlProxyDatasource,
            RemoteControlProxyQueue,
        )
        from easy_visualiser.proxy.remote_thread import VisualiserThread

        @dataclass
        class PyroDaemonIO(RemoteControlProxyQueue):
            input_queue = queue.Queue()
            output_queue = queue.Queue()

        _queue = PyroDaemonIO()
        thread = VisualiserThread(_queue)
        thread.start()
        print("started!")

        from .proxy.visualiser_proxy import (
            EasyVisualiserClientProxy,
            VisualiserServerIO,
        )

        return EasyVisualiserClientProxy(
            VisualiserServerIO(_queue.input_queue, _queue.output_queue)
        )

    if process_type in ("process", "pyro", "multiprocessing", "socket"):
        return spawn_local_visualiser()


def get_remote_visualiser(uri=None) -> Visualiser:
    from .proxy.visualiser_proxy import EasyVisualiserClientProxy

    port = 9413
    if uri is None:
        uri = f"PYRO:easy_visualiser.Visualiser@localhost:{port}"
    import Pyro5

    viz = EasyVisualiserClientProxy(Pyro5.api.Proxy(uri))

    return viz


def spawn_daemon_visualiser() -> str:
    """
    Spawn a visualiser in a separate process
    """

    import multiprocessing

    def __daemon_visualiser(uri_return_queue):
        import easy_visualiser as ev

        from .proxy.remote_socket import build_remote_datasource

        viz = ev.Visualiser()
        viz.register_datasource(build_remote_datasource(uri_return_queue))
        # print("ok-<<-")
        viz.run()
        # print("ok")
        exit()

    import multiprocessing

    uri_return_queue = multiprocessing.Queue()
    p = multiprocessing.Process(target=__daemon_visualiser, args=(uri_return_queue,))
    # the following ensure that this process will gets killed when main process exit
    p.daemon = True
    p.start()
    return uri_return_queue.get()


def spawn_local_visualiser() -> Visualiser:
    import Pyro5

    from .proxy.visualiser_proxy import EasyVisualiserClientProxy

    return EasyVisualiserClientProxy(Pyro5.api.Proxy(spawn_daemon_visualiser()))
