import enum
import math
import os
import pathlib
import time
from typing import Dict, List

import numpy as np
import vispy
from scipy.interpolate import NearestNDInterpolator
from vispy import app
from vispy.scene import Mesh, transforms

from easy_visualiser.key_mapping import Key
from easy_visualiser.modal_control import ModalControl
from easy_visualiser.plugin_capability import GuardableMixin, TriggerableMixin
from easy_visualiser.plugins import VisualisablePlugin

PITCH_ANGLE_CHANNEL_NAME = "VEHICLE_ANGLE"
SWARM_VEHICLES_REPORT_CHANNEL_NAME = "NODE_REPORT_LOCAL"


class SwarmModelType(enum.Enum):
    auv = 0
    submarine = 1
    simple_sphere = 2
    END_OF_ENUM = 3


ASSETS_ROOT = pathlib.Path(os.path.dirname(os.path.realpath(__file__))) / "assets"

SWARM_MODEL_MAPPING = {
    SwarmModelType.auv: ASSETS_ROOT / "AUV_mesh.stl",
    SwarmModelType.submarine: ASSETS_ROOT / "floating_submarine.stl",
    SwarmModelType.simple_sphere: ASSETS_ROOT / "300_poly_sphere.stl",
}


class Vehicle:
    def __init__(self, datastring: List[str]):
        self.data = dict()
        self.update(datastring)

    def update(self, datastring: List[str]):
        self.data = {v[0]: v[1] for v in datastring}

    def float(self, key: str):
        return float(self.data[key])

    @property
    def name(self) -> str:
        return self.data["NAME"]

    @property
    def pos(self) -> List[float]:
        return [
            self.float("X"),
            self.float("Y"),
            -self.float("DEP"),
        ]

    def __repr__(self):
        return self.data.__repr__()


class VisualisableMoosSwarm(
    GuardableMixin,
    TriggerableMixin,
    # UpdatableMixin,
    VisualisablePlugin,
):
    bathy_mesh = None
    bathy_intert: NearestNDInterpolator = None

    def __init__(self, swarm_model_type: str):
        super().__init__(swarm_model_type)
        # cast string arg to enum
        self.swarm_model_type = SwarmModelType[swarm_model_type]

        from easy_visualiser.input.moos import MoosComm

        self.moos = MoosComm.get_instance()
        self.moos.register_variable(
            SWARM_VEHICLES_REPORT_CHANNEL_NAME, self.moos_vehicle_msg_cb
        )
        self.moos.register_variable(
            PITCH_ANGLE_CHANNEL_NAME, self.moos_vehicle_angle_cb
        )

        # self.moos = pMoosVisualiser(self.refresh)
        self.vehicle_visual: Dict[str, Mesh] = dict()
        self.throttle_last_update = time.time()

        self.vehicles: Dict[Vehicle] = dict()
        self.current_vehicle_angle: float = 0
        self.vehicle_scale = 500
        # self.vehicle_scale = 10
        self.auto_zoom_timer = app.Timer(
            interval=2,
            connect=lambda ev: self.__center_view(),
            iterations=-1,
        )
        self.add_mapping(
            ModalControl(
                "m",
                [
                    (
                        Key(["+", "="]),
                        "increase scale",
                        lambda: self.__scale_cb(1.5),
                    ),
                    (
                        Key(["-", "_"]),
                        "decrease scale",
                        lambda: self.__scale_cb(0.5),
                    ),
                    (
                        Key(["z"]),
                        "zoom to swarm",
                        self.__zoom_cb,
                    ),
                    (
                        Key(["c"]),
                        "toggle auto center view",
                        self.__toggle_auto_zoom_cb,
                    ),
                    (
                        Key(["a"]),
                        "change swarm appearance",
                        self.__change_swarm_appearance_cb,
                    ),
                ],
                modal_name="moos swarm",
            )
        )

    def moos_vehicle_msg_cb(self, msg):
        data_list = list(pair.split("=") for pair in msg.string().split(","))
        for k, v in data_list:
            if k == "NAME":
                if v not in self.vehicles:
                    self.vehicles[v] = Vehicle(data_list)
                else:
                    self.vehicles[v].update(data_list)
                break
        self.on_update()

    def moos_vehicle_angle_cb(self, msg):
        self.current_vehicle_angle = msg.double()

    def __scale_cb(self, num):
        self.vehicle_scale *= num
        self.on_update()

    @property
    def name(self):
        return "moos_swarm"

    def construct_plugin(self) -> None:
        super().construct_plugin()

        # self.axis_visual = XYZAxis(
        #     parent=self.visualiser.visual_parent,
        #     width=5,
        # )

    def __toggle_auto_zoom_cb(self):
        self.__center_view()
        if self.auto_zoom_timer.running:
            self.auto_zoom_timer.stop()
        else:
            self.auto_zoom_timer.start()

    def __zoom_cb(self):
        if len(self.vehicles) < 1:
            return
        poses = np.array([v.pos for v in self.vehicles.values()])
        poses[:, 2] = self.other_plugins.zscaler.scaler(poses[:, 2])

        margin = 200
        bounds = np.stack([poses.min(0) - margin, poses.max(0) + margin]).T

        self.set_range(*bounds)

    def __center_view(self):
        poses = np.array([v.pos for v in self.vehicles.values()])
        poses[:, 2] = self.other_plugins.zscaler.scaler(poses[:, 2])
        self.visualiser.view.camera.center = np.array(poses).mean(0)

    def __change_swarm_appearance_cb(self):
        val = self.swarm_model_type.value
        val += 1
        if val >= SwarmModelType.END_OF_ENUM.value:
            val = 0
        self.swarm_model_type = SwarmModelType(val)
        for visual in self.vehicle_visual.values():
            visual.parent = None
            del visual
        self.vehicle_visual.clear()
        self.on_update()

    def on_update_guard(self) -> bool:
        return (
            self.other_plugins.bathymetry.last_min_max_pos is not None
            and self.visualiser.initialised
        )

    def refresh(self):
        pass

    def on_update(self) -> None:
        _now = time.time()
        if _now - self.throttle_last_update < 0.08:
            return
        if not self.on_update_guard():
            return
        self.throttle_last_update = _now

        for n, v in self.vehicles.items():
            if v.name not in self.vehicle_visual:
                with open(SWARM_MODEL_MAPPING[self.swarm_model_type], "rb") as f:
                    data = vispy.io.stl.load_stl(f)
                vertices, faces, normals = (
                    data["vertices"],
                    data["faces"],
                    data["face_normals"],
                )
                # self.vehicle_visual[v.name] = Markers(
                #     symbol="triangle_up",
                #     # faces=faces,
                #     # color=(0.5, 0.7, 0.5, 1),
                #     parent=self.visualiser.visual_parent,
                #     # shading="smooth",
                # )
                self.vehicle_visual[v.name] = Mesh(
                    vertices=vertices,
                    faces=faces,
                    color=(0.5, 0.7, 0.5, 1),
                    parent=self.visualiser.visual_parent,
                    shading="smooth",
                )

                # self.vehicle_visual[v.name].transform.scale([2000.1] * 3)

                # self.vehicle_visual[v.name].set_data()

                # print("built")

            self.vehicle_visual[v.name].transform = transforms.MatrixTransform()
            self.vehicle_visual[v.name].transform.scale([self.vehicle_scale] * 3)

            # self.vehicle_visual[v.name].transform = transforms.MatrixTransform()
            #
            # # self.vehicle_visual[v.name].transform.scale([2000.1] * 3)
            # self.vehicle_visual[v.name].transform.scale([self.vehicle_scale] * 3)
            # # # Create a colored `MeshVisual`.
            # # mesh = Mesh(vertices, faces, color=(.5, .7, .5, 1),
            # #             parent=self.visualiser.visual_parent,
            # #             shading='smooth')
            # # self.vehicle_visual[v.name].transform.rotate(90, (1, 0, 0))
            #
            # # self.vehicle_visual[v.name].transform.rotate(
            # #     self.vehicles[v.name].float("YAW") * 180 / np.pi, (0, 0, 1)
            # # )
            #
            # # view.add(self.vehicle_visual[v.name])
            # # print(self.vehicles[v.name])
            pos = self.vehicles[v.name].pos
            pos[2] = self.other_plugins.zscaler.scaler(pos[2])
            # print(np.array(pos).reshape(1, -1))

            # self.vehicle_visual[v.name].set_data(
            #     pos=np.array(pos).reshape(1, -1), scaling=1000, size=10000
            # )
            # print(pos)

            # # self.vehicle_visual[v.name].transform.translate(pos)
            # continue

            # print(pos)
            # print(self.vehicles[v.name].float('X'), )
            # self.vehicle_visual[v.name].transform.translate([1, 2, 3])

            # scale the pitch angle according to the z axis exaggerated scale
            _scaled_pitch_angle = math.atan(
                self.other_plugins.zscaler.scaler(math.tan(self.current_vehicle_angle))
            )

            self.vehicle_visual[v.name].transform.rotate(
                _scaled_pitch_angle * 180 / np.pi,
                (0, 1, 0),
            )
            # print(_scaled_pitch_angle)
            self.vehicle_visual[v.name].transform.rotate(
                (np.pi + self.vehicles[v.name].float("YAW")) * 180 / np.pi,
                (0, 0, 1),
            )

            # print(self.vehicle_visual[v.name].transform.matrix)
            mat = self.vehicle_visual[v.name].transform.matrix
            # print(mat)

            # mat[:, :] = utran.rotate(
            #     self.vehicles[v.name].float("YAW") * 180 / np.pi, (0, 0, 1))
            # mat[3, :3] = self.other_plugins.bathymetry.last_min_max_pos
            mat[3, :3] = pos

            self.vehicle_visual[v.name].transform.matrix = mat
