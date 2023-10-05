import dearpygui.dearpygui as dpg

import easy_visualiser as ev


def program_closing():
    dirty_projects: List[Project] = list(
        filter(
            lambda _: STATE.is_project_dirty(_)
            and STATE.get_project_tab(_) is not None,
            STATE.projects,
        )
    )
    STATE.serialize_project_snapshots(dirty_projects)
    clean_projects: List[Project] = list(
        filter(
            lambda _: not STATE.is_project_dirty(_)
            and STATE.get_project_tab(_) is not None,
            STATE.projects,
        )
    )
    STATE.clear_project_backups(clean_projects)
    STATE.save_recent_projects()
    STATE.config.save()


import dataclasses
import uuid
import warnings
from typing import Callable, Dict, List, Optional


@dataclasses.dataclass
class EventType:
    name: str
    registered_callbacks: Dict[str, Callable]

    def __init__(self, name: str):
        self.name = name
        self.registered_callbacks = dict()

    def emit(self, *args, **kwargs):
        if len(self.registered_callbacks) == 0:
            warnings.warn(
                f"Event '{self.name}' is emitted, but no registered callbacks!"
            )
        for callback in self.registered_callbacks.values():
            callback(*args, **kwargs)

    def unregister(self, _uuid: str) -> Optional[Callable]:
        callable = self.registered_callbacks.pop(_uuid, None)
        if callable is None:
            warnings.warn(
                f"uuid handler '{_uuid}' is given to unregister, but none was found."
            )
        return callable

    def clear(self):
        self.registered_callbacks.clear()

    def register(self, callable: Callable) -> str:
        _uuid = str(uuid.uuid4())

        assert _uuid not in self.registered_callbacks
        self.registered_callbacks[_uuid] = callable
        return _uuid


@dataclasses.dataclass
class _EventRegistry:
    all_events: Dict[str, EventType]

    def __init__(self):
        self.all_events = dict()

    def __getattr__(self, name: str) -> EventType:
        try:
            return self.all_events[name]
        except KeyError:
            if not name.isupper():
                raise ValueError(f"Event name must be all caps, but was '{name}'")
            self.all_events[name] = EventType(name)
        return self.all_events[name]


Event = _EventRegistry()


class MenuBar:
    def __init__(self):
        button: int
        with dpg.menu_bar():
            with dpg.menu(label="File"):
                dpg.add_menu_item(
                    label="New project",
                    callback=Event.NEW_PROJECT.emit,
                )
                dpg.add_menu_item(
                    label="Load project",
                    callback=Event.SELECT_PROJECT_FILES.emit,
                )
                button = dpg.add_menu_item(
                    label="Save project",
                    enabled=False,
                    callback=Event.SAVE_PROJECT.emit,
                )
                Event.SELECT_HOME_TAB.register(
                    lambda b=button, *args, **kwargs: dpg.disable_item(b),
                )
                Event.SELECT_PROJECT_TAB.register(
                    lambda b=button, *args, **kwargs: dpg.enable_item(b),
                )
                Event.SELECT_HOME_TAB.emit()
                button = dpg.add_menu_item(
                    label="Save project as",
                    enabled=False,
                    callback=Event.SAVE_PROJECT_AS.emit,
                )
                Event.SELECT_HOME_TAB.register(
                    lambda b=button, *args, **kwargs: dpg.disable_item(b),
                )
                Event.SELECT_PROJECT_TAB.register(
                    lambda b=button, *args, **kwargs: dpg.enable_item(b),
                )
                button = dpg.add_menu_item(
                    label="Close project",
                    enabled=False,
                    callback=Event.CLOSE_PROJECT.emit,
                )
                Event.SELECT_HOME_TAB.register(
                    lambda b=button, *args, **kwargs: dpg.disable_item(b),
                )
                Event.SELECT_PROJECT_TAB.register(
                    lambda b=button, *args, **kwargs: dpg.enable_item(b),
                )
                dpg.add_menu_item(label="Exit", callback=dpg.stop_dearpygui)
            with dpg.menu(label="Edit"):
                dpg.add_menu_item(
                    label="Undo",
                    enabled=False,
                    callback=lambda s, a, u: signals.emit(Signal.UNDO_PROJECT_ACTION),
                )
                button = dpg.last_item()
                Event.SELECT_HOME_TAB.register(
                    lambda b=button, *args, **kwargs: dpg.disable_item(b),
                )
                Event.SELECT_PROJECT_TAB.register(
                    lambda b=button, *args, **kwargs: dpg.enable_item(b),
                )
                dpg.add_menu_item(
                    label="Redo",
                    enabled=False,
                    callback=lambda s, a, u: signals.emit(Signal.REDO_PROJECT_ACTION),
                )
                button = dpg.last_item()
                Event.SELECT_HOME_TAB.register(
                    lambda b=button, *args, **kwargs: dpg.disable_item(b),
                )
                Event.SELECT_PROJECT_TAB.register(
                    lambda b=button, *args, **kwargs: dpg.enable_item(b),
                )
            with dpg.menu(label="Settings"):
                dpg.add_menu_item(
                    label="Appearance",
                    callback=Event.SHOW_SETTINGS_APPEARANCE.emit,
                )
                dpg.add_menu_item(
                    label="Defaults",
                    callback=Event.SHOW_SETTINGS_DEFAULTS.emit,
                )
                dpg.add_menu_item(
                    label="Keybindings",
                    callback=Event.SHOW_SETTINGS_KEYBINDINGS.emit,
                )
                dpg.add_menu_item(
                    label="User-defined elements",
                    callback=Event.SHOW_SETTINGS_USER_DEFINED_ELEMENTS.emit,
                )
            # TODO: Tools?
            # - Calculate equivalent capacitance from (RQ) circuit
            # - Convert Y to sigma for Warburg elements
            with dpg.menu(label="Help"):
                dpg.add_menu_item(
                    label="Documentation",
                    callback=lambda: webbrowser.open(
                        "https://vyrjana.github.io/DearEIS"
                    ),
                )
                dpg.add_menu_item(label="About", callback=Event.SHOW_HELP_ABOUT.emit)
                dpg.add_menu_item(
                    label="Changelog",
                    callback=Event.SHOW_CHANGELOG.emit,
                )
                dpg.add_menu_item(
                    label="Check for updates",
                    callback=Event.CHECK_UPDATES.emit,
                )
                dpg.add_menu_item(
                    label="Licenses",
                    callback=Event.SHOW_HELP_LICENSES.emit,
                )


class HomeTab:
    def __init__(self):
        self.tab: int = dpg.generate_uuid()
        with dpg.tab(
            label="Home",
            order_mode=dpg.mvTabOrder_Fixed,
            tag=self.tab,
        ):
            dpg.add_text("Recent projects")
            self.recent_projects_table: int = dpg.generate_uuid()
            with dpg.child_window(border=False):
                dpg.add_image_button("texture_tag", tag="my_buton")

            return
            with dpg.child_window(border=False, width=-1, height=-24):
                with dpg.table(
                    borders_outerV=True,
                    borders_outerH=True,
                    borders_innerV=True,
                    borders_innerH=True,
                    scrollY=True,
                    freeze_rows=1,
                    height=-1,
                    tag=self.recent_projects_table,
                ):
                    dpg.add_table_column(width_fixed=True)
                    dpg.add_table_column(label="Filename")
                    dpg.add_table_column(width_fixed=True)
            with dpg.child_window(border=False):
                with dpg.group(horizontal=True):
                    dpg.add_button(
                        label="New project",
                        callback=lambda: signals.emit(Signal.NEW_PROJECT),
                    )
                    return
                    attach_tooltip(tooltips.home.new_project)
                    self.load_projects_button: int = dpg.generate_uuid()
                    dpg.add_button(
                        label="Load project(s)",
                        callback=lambda: signals.emit(Signal.SELECT_PROJECT_FILES),
                        tag=self.load_projects_button,
                    )
                    attach_tooltip(tooltips.home.load_projects)
                    self.merge_projects_button: int = dpg.generate_uuid()
                    dpg.add_button(
                        label="Merge projects",
                        callback=lambda: signals.emit(
                            Signal.SELECT_PROJECT_FILES,
                            merge=True,
                        ),
                        tag=self.merge_projects_button,
                    )
                    attach_tooltip(tooltips.home.merge_projects)
                    self.clear_recent_projects_button: int = dpg.generate_uuid()
                    dpg.add_button(
                        label="Clear recent projects",
                        callback=lambda: signals.emit(
                            Signal.CLEAR_RECENT_PROJECTS,
                            selected_projects=self.get_selected_projects(),
                        ),
                        tag=self.clear_recent_projects_button,
                    )
                    attach_tooltip(tooltips.home.clear_recent_projects)

    def update_recent_projects_table(self, paths: List[str]):
        assert type(paths) is list, paths
        dpg.delete_item(self.recent_projects_table, children_only=True, slot=1)
        for path in paths:
            if path.strip() == "":
                continue
            with dpg.table_row(
                parent=self.recent_projects_table,
            ):
                dpg.add_button(
                    label="Load",
                    callback=lambda s, a, u: signals.emit(
                        Signal.LOAD_PROJECT_FILES,
                        paths=[u],
                    ),
                    user_data=path,
                )
                attach_tooltip(tooltips.home.load)
                dpg.add_text(basename(path))
                attach_tooltip(path)
                dpg.add_checkbox(
                    user_data=path,
                    callback=lambda s, a, u: self.update_selection(),
                )
                attach_tooltip(tooltips.recent_projects.checkbox)
        self.update_selection()

    def update_selection(self):
        paths: List[str] = self.get_selected_projects()
        if len(paths) > 1:
            dpg.set_item_label(
                self.load_projects_button,
                "Load selected projects",
            )
            dpg.set_item_label(
                self.merge_projects_button,
                "Merge selected projects",
            )
            dpg.set_item_label(
                self.clear_recent_projects_button,
                "Clear selected recent projects",
            )
        elif len(paths) == 1:
            dpg.set_item_label(
                self.load_projects_button,
                "Load selected project",
            )
            dpg.set_item_label(
                self.merge_projects_button,
                "Merge selected projects",
            )
            dpg.set_item_label(
                self.clear_recent_projects_button,
                "Clear selected recent project",
            )
        else:
            dpg.set_item_label(
                self.load_projects_button,
                "Load project(s)",
            )
            dpg.set_item_label(
                self.merge_projects_button,
                "Merge projects",
            )
            dpg.set_item_label(
                self.clear_recent_projects_button,
                "Clear recent projects",
            )

    def get_selected_projects(self) -> List[str]:
        paths: List[str] = []
        row: int
        for row in dpg.get_item_children(self.recent_projects_table, slot=1):
            checkbox: int = dpg.get_item_children(row, slot=1)[-2]
            assert "Checkbox" in dpg.get_item_type(checkbox), dpg.get_item_type(
                checkbox
            )
            if dpg.get_value(checkbox):
                path: Optional[str] = dpg.get_item_user_data(checkbox)
                assert type(path) is str, path
                paths.append(path)
        return paths


class ProjectTabBar:
    def __init__(self):
        self.tab_bar: int = dpg.generate_uuid()
        with dpg.tab_bar(
            callback=lambda s, a, u: (
                Event.SELECT_PROJECT_TAB
                if dpg.get_item_user_data(a) is not None
                else Event.SELECT_HOME_TAB
            ).emit(uuid=dpg.get_item_user_data(a)),
            tag=self.tab_bar,
        ):
            self.home_tab: HomeTab = HomeTab()

    def select_tab(self, project_tab: "ProjectTab"):
        dpg.set_value(self.tab_bar, project_tab.tab)

    def select_home_tab(self):
        dpg.set_value(self.tab_bar, self.home_tab.tab)

    def select_next_tab(self):
        tabs: List[int] = dpg.get_item_children(self.tab_bar, slot=1)
        index: int = tabs.index(dpg.get_value(self.tab_bar)) + 1
        dpg.set_value(self.tab_bar, tabs[index % len(tabs)])

    def select_previous_tab(self):
        tabs: List[int] = dpg.get_item_children(self.tab_bar, slot=1)
        index: int = tabs.index(dpg.get_value(self.tab_bar)) - 1
        dpg.set_value(self.tab_bar, tabs[index % len(tabs)])


import numpy as np

raw_data = np.zeros([500, 500, 4], dtype=np.float32)


def initialize_program(**kwargs):
    print(kwargs, "ok")
    dpg.set_viewport_resize_callback(dpg_resize)

    raw_data[:] = [1.0, 0.0, 1.0, 1.0]
    with dpg.texture_registry(
        # show=True
    ):
        dpg.add_raw_texture(
            width=500,
            height=500,
            default_value=raw_data,
            format=dpg.mvFormat_Float_rgba,
            tag="texture_tag",
        )

    window: int = dpg.generate_uuid()
    with dpg.window(tag=window):
        menu_bar: MenuBar = MenuBar()
        project_tab_bar: ProjectTabBar = ProjectTabBar()

        # self.busy_message: BusyMessage = BusyMessage()
        # self.error_message: ErrorMessage = ErrorMessage()

        # with dpg.window(tag="vispy"):
        #     menu_bar: MenuBar = MenuBar()

    dpg.set_primary_window(window, True)

    def change_text(sender, app_data):
        dpg.set_value(
            "text_item",
            f"Mouse Button: {app_data[0]}, Down Time: {app_data[1]} seconds",
        )

    def mouse_move(sender, app_data, user_data, lol):
        mouse_control_active = dpg.is_item_active("my_buton")
        if mouse_control_active or dpg.is_item_hovered("my_buton"):
            canvas_mouse_pos = app_data - np.array(dpg.get_item_rect_min("my_buton"))
            print(canvas_mouse_pos)

            # print(sender, app_data, user_data, lol)
            # print(dpg.get_available_content_region("my_buton"))
            # print(dpg.get_item_source("my_buton"))
            # print(dpg.get_item_rect_size("my_buton"))
            # print(dpg.get_item_rect_min("my_buton"))
            print("activated", dpg.is_item_activated("my_buton"))
            # print("focused", dpg.is_item_focused("my_buton"))
            # print("active", dpg.is_item_active("my_buton"))
            print("hovered", dpg.is_item_hovered("my_buton"))

        # dpg.set_value("text_item", f"Mouse Button: {app_data[0]}, Down Time: {app_data[1]} seconds")

    with dpg.handler_registry():
        dpg.add_mouse_down_handler(callback=change_text)
        dpg.add_mouse_move_handler(callback=mouse_move)
    with dpg.window(width=500, height=300):
        dpg.add_text("Press any mouse button", tag="text_item")

    def update_dynamic_texture(sender, app_data, user_data):
        raw_data[:] = app_data

    with dpg.window(label="Tutorial"):
        # dpg.add_image_button("texture_tag", tag="my_buton")
        dpg.add_color_picker(
            (255, 0, 255, 255),
            label="Texture",
            no_side_preview=True,
            alpha_bar=True,
            width=200,
            callback=update_dynamic_texture,
        )


def dpg_resize():
    print("resize", dpg.get_viewport_width(), dpg.get_viewport_height())
    return
    global raw_data
    raw_data = np.zeros(
        [dpg.get_viewport_height() - 20, dpg.get_viewport_width() - 20, 4],
        dtype=np.float32,
    )
    print("setting")
    raw_data[:] = np.random.rand(*raw_data.shape)

    dpg.set_value("texture_tag", raw_data)
    print("setting ok")


import sys

import glfw
import numpy as np
import tqdm


class GlfwContextManager:
    def __enter__(self):
        self.__ctx = glfw.get_current_context()

    def __exit__(self, *args):
        glfw.make_context_current(self.__ctx)


glfw_ctxmgr = GlfwContextManager()

# print(glfw.get_current_context())
# exit()

from loguru import logger
from soraxas_toolbox.image import display as D

from easy_visualiser import Visualiser, spawn_local_visualiser

logger.remove()
logger.add(sys.stderr, level="INFO")
# viz = spawn_local_visualiser()

import threading


class VisualiserThread:
    def __init__(self) -> None:
        x = threading.Thread(target=self.__thread_runner, args=(), daemon=True)
        x.start()

    def __thread_runner(self):
        self.viz = Visualiser(
            # auto_add_default_plugins=False
        )
        print("RUNNNNN")
        self.viz.run()


viz_thread = VisualiserThread()
import time

time.sleep(0.5)
viz = viz_thread.viz
# viz = Visualiser()


# def thread_function(arg):
#     while viz:
#         # with glfw_ctxmgr:
#         # viz.canvas._backend._context.make_current()

#         viz.scatter(np.random.rand(N, 3).tolist())
#         # # time.sleep(1)


#         # # viz.spin_until_keypress()
#         # # pbar.update()
#         # # print(viz.canvas.get_frame())
#         # # print(dir(viz.app))
#         # # print(viz.canvas.CAN)
#         # # print(type(viz.canvas.CAN))
#         # # print(dir(viz.canvas._backend))
#         # # print((viz.canvas._backend))
#         # # print((viz.canvas._backend))
#         # # print((viz.canvas._backend))
#         # # asd
#         # # print(viz.canvas._backend.get_frame())
#         # D(viz.canvas._backend.get_frame())
#         # continue
#         raw_data[:]=(viz.get_frame().astype(float)/255)
#         # raw_data[:]=(np.asarray(viz.get_frame()).reshape(500, 500, 4).astype(float)/255)
#         # break
# import threading

# x = threading.Thread(target=thread_function, args=(1,), daemon=True)
# x.start()

# viz.canvas._backend.handle_event(
#     {
#         "event_type": "resize",
#         "width": 500,
#         "height": 500,
#         "pixel_ratio": 1,
#     }
# )

dpg.create_context()


# args: Namespace = parse_arguments()
dpg.create_viewport(title="DearEIS")
dpg.set_viewport_min_width(800)
dpg.set_viewport_min_height(600)
dpg.setup_dearpygui()
dpg.show_viewport()
# dpg.show_style_editor()
# dpg.show_item_registry()
try:
    dpg.set_frame_callback(1, initialize_program, user_data="hi")
    dpg.set_exit_callback(program_closing)
    # dpg.start_dearpygui()

    import sys

    N = 20
    i = 0
    while dpg.is_dearpygui_running():
        i += 1

        viz_thread.viz.scatter(np.random.rand(N, 3).tolist())
        viz_thread.viz.get_frame()

        # Start and stop the video stream
        # if dpg.is_item_clicked("BtnStart"):
        #     run = 1
        # elif dpg.is_item_clicked("BtnStop"):
        #     run = 0

        # if run == 1:
        # stream()
        # raw_data[:] = np.random.rand(*raw_data.shape)

        # if i > 50:
        # with tqdm.tqdm() as pbar:
        # print(
        #     viz.canvas._backend.handle_event(
        #         {
        #             "event_type": "resize",
        #             "width": 500,
        #             "height": 500,
        #             "pixel_ratio": 1,
        #         }
        #     )
        # )

        # while viz:
        #     # with glfw_ctxmgr:
        #     # viz.canvas._backend._context.make_current()

        #     # viz.scatter(np.random.rand(N, 3).tolist())
        #     # # time.sleep(1)

        #     # # viz.spin_until_keypress()
        #     # # pbar.update()
        #     # # print(viz.canvas.get_frame())
        #     # # print(dir(viz.app))
        #     # # print(viz.canvas.CAN)
        #     # # print(type(viz.canvas.CAN))
        #     # # print(dir(viz.canvas._backend))
        #     # # print((viz.canvas._backend))
        #     # # print((viz.canvas._backend))
        #     # # print((viz.canvas._backend))
        #     # # asd
        #     # # print(viz.canvas._backend.get_frame())
        #     # D(viz.canvas._backend.get_frame())
        #     raw_data[:]=(np.asarray(viz.get_frame()).reshape(500, 500, 4).astype(float)/255)
        #     break

        # print(dir(viz.app._backend))

        # print(raw_data)
        # print(viz.canvas.CAN.get_frame())
        # print(raw_data.shape)
        # print(viz.canvas.CAN.get_frame().shape)

        # raw_data[:] = viz.canvas._backend.get_frame().astype(np.float32) / 255

        dpg.render_dearpygui_frame()
except Exception:
    print(format_exc())
finally:
    dpg.destroy_context()

exit()


import sys

from loguru import logger

from easy_visualiser.proxy.remote_socket import RemoteControlProxyDatasource

logger.remove()
logger.add(sys.stderr, level="TRACE")

viz = ev.Visualiser()

viz.register_datasource(RemoteControlProxyDatasource())

viz.run()
viz.spin_until_keypress()

exit()

# v=ev.Visualiser()
# v.spin_once()
# v.spin_once()
# v.spin_once()
# while v:
#     v.spin_once()


# import time

# time.sleep(4)


# exit()

v2 = ev.gcv()

v2.spin_until_keypress()


v = ev.Visualiser()

v.spin_until_keypress()
print("..")

print(ev.gcv())

ev.gcv().spin_until_keypress()
