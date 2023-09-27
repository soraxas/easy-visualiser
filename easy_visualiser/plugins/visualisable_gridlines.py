from vispy.scene import GridLines
from vispy.visuals.transforms import MatrixTransform

from easy_visualiser.plugins import VisualisablePlugin


class VisualisableGridLines(VisualisablePlugin):
    gridlines_visual: GridLines

    def __init__(self, scale=(1, 1), color="white", plane: str = "xy"):
        super().__init__()
        self.scale = scale
        self.color = color

        plane_choices = ("xy", "yz", "xz")
        if plane not in plane_choices:
            raise ValueError(
                f"grid lines plane must be one of {', '.join(plane_choices)}"
            )
        self.plane = plane

    def construct_plugin(self) -> None:
        super().construct_plugin()

        self.gridlines_visual = GridLines(
            scale=self.scale, color=self.color, parent=self.visualiser.visual_parent
        )

        if self.plane != "xy":
            my_transform = MatrixTransform()
            if self.plane == "xz":
                my_transform.rotate(90, [1, 0, 0])
            elif self.plane == "yz":
                my_transform.rotate(90, [0, 1, 0])
            self.gridlines_visual.transform = my_transform
