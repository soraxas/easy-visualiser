from collections import namedtuple

import dataclasses
import numpy as np

from vispy.scene.visuals import create_visual_node, Text
from vispy.visuals import LineVisual


@dataclasses.dataclass
class TickLocation:
    tick_location: np.ndarray
    is_major: bool
    length_from_origin: float


def tick_location_generator(
    pt1: np.ndarray,
    pt2: np.ndarray,
    tick_gap_length: float,
    major_tick_every: int,
    include_end: bool = False,
    scale_factor: float = 1,
):
    """
    Given 2 points, return a generator of all tick location
    """

    vec_diff = pt2 - pt1
    vec_norm = np.linalg.norm(vec_diff)
    vec_unit = vec_diff / vec_norm
    ################################
    # scale_factor = 1

    all_ticks_factors = np.arange(0, vec_norm * scale_factor, tick_gap_length)

    for i, _factor in enumerate(all_ticks_factors):
        is_major = False
        if i % major_tick_every == 0:
            is_major = True

        # each tick
        tick_origin = pt1 + _factor * vec_unit / scale_factor
        yield TickLocation(tick_origin, is_major, _factor)

    if include_end and vec_norm / tick_gap_length != 0:
        yield TickLocation(pt2, True, vec_norm * scale_factor)


def get_perpendicular_vec(pt1, pt2):
    vec_diff = pt2 - pt1
    vec_norm = np.linalg.norm(vec_diff)
    if np.isclose(vec_norm, 0.0):
        return np.array([0, 0, 1.0])
    vec_unit = vec_diff / vec_norm

    tick_vec = np.zeros_like(pt1)
    # default to creat perpendicular vec in z direction
    if abs(vec_unit[-1]) != 1:
        tick_vec[-1] = 1
    else:
        # the target vect is already perfectly align with z axis.
        #  we will use a different principle axis instead.
        tick_vec[-2] = 1

    tick_vec -= tick_vec.dot(vec_unit) * vec_unit  # make it orthogonal to k
    return tick_vec / np.linalg.norm(tick_vec)  # normalize it


class RulerScaleVisual(LineVisual):
    def __init__(
        self,
        start_end_pos=None,
        tick_gap=1,
        tick_length=None,
        major_tick_every=5,
        font_size=10000000,
        tick_label_formatter=lambda num: f"{num:.2f}",
        scale_factor=1,
        **kwargs,
    ):
        if kwargs.pop("pos", None) is not None:
            raise ValueError(
                f"{self.__class__.__name__} does not supports " f"pos argument."
            )
        self.__tick_gap = tick_gap
        self.__major_tick_every = major_tick_every
        self.__tick_length = tick_length
        self.__cur_vec_norm = 1
        self.__last_start_end_pos = None
        self.__ticks_label = Text(font_size=font_size, color="white")
        # to scale the ruler
        self.scale_factor = scale_factor
        self.tick_label_formatter = tick_label_formatter
        super().__init__(
            **kwargs,
            connect="segments",
        )
        if start_end_pos is not None:
            self.set_data(start_end_pos=start_end_pos)

    @property
    def tick_gap(self) -> float:
        return self.__tick_gap

    @tick_gap.setter
    def tick_gap(self, tick_gap: float):
        self.__tick_gap = tick_gap
        self.set_data(start_end_pos=self.__last_start_end_pos)

    @property
    def tick_length(self):
        if self.__tick_length is not None:
            return self.__tick_length
        # default to 1/10th of norm
        return self.__cur_vec_norm / 10.0

    @property
    def start_end_pos(self):
        return self.__last_start_end_pos

    def set_data(self, start_end_pos=None, color=None, width=None, connect=None):
        """Set the data used to draw this visual.

        Parameters
        ----------
        pos : array
            A tuple of size 2, with shape 2 or 3 specifying the starting and ending
            vertex coordinates.
        color : Color, tuple, or array
            The color to use when drawing the line. If an array is given, it
            must be of shape (..., 4) and provide one rgba color per vertex.
        width:
            The width of the line in px. Line widths < 1 px will be rounded up
            to 1 px when using the 'gl' method.
        connect : str or array
            Determines which vertices are connected by lines.

                * "strip" causes the line to be drawn with each vertex
                  connected to the next.
                * "segments" causes each pair of vertices to draw an
                  independent line segment
                * int numpy arrays specify the exact set of segment pairs to
                  connect.
                * bool numpy arrays specify which _adjacent_ pairs to connect.

        """
        pos = None
        if start_end_pos is not None:
            self.__last_start_end_pos = start_end_pos
            if len(start_end_pos) != 2:
                raise ValueError(
                    f"The start_end_pos should have len 2, "
                    f"but was {len(start_end_pos)}"
                )
            dim = None
            for pos in start_end_pos:
                if len(pos) not in (2, 3):
                    raise ValueError(
                        f"Each starting and ending pos should have len 2 or 3, "
                        f"but was {len(start_end_pos)}"
                    )
                if dim is None:
                    dim = len(pos)
                if dim != len(pos):
                    raise ValueError(f"Each pos should have same dimension")

            self.__cur_vec_norm = np.linalg.norm(start_end_pos[1] - start_end_pos[0])

            # tick vector
            tick_vec_unit = get_perpendicular_vec(start_end_pos[0], start_end_pos[1])

            all_ticks_info = list(
                tick_location_generator(
                    pt1=start_end_pos[0],
                    pt2=start_end_pos[1],
                    tick_gap_length=self.__tick_gap,
                    major_tick_every=self.__major_tick_every,
                    include_end=True,
                    scale_factor=self.scale_factor,
                )
            )

            pos = np.empty((2 + len(all_ticks_info) * 2 + 1, dim), dtype=np.float)
            # actual bar of start, end
            pos[0, :] = start_end_pos[0]
            pos[1, :] = start_end_pos[1]
            ###################

            _label_pos, _label_text = [], []
            for i, tick_info in enumerate(all_ticks_info):
                _tick_length = self.tick_length
                if tick_info.is_major:
                    _tick_length *= 2

                # each tick
                _tick_end = tick_info.tick_location + tick_vec_unit * _tick_length
                pos[2 + i * 2 + 0, :] = tick_info.tick_location
                pos[2 + i * 2 + 1, :] = _tick_end

                if tick_info.is_major:
                    # add major tick label
                    _label_text.append(
                        self.tick_label_formatter(tick_info.length_from_origin)
                    )
                    _label_pos.append(_tick_end + tick_vec_unit * 1000)

            if len(_label_pos) > 0:
                self.__ticks_label.parent = self.parent
                self.__ticks_label.text = _label_text
                self.__ticks_label.pos = _label_pos

        super().set_data(pos=pos, color=color, width=width, connect=connect)


RulerScale = create_visual_node(RulerScaleVisual)
