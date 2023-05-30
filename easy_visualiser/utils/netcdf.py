from typing import List

import netCDF4
import numpy as np


class PlottableNetCDF4:
    """
    E.g.

    dataset = netCDF4.Dataset(
        args.data_path,
    )

    plottable = PlottableNetCDF4(dataset, "sound")

    sound_speed = plottable.get_array(
        "sound",
        filter_valid=True,
        force_using_timestep=1,
        # fill_value=plottable.get_array("sound").min()
        fill_value=np.nan,
        # fill_value=1000
    )
    sound_speed = sound_speed[0, ...]
    sound_speed = np.moveaxis(sound_speed, 0, -1)

    scale = 2
    data = dict()
    botz = plottable.get_array("botz", filter_missing=True)
    botz = np.rollaxis(botz, 1)
    botz = -botz
    botz = resize(botz, (botz.shape[0] * scale, botz.shape[1] * scale))

    zc = plottable.get_array("zc")
    zc_bounds = [zc.min(), zc.max() + 100]
    data['sound_speed'] = sound_speed
    data['botz'] = botz
    data['zc'] = zc

    """

    def __init__(self, dataset: netCDF4.Dataset, variable: str):
        self.dataset = dataset
        self.variable = variable

    def _get_var(self, var: str) -> netCDF4.Variable:
        return self.dataset.variables[var]

    def get_array(
        self,
        var: str,
        filter_valid: bool = False,
        filter_missing: bool = False,
        fill_value=0,
        force_using_timestep=None,
    ):
        variable = self._get_var(var)
        _var = variable
        if force_using_timestep is not None:
            _var = variable[force_using_timestep : force_using_timestep + 1, ...]
        array = np.array(_var).astype(np.float32)
        if filter_valid:
            valid_range = variable.valid_range
            array[(array < valid_range[0]) | (array > valid_range[1])] = fill_value
        if filter_missing:
            missing_value = variable.missing_value
            array[array == missing_value] = fill_value
        return array

    def get_coordinates(self, coordinates: str) -> List[np.ndarray]:
        return [self.get_array(var) for var in coordinates.split(" ")]

    def get_coordinates_array_of_var(self, var: str) -> List[np.ndarray]:
        return self.get_coordinates(self.get_coordinates_of_var(var))

    def get_coordinates_of_var(self, var: str) -> str:
        return self._get_var(var).coordinates
