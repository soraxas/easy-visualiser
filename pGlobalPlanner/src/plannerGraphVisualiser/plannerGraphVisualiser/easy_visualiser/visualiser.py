import dataclasses
from vispy.color import get_colormap

from typing import List, Tuple, Dict, Callable

from .utils import AxisScaler

from plannerGraphVisualiser.easy_visualiser.plugins.abstract_visualisable_plugin import (
    VisualisablePlugin,
    VisualisablePluginInitialisationError,
)
from .plugin_capability import ToggleableMixin, WidgetsMixin, PluginState, WidgetOption
from .modal_control import ModalControl, ModalState


@dataclasses.dataclass
class VisualiserHooks:
    on_initialisation_finish: List[Callable]
    on_keypress_finish: List[Callable]


class Visualiser:
    polling_registry: List[VisualisablePlugin] = []
    plugins: List[VisualisablePlugin] = []

    def __init__(
        self,
        args,
    ):
        self.args = args

        self.start_markers = None
        self.goal_markers = None
        self.axis_visual = None
        self.current_modal = ModalState()
        self.hooks = VisualiserHooks([], [])

        self.args.z_scaler = AxisScaler(scale_factor=self.args.z_scale_factor)

        # colormap = get_colormap("viridis")
        # colormap = get_colormap("jet")
        # colormap = get_colormap("plasma")
        args.colormap = get_colormap(args.colormap)

        self.grid = args.canvas.central_widget.add_grid(margin=10)
        # col num just to make it on the right size (0 is left)
        self.grid.add_widget(col=10)

        self.initialised = False

    def initialise(self):
        for plugin in self.plugins:
            try:
                ###########################################################
                # build widget
                if isinstance(plugin, WidgetsMixin):
                    for widget, data in plugin.get_constructed_widgets():
                        self.grid.add_widget(widget, **data)
                ###########################################################
                # construct actual plugin
                if plugin.construct_plugin():
                    plugin.state = PluginState.OFF
                ###########################################################
                # register hooks
                plugin.on_initialisation_finish()
                ###########################################################

            except VisualisablePluginInitialisationError as e:
                print(str(e))
        for hook in self.hooks.on_initialisation_finish:
            hook()

        @self.args.canvas.connect
        def on_key_press(ev):
            def process():
                # print(ev.key.name)
                for _plugin in (
                    p for p in self.plugins if isinstance(p, ToggleableMixin)
                ):

                    if self.current_modal.state is None:
                        # selecting modal
                        for registered_modal in _plugin.keys:

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
                        for mappings in self.current_modal.state.mappings:
                            if mappings.key.match(ev.key.name.upper()):
                                mappings.callback()
                                return True

            result = process()
            for _hook in self.hooks.on_keypress_finish:
                _hook()
            return result

    def register_plugin(self, plugin: VisualisablePlugin):
        self.plugins.append(plugin)

    def update(self):
        for plugin in self.plugins:
            plugin.update()
        self.initialised = True
