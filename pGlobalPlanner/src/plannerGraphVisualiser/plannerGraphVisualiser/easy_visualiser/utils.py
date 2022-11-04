class AxisScaler:
    def __init__(self, scale_factor: float) -> None:
        self.min = 0
        self.scale_factor = scale_factor

    def set_min(self, value: float) -> None:
        self.min = value

    def __call__(self, value: float) -> float:
        return (value - self.min) * self.scale_factor + self.min


def boolean_to_onoff(boolean: bool):
    return "ON" if boolean else "OFF"
