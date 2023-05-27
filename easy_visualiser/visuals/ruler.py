import dataclasses
from typing import Callable, List, Optional

import numpy as np
from vispy.scene.visuals import Text, create_visual_node
from vispy.visuals import CompoundVisual, LineVisual


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
    if vec_norm == 0:
        return
    vec_unit = vec_diff / vec_norm
    ################################

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
        scale_factor=1,
        tick_label_callback: Optional[
            Callable[[float, np.ndarray, np.ndarray], None]
        ] = None,
        **kwargs,
    ):
        """
        tick_label_callback is a callable with:
            1st arg: value on the ruler (i.e. length)
            2nd arg: tick end position in the world coordinate (i.e. 2/3d coordinate)
            3rd arg: a unit vector that represent the direction of the tick
        """

        if kwargs.pop("pos", None) is not None:
            raise ValueError(
                f"{self.__class__.__name__} does not supports " f"pos argument."
            )
        self.__tick_gap = tick_gap
        self.__major_tick_every = major_tick_every
        self.__tick_length = tick_length
        self.__cur_vec_norm = 1
        self.__last_start_end_pos = None
        self.ticks_info: List[TickLocation] = []
        # to scale the ruler
        self.scale_factor = scale_factor
        self.tick_label_callback = tick_label_callback
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

    def set_data(
        self, start_end_pos: np.ndarray = None, color=None, width=None, connect=None
    ):
        """Set the data used to draw this visual.

        Parameters
        ----------
        start_end_pos : array
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

            self.ticks_info = list(
                tick_location_generator(
                    pt1=start_end_pos[0],
                    pt2=start_end_pos[1],
                    tick_gap_length=self.__tick_gap,
                    major_tick_every=self.__major_tick_every,
                    include_end=True,
                    scale_factor=self.scale_factor,
                )
            )

            pos = np.empty((2 + len(self.ticks_info) * 2 + 1, dim), dtype=np.float)
            # actual bar of start, end
            pos[0, :] = start_end_pos[0]
            pos[1, :] = start_end_pos[1]
            ###################

            for i, tick_info in enumerate(self.ticks_info):
                _tick_length = self.tick_length
                if tick_info.is_major:
                    _tick_length *= 2

                # each tick
                _tick_end = tick_info.tick_location + tick_vec_unit * _tick_length
                pos[2 + i * 2 + 0, :] = tick_info.tick_location
                pos[2 + i * 2 + 1, :] = _tick_end

                if tick_info.is_major and self.tick_label_callback is not None:
                    self.tick_label_callback(
                        tick_info.length_from_origin, _tick_end, tick_vec_unit
                    )

        super().set_data(pos=pos, color=color, width=width, connect=connect)


class RulerScaleWithLabelVisual(CompoundVisual):
    def __init__(
        self,
        tick_label_formatter: Callable[[float], str] = lambda num: f"{num:.2f}",
        font_size=100,
        font_color="white",
        **kwargs,
    ):
        # self.tick_label_formatter = tick_label_formatter
        self.label_text = []
        self.label_pos = []

        def label_collector(
            value: float, tick_end: np.ndarray, tick_unit_vec: np.ndarray
        ):
            self.label_text.append(tick_label_formatter(value))
            self.label_pos.append(tick_end + tick_unit_vec * font_size / 1000)

        self._ticks_label = Text(font_size=font_size, color=font_color)
        self._ticks_ruler = RulerScaleVisual(
            tick_label_callback=label_collector, **kwargs
        )

        CompoundVisual.__init__(self, [self._ticks_ruler, self._ticks_label])

    @property
    def start_end_pos(self):
        return self._ticks_ruler.start_end_pos

    def set_data(self, **kwargs):
        # clear previous labels
        self.label_text.clear()
        self.label_pos.clear()

        # the following will set our list via callback
        self._ticks_ruler.set_data(**kwargs)

        if len(self.label_pos) == 0:
            self._ticks_label.text = ""
        else:
            self._ticks_label.text = self.label_text
            self._ticks_label.pos = self.label_pos


RulerScale = create_visual_node(RulerScaleWithLabelVisual)

__all__ = ["RulerScale"]
