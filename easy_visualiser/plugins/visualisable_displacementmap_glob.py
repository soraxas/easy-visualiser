import glob

import numpy as np
from PIL import Image
from vispy.color import get_colormap

from easy_visualiser.key_mapping import MappingOnlyDisplayText
from easy_visualiser.plugin_capability import IntervalUpdatableMixin
from easy_visualiser.plugins.visualisable_displacementmap import (
    VisualisableDisplacementMap,
)
from easy_visualiser.utils import map_array_to_0_1


class VisualisableDisplacementMapLoopWithGlob(
    IntervalUpdatableMixin, VisualisableDisplacementMap
):
    """A version that loop through all matched files"""

    def __init__(self, image_glob_path: str):
        self.globbed_images = sorted(glob.glob(image_glob_path))
        self.current_image_path = None
        if len(self.globbed_images) < 1:
            raise ValueError(
                f"No images found with the glob string '{image_glob_path}'"
            )

        def iterator():
            while True:
                yield from self.globbed_images

        self.iterator = iterator()
        # initialise with the first image
        super().__init__(image_path=self.__get_next_image())

        # line to display current image
        self.add_mapping(
            MappingOnlyDisplayText(
                lambda: f"Displaying: {self.current_image_path.split('/')[-1]}\n"
            ),
            front=True,
        )

    def __get_next_image(self):
        self.current_image_path = next(self.iterator)
        return self.current_image_path

    def on_update(self) -> None:
        super().on_update()
        image_path = self.__get_next_image()
        with Image.open(image_path) as im:
            self.z_data = np.array(im.convert("L")).ravel()
        cmap = get_colormap("jet")
        colours = cmap.map(map_array_to_0_1(self.z_data))
        self.points_visual.set_data(face_color="white")
        self._reload_pos_data(self._compute_new_point_data())
        self.points_visual.update_data(colors=colours)

        # update status
        self.other_plugins.VisualisableAutoStatusBar.update_status()
