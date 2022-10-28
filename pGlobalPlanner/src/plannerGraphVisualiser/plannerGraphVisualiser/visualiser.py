from itertools import chain

from vispy.color import get_colormap

from ._impl import *
from typing import List, Type

from .abstract_visualisable_plugin import (
    VisualisablePlugin,
    ToggleableMixin,
    VisualisablePluginInitialisationError,
)
from .modal_control import ModalControl, ModalState


class Visualiser:
    plugin_registry: List[Type[VisualisablePlugin]] = []
    polling_registry: List[VisualisablePlugin] = []
    plugins: List[VisualisablePlugin] = []

    def __init__(self, args):
        self.args = args

        self.start_markers = None
        self.goal_markers = None
        self.axis_visual = None
        self.current_modal = ModalState()

        self.args.z_scaler = Zscaler(z_scale_factor=self.args.z_scale_factor)

        # colormap = get_colormap("viridis")
        # colormap = get_colormap("jet")
        # colormap = get_colormap("plasma")
        args.colormap = get_colormap(args.colormap)

        cbar_widget = scene.ColorBarWidget(
            label="Cost",
            clim=(0, 99),
            cmap=args.colormap,
            orientation="right",
            border_width=1,
            label_color="#ffffff",
        )
        cbar_widget.border_color = "#212121"
        args.cbar_widget = cbar_widget

        grid = args.canvas.central_widget.add_grid(margin=10)

        # col num just to make it on the right size (0 is left)
        grid.add_widget(col=10)
        grid.add_widget(cbar_widget, col=10, row_span=9)
        self.status_bar = scene.Label(
            "",
            color="white",
            anchor_x="left",
            anchor_y="bottom",
            pos=[0, 0],
        )
        grid.add_widget(
            self.status_bar,
            col=0,
            row=0,
            row_span=1,
        )

        #     scene.Label(
        #         "\n".join(
        #             "Press [{key}] to {functionality}".format(
        #                 key=cb[0], functionality=cb[1]
        #             )
        #             for cb in chain(
        #                 *(
        #                     p.keys
        #                     for p in args.vis.plugins
        #                     if isinstance(p, ToggleableMixin)
        #                 )
        #             )
        #         ),
        #         color="white",
        #         anchor_x="left",
        #         anchor_y="bottom",
        #         pos=[0, 0],
        #     ),
        #     col=0,
        #     row=8,
        #     row_span=2,
        self.initialised = False

    def initialise(self):
        self.plugins = []
        for pcls in self.plugin_registry:
            try:
                self.plugins.append(pcls(self.args))
            except VisualisablePluginInitialisationError as e:
                print(str(e))
        self.update_status()

        @self.args.canvas.connect
        def on_key_press(ev):
            def process():
                # print(ev.key.name)
                for plugin in (
                    p for p in self.plugins if isinstance(p, ToggleableMixin)
                ):

                    if self.current_modal.state is None:
                        # selecting modal
                        for registered_modal in plugin.keys:

                            if isinstance(registered_modal, tuple):
                                continue
                            registered_modal: ModalControl

                            if registered_modal.key.match(ev.key.name):
                                self.current_modal.state = registered_modal
                                return True
                    else:
                        # operating within modal
                        if ModalState.quit_key.match(ev.key.name):
                            self.current_modal.state = None
                            return True
                        for _key, _, cb in self.current_modal.state.mappings:
                            if _key.match(ev.key.name.upper()):
                                cb()
                                return True

            result = process()
            self.update_status()
            return result

    def update_status(self):
        if self.current_modal.state is not None:
            msg = f">>>>>  {self.current_modal.state.modal_name}\n\n"

            msg += "\n".join(
                f"Press [{k}] to {msg}"
                for k, msg, _ in self.current_modal.state.mappings
            )

            msg += f"\n\n\n\nPress [{ModalState.quit_key}] to exit current modal"

            self.status_bar.text = msg

        else:
            msg = "~~~~~~~~~~ Directory ~~~~~~~~~\n\n"
            msg += "\n".join(
                "Press [{key}] to {functionality}".format(
                    key=cb.key, functionality=f"control {cb.modal_name}"
                )
                for cb in chain(
                    *(p.keys for p in self.plugins if isinstance(p, ToggleableMixin))
                )
            )

            self.status_bar.text = msg

    def register_plugin(self, plugin_cls: Type[VisualisablePlugin]):
        self.plugin_registry.append(plugin_cls)

    def update(self):
        for plugin in self.plugins:
            plugin.update()
        self.initialised = True
