from vispy.app.backends import _jupyter_rfb, _offscreen_util

ApplicationBackend = _jupyter_rfb.ApplicationBackend
# CanvasBackend = _jupyter_rfb.CanvasBackend
TimerBackend = _jupyter_rfb.TimerBackend

import asyncio

from jupyter_rfb import RemoteFrameBuffer
from vispy.app.backends._jupyter_rfb import FrameBufferHelper
from vispy.app.base import BaseApplicationBackend, BaseCanvasBackend, BaseTimerBackend


class CanvasBackend(_jupyter_rfb.CanvasBackend):
    def __init__(self, vispy_canvas, **kwargs):
        BaseCanvasBackend.__init__(self, vispy_canvas)
        RemoteFrameBuffer.__init__(self)
        # Use a context per canvas, because we seem to make assumptions
        # about OpenGL state being local to the canvas.
        self._context = (
            CustomOffscreenContext()
        )  # OffscreenContext.get_global_instance()
        self._helper = FrameBufferHelper()
        self._loop = asyncio.get_event_loop()
        self._logical_size = 1, 1
        self._physical_size = 1, 1
        self._lifecycle = 0  # 0: not initialized, 1: initialized, 2: closed
        # Init more based on kwargs (could maybe handle, title, show, context)
        self._vispy_set_size(*kwargs["size"])
        self.resizable = kwargs["resizable"]
        # Need a first update
        self._vispy_update()


class CustomOffscreenContext(_offscreen_util.OffscreenContext):
    """A helper class to provide an OpenGL context. This context is global
    to the application.
    """

    def __init__(self):
        if self._canvas is not None:
            return  # already initialized

        self._is_closed = False

        # Glfw is probably the most lightweight approach, so let's try that.
        # But there are two incompatible packages providing glfw :/
        self.glfw = None
        try:
            import glfw
        except ImportError:
            pass
        else:
            need_from_glfw = ["create_window", "make_context_current"]
            if all(hasattr(glfw, attr) for attr in need_from_glfw):
                self.glfw = glfw

        if self.glfw:
            self.glfw.init()
            self.glfw.window_hint(self.glfw.VISIBLE, 0)
            self._canvas = self.glfw.create_window(1, 1, "dummy window", None, None)
        else:
            try:
                _app = Application("default")
            except Exception:
                raise RuntimeError(
                    "Cannot find a backend to create an OpenGL context. "
                    "Install e.g. PyQt5, PySide2, or `pip install glfw`."
                )
            self._canvas = Canvas(app=_app)
            self._canvas.show(False)
