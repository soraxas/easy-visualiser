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

kelly_colors = qualitative + [
    "#F3C300",
    "#875692",
    "#F38400",
    "#A1CAF1",
    "#BE0032",
    "#C2B280",
    "#848482",
    "#008856",
    "#E68FAC",
    "#0067A5",
    "#F99379",
    "#604E97",
    "#F6A600",
    "#B3446C",
    "#DCD300",
    "#882D17",
    "#8DB600",
    "#654522",
    "#E25822",
    "#2B3D26",
    "#F2F3F4",
    "#222222",
]

distinct_colors = [
    "#e6194b",
    "#3cb44b",
    "#ffe119",
    "#4363d8",
    "#f58231",
    "#911eb4",
    "#46f0f0",
    "#f032e6",
    "#bcf60c",
    "#fabebe",
    "#008080",
    "#e6beff",
    "#9a6324",
    "#fffac8",
    "#800000",
    "#aaffc3",
    "#808000",
    "#ffd8b1",
    "#000075",
    "#808080",
    "#ffffff",
    "#000000",
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
