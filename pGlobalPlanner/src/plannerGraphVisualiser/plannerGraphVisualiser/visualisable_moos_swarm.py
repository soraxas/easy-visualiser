import enum
import os
import pymoos as moos
import traceback
from typing import Tuple, Optional, Dict, Callable, List
import time
import pathlib

import numpy as np
import vispy
from scipy.interpolate import griddata, NearestNDInterpolator
from vispy.scene import XYZAxis, Mesh, Markers
from vispy.scene import transforms

from plannerGraphVisualiser.abstract_visualisable_plugin import (
    VisualisablePlugin,
    UpdatableMixin,
    GuardableMixin,
    ToggleableMixin,
    VisualisablePluginInitialisationError,
)

from plannerGraphVisualiser.modal_control import ModalControl, Key

PITCH_ANGLE_CHANNEL_NAME = "VEHICLE_ANGLE"
SWARM_VEHICLES_REPORT_CHANNEL_NAME = "NODE_REPORT_LOCAL"


class SwarmModelType(enum.Enum):
    auv = 0
    simple_sphere = 1
    END_OF_ENUM = 2


ASSETS_ROOT = pathlib.Path(os.path.dirname(os.path.realpath(__file__))) / "assets"

SWARM_MODEL_MAPPING = {
    SwarmModelType.auv: ASSETS_ROOT / "floating_submarine.stl",
    SwarmModelType.simple_sphere: ASSETS_ROOT / "300_poly_sphere.stl",
}


class pMoosVisualiser(moos.comms):
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

    def __init__(self, refresh_cb: Callable):
        super().__init__()
        self.connect_to_moos("localhost", 9000)
        self.refresh_cb = refresh_cb

        self.depths = None
        self.currents = None

        self.use_real_map = True
        self.current_vehicle_angle = 0

        self.vehicles: Dict[pMoosVisualiser.Vehicle] = dict()

    def connect_to_moos(self, moos_host, moos_port):
        self.set_on_connect_callback(self.__on_connect)
        self.set_on_mail_callback(self.__on_new_mail)
        self.run(moos_host, moos_port, self.__class__.__name__)
        if not self.wait_until_connected(2000):
            self.close(True)
            raise VisualisablePluginInitialisationError(
                VisualisableMoosSwarm, "Failed to connect to local MOOSDB"
            )

    def __on_connect(self):
        self.register(SWARM_VEHICLES_REPORT_CHANNEL_NAME, 0)
        self.register(PITCH_ANGLE_CHANNEL_NAME, 0)
        return True

    def __on_new_mail(self):
        try:
            for msg in self.fetch():
                # print(msg.key(), )
                if msg.key() == SWARM_VEHICLES_REPORT_CHANNEL_NAME:
                    # print(msg.string())
                    data_list = list(
                        pair.split("=") for pair in msg.string().split(",")
                    )
                    for k, v in data_list:
                        if k == "NAME":
                            if v not in self.vehicles:
                                self.vehicles[v] = pMoosVisualiser.Vehicle(data_list)
                            else:
                                self.vehicles[v].update(data_list)
                            break
                elif msg.key() == PITCH_ANGLE_CHANNEL_NAME:
                    self.current_vehicle_angle = -msg.double()

            self.refresh_cb()

            # print(msg.key(), msg.string())

            # if msg.key() == OCEAN_CURRENT_VARIABLE:
            #     self.currents = json.loads(msg.string())
            # elif msg.key() == DEPTH_POINTS_VARIABLE:
            #     self.depths = json.loads(msg.string())
        except Exception as e:
            traceback.print_exc()
            return False
        return True


class VisualisableMoosSwarm(
    GuardableMixin,
    ToggleableMixin,
    # UpdatableMixin,
    VisualisablePlugin,
):
    bathy_mesh = None
    bathy_intert: NearestNDInterpolator = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # cast string arg to enum
        self.args.swarm_model_type = SwarmModelType[self.args.swarm_model_type]
        self.moos = pMoosVisualiser(self.on_update)
        # self.moos = pMoosVisualiser(self.refresh)
        self.vehicle_visual: Dict[str, Mesh] = dict()
        self.throttle_last_update = time.time()
        self.vehicle_scale = 500
        # self.vehicle_scale = 10
        self.keys = [
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
                        Key(["a"]),
                        "change swarm appearance",
                        self.__change_swarm_appearance_cb,
                    ),
                ],
                modal_name="moos swarm",
            )
        ]

    def __scale_cb(self, num):
        self.vehicle_scale *= num
        self.on_update()

    @property
    def name(self):
        return "moos_swarm"

    @property
    def target_file(self) -> str:
        return self.args.depth_datapath

    def construct_plugin(self) -> None:
        super().construct_plugin()

        # self.axis_visual = XYZAxis(
        #     parent=self.args.view.scene,
        #     width=5,
        # )

    def __zoom_cb(self):
        if len(self.moos.vehicles) < 1:
            return
        poses = np.array([v.pos for v in self.moos.vehicles.values()])
        poses[:, 2] = self.args.z_scaler(poses[:, 2])

        margin = 200
        bounds = np.stack([poses.min(0) - margin, poses.max(0) + margin]).T

        # icecream.ic(bounds)
        # print(self.moos.vehicles)
        # riesnt
        self.set_range(*bounds)

    def __change_swarm_appearance_cb(self):
        val = self.args.swarm_model_type.value
        val += 1
        if val >= SwarmModelType.END_OF_ENUM.value:
            val = 0
        self.args.swarm_model_type = SwarmModelType(val)
        for visual in self.vehicle_visual.values():
            visual.parent = None
            del visual
        self.vehicle_visual.clear()
        self.on_update()

    def on_update_guard(self) -> bool:
        return (
            self.other_plugins_mapper["bathymetry"].last_min_pos is not None
            and self.args.vis.initialised
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

        for n, v in self.moos.vehicles.items():
            if v.name not in self.vehicle_visual:
                with open(SWARM_MODEL_MAPPING[self.args.swarm_model_type], "rb") as f:
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
                #     parent=self.args.view.scene,
                #     # shading="smooth",
                # )
                self.vehicle_visual[v.name] = Mesh(
                    vertices=vertices,
                    faces=faces,
                    color=(0.5, 0.7, 0.5, 1),
                    parent=self.args.view.scene,
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
            # #             parent=self.args.view.scene,
            # #             shading='smooth')
            # # self.vehicle_visual[v.name].transform.rotate(90, (1, 0, 0))
            #
            # # self.vehicle_visual[v.name].transform.rotate(
            # #     self.moos.vehicles[v.name].float("YAW") * 180 / np.pi, (0, 0, 1)
            # # )
            #
            # # view.add(self.vehicle_visual[v.name])
            # # print(self.moos.vehicles[v.name])
            pos = self.moos.vehicles[v.name].pos
            pos[2] = self.args.z_scaler(pos[2])
            # print(np.array(pos).reshape(1, -1))

            # self.vehicle_visual[v.name].set_data(
            #     pos=np.array(pos).reshape(1, -1), scaling=1000, size=10000
            # )
            # print(pos)

            # # self.vehicle_visual[v.name].transform.translate(pos)
            # continue

            # print(pos)
            # print(self.moos.vehicles[v.name].float('X'), )
            # self.vehicle_visual[v.name].transform.translate([1, 2, 3])
            self.vehicle_visual[v.name].transform.rotate(
                self.moos.current_vehicle_angle * 180 / np.pi,
                (0, 1, 0),
            )
            self.vehicle_visual[v.name].transform.rotate(
                (np.pi + self.moos.vehicles[v.name].float("YAW")) * 180 / np.pi,
                (0, 0, 1),
            )

            # print(self.vehicle_visual[v.name].transform.matrix)
            mat = self.vehicle_visual[v.name].transform.matrix
            # print(mat)

            # mat[:, :] = utran.rotate(
            #     self.moos.vehicles[v.name].float("YAW") * 180 / np.pi, (0, 0, 1))
            # mat[3, :3] = self.other_plugins_mapper["bathymetry"].last_min_pos
            mat[3, :3] = pos

            self.vehicle_visual[v.name].transform.matrix = mat

            # print(mat)

            # rsient
            # self.vehicle_visual[v.name].transform.translate = self.other_plugins_mapper["bathymetry"].last_min_pos
            # self.vehicle_visual[v.name].transform.translate = [0,0,-550]
            # break


# mon = pMoosVisualiser()
# import time
#
# while True:
#     time.sleep(1)
