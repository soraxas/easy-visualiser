import matplotlib.cbook as cbook
import matplotlib.pyplot as plt
import numpy as np

import easy_visualiser.plugins
from easy_visualiser.visualiser import Visualiser


def run():
    visualiser = Visualiser(
        title="Example on image callback",
        auto_add_default_plugins=False,
    )

    def random_noise_callback(plugin, new_pos):
        plugin.image_visual.set_data(
            np.random.rand(*plugin.image_array.shape).astype(np.float32)
        )
        plugin.image_visual.update()

    with cbook.get_sample_data("logo2.png") as image_file:
        image = plt.imread(image_file)
        visualiser.register_plugin(
            easy_visualiser.plugins.VisualisableImage(
                image,
                widget_configs=dict(col=0, row=0, col_span=5, row_span=2),
                on_mouse_callback=random_noise_callback,
            ),
            name="source",
        )

    with cbook.get_sample_data("Minduka_Present_Blue_Pack.png") as image_file:
        image = plt.imread(image_file)
        visualiser.register_plugin(
            easy_visualiser.plugins.VisualisableImage(
                image,
                widget_configs=dict(col=0, row=2, col_span=5, row_span=2),
                on_mouse_callback=random_noise_callback,
            ),
            name="target",
        )

    visualiser.run()


if __name__ == "__main__":
    run()
