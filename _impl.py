from vispy import scene

import numpy as np
import scipy
import scipy.stats

import os


def mean_confidence_interval(data, confidence=0.95):
    a = 1.0 * np.array(data)
    n = len(a)
    m, se = np.mean(a), scipy.stats.sem(a)
    h = se * scipy.stats.t.ppf((1 + confidence) / 2.0, n - 1)
    return m, m - h, m + h


class Wall:
    def __init__(self, xy_start, xy_goal, depth, bathy_interp):
        self.xy_start = xy_start
        self.xy_goal = xy_goal
        self.depth = depth
        self.start_idx = 0
        self.bathy_interp = bathy_interp

    def get_vertices(self):
        depth1 = -self.depth
        depth2 = -self.depth

        if self.bathy_interp is not None:
            # cut it off at the bathymetry
            depth1 = max(self.bathy_interp(*self.xy_start), -self.depth)
            depth2 = max(self.bathy_interp(*self.xy_goal), -self.depth)

        return (
            (*self.xy_start, 0),
            (*self.xy_start, depth1),
            (*self.xy_goal, 0),
            (*self.xy_goal, depth2),
        )

    def at(self, idx):
        return self.start_idx + idx

    def get_faces(self):
        return (self.at(0), self.at(1), self.at(2)), (
            self.at(1),
            self.at(2),
            self.at(3),
        )


class KeepoutZone:
    def __init__(self, depth, points, bathy_interp) -> None:
        self.walls = []
        self.depth = depth

        _start_idx = 0
        for i in range(len(points)):
            w = Wall(
                points[i],
                points[(i + 1) % len(points)],
                depth=self.depth,
                bathy_interp=bathy_interp,
            )
            w.start_idx = _start_idx
            _start_idx += len(w.get_vertices())
            self.walls.append(w)

    @property
    def vertices(self):
        for w in self.walls:
            yield from w.get_vertices()

    @property
    def faces(self):
        for w in self.walls:
            yield from w.get_faces()

    @property
    def depth(self):
        return self.__depth

    @depth.setter
    def depth(self, value):
        self.__depth = value
        for w in self.walls:
            w.depth = value

    def __repr__(self) -> str:
        return f"{np.array([w.xy_start for w in self.walls])}"


# bar.canvas = view.scene

last_modify_time = None
