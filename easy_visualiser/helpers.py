import numpy as np
from vispy import scene
from vispy.scene import BaseCamera
from vispy.scene.cameras.perspective import Base3DRotationCamera


def visual_coordinate_to_pixel_coordinate(
    visual_node: scene.visuals.visuals.BaseVisual, coordinates: np.ndarray
):
    """
    Maps a coordinate from visual coordinate to pixel coordinate.
    """
    tr = visual_node.get_transform(map_from="visual", map_to="canvas")
    # convert points to pixel coordinates
    pixel_coords = tr.map(coordinates)
    # normalise it
    # similar to coor / self.visualiser.view.camera._actual_distance
    return pixel_coords / pixel_coords[-1]


# def compute_delta_vec_from_canvas_to_visual_coordinate(camera: BaseCamera, diff_vec):
#     """
#     Given a camera instance, and a vector that denote the movement of a mouse on
#     that camera (i.e. pixel coordinate system);
#
#     Returns the corresponding diff vector in visual coordinate system
#     """
#     norm = np.mean(camera._viewbox.size)
#
#     if (
#             camera._event_value is None
#             or len(camera._event_value) == 2
#     ):
#         ev_val = camera.center
#     else:
#         ev_val = camera._event_value
#     dist = diff_vec / norm * camera._scale_factor
#
#     dist[1] *= -1
#     # dist[2] *= -1
#     # Black magic part 1: turn 2D into 3D translations
#     dx, dy, dz = camera._dist_to_trans(dist)
#     # Black magic part 2: take up-vector and flipping into account
#     ff = camera._flip_factors
#     up, forward, right = camera._get_dim_vectors()
#     dx, dy, dz = right * dx + forward * dy + up * dz
#     dx, dy, dz = ff[0] * dx, ff[1] * dy, dz * ff[2]
#     c = ev_val
#     # shift by scale_factor half
#     sc_half = camera._scale_factor / 2
#     # sc_half = 0
#     # point = c[0] + dx - sc_half, c[1] + dy - sc_half, c[2] + dz + sc_half
#     return dx - sc_half, dy - sc_half, dz + sc_half


def compute_delta_vec_from_canvas_to_visual_coordinate(
    camera: Base3DRotationCamera, diff_vec
):
    """
    Given a camera instance, and a vector that denote the movement of a mouse on
    that camera (i.e. pixel coordinate system);

    Returns the corresponding diff vector in visual coordinate system
    """
    delta = np.array(camera._dist_to_trans(diff_vec))
    delta[2] *= -1
    return delta
