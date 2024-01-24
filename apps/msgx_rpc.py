import traceback

from easy_visualiser.input.msgx import MsgX
from easy_visualiser.visualiser import Visualiser


def run():
    visualiser = Visualiser(
        title="Msgx RPC",
        # auto_add_default_plugins=False,
    )

    visualiser.register_datasource(MsgX.get_instance())
    visualiser.initialise()

    def msgx_rpc(msg):
        try:
            args = msg.get("args", [])
            kwargs = msg.get("kwargs", {})

            getattr(visualiser, msg["method"])(*args, **kwargs)
        except Exception:
            print(traceback.format_exc())

    MsgX.get_instance().add_callback(msgx_rpc)

    visualiser.run()


if __name__ == "__main__":
    run()
