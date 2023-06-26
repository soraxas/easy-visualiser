from vispy.scene import GridLines

from easy_visualiser.plugins import VisualisablePlugin


class VisualisableGridLines(VisualisablePlugin):
    def __init__(self, scale=(1, 1), color="white"):
        super().__init__()
        self.scale = scale
        self.color = color

    @property
    def name(self):
        return "grid_lines"

    def construct_plugin(self) -> None:
        super().construct_plugin()

        self.linegrid_visual = GridLines(
            scale=self.scale, color=self.color, parent=self.visualiser.visual_parent
        )
