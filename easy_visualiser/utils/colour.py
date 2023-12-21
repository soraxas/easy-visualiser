import numpy as np

qualitative = [
    "#636EFA",
    "#EF553B",
    "#00CC96",
    "#AB63FA",
    "#FFA15A",
    "#19D3F3",
    "#FF6692",
    "#B6E880",
    "#FF97FF",
    "#FECB52",
]


def hex2rgb(hex_val):
    return tuple(int(hex_val.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))


def gen_colour(colour_list, convert_hex2rgb: bool = False):
    while True:
        if convert_hex2rgb:
            yield from [hex2rgb(h) for h in colour_list]
        else:
            yield from colour_list


def add_alpha(colour: np.ndarray, alpha_value):
    assert isinstance(colour, np.ndarray)
    assert colour.shape[-1] == 3
    if len(colour.shape) == 1:
        return np.append(colour, alpha_value)
    if isinstance(alpha_value, np.ndarray):
        alpha_array = alpha_value
    else:
        alpha_array = np.empty((*colour.shape[:-1], 1), dtype=colour.dtype)
        alpha_array[:] = alpha_value
    return np.append(colour, alpha_array, axis=-1)
