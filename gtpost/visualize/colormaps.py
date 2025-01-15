from typing import NamedTuple

import numpy as np
from matplotlib import cm
from matplotlib.colors import (
    BoundaryNorm,
    LinearSegmentedColormap,
    ListedColormap,
    Normalize,
)


def categorical_cmap(alphas, colors, name):
    cmap = ListedColormap(
        colors=colors,
        name=name,
    )
    cmap = cmap(np.arange(cmap.N))
    cmap[:, -1] = alphas

    cmap = ListedColormap(cmap)
    bounds = np.arange(cmap.N + 1)
    vals = bounds[:-1]
    norm = BoundaryNorm(bounds, cmap.N)
    mappable = cm.ScalarMappable(norm=norm, cmap=cmap)
    return cmap, mappable, bounds, vals, norm


def continuous_cmap(colorlist, name, vmin, vmax):
    norm = Normalize(vmin=vmin, vmax=vmax)
    cmap = LinearSegmentedColormap.from_list(name, colorlist)
    mappable = cm.ScalarMappable(norm=norm, cmap=cmap)
    return cmap, mappable, norm


class ArchelColormap(NamedTuple):
    alphas = [1, 1, 1, 1, 1, 1, 1]
    colors = [
        "snow",
        "yellowgreen",
        "mediumseagreen",
        "deepskyblue",
        "yellow",
        "turquoise",
        "mediumblue",
    ]
    labels = ["N/A", "DT-subar", "DT-subaq", "AC", "MB", "DF", "PD"]
    ticks = np.arange(0, 7)
    name = "Architectural elements"
    type = "categorical"
    cmap, mappable, bounds, values, norm = categorical_cmap(alphas, colors, name)


class WaveArchelColormap(NamedTuple):
    alphas = [1, 1, 1, 1, 1]
    colors = [
        "snow",
        "yellowgreen",
        "mediumseagreen",
        "deepskyblue",
        "yellow",
    ]
    labels = ["N/A", "Delta top", "Shoreface", "Channel", "Spit"]
    ticks = np.arange(0, 5)
    name = "Architectural elements"
    type = "categorical"
    cmap, mappable, bounds, values, norm = categorical_cmap(alphas, colors, name)


class ExperimentalArchelColormap(NamedTuple):
    alphas = [1, 1, 1, 1, 1, 1]
    colors = [
        "snow",
        "yellowgreen",
        "mediumseagreen",
        "deepskyblue",
        "yellow",
        "turquoise",
    ]
    labels = ["N/A", "DT-subar", "DT-subaq", "Channel", "Mouth bar", "Delta front"]
    ticks = np.arange(0, 6)
    name = "Architectural elements"
    type = "categorical"
    cmap, mappable, bounds, values, norm = categorical_cmap(alphas, colors, name)


class GrainsizeColormap(NamedTuple):
    c0 = (0.0, "#006400")  # dark green
    c1 = (0.044, "#6B8E23")  # olivedrab
    c2 = (0.088, "#FFFF00")  # yellow
    c3 = (0.177, "#FFD700")  # gold
    c4 = (0.354, "#FF8C00")  # dark orange
    c5 = (0.707, "#8B0000")  # dark red
    c6 = (1.0, "#BA55D3")  # mediumorchid
    name = "Grain size (D50)"
    type = "mappable"
    vmin = 0
    vmax = 1.6
    cmap, mappable, norm = continuous_cmap(
        [c0, c1, c2, c3, c4, c5, c6], name, vmin, vmax
    )


class SandfractionColormap(NamedTuple):
    c0 = (0.0, "#006400")  # dark green
    c1 = (0.044, "#6B8E23")  # olivedrab
    c2 = (0.088, "#FFFF00")  # yellow
    c3 = (0.177, "#FFD700")  # gold
    c4 = (0.354, "#FF8C00")  # dark orange
    c5 = (0.707, "#8B0000")  # dark red
    c6 = (1.0, "#BA55D3")  # mediumorchid
    name = "Sand fraction"
    type = "mappable"
    vmin = 0
    vmax = 1
    cmap, mappable, norm = continuous_cmap(
        [c0, c1, c2, c3, c4, c5, c6], name, vmin, vmax
    )


class BedlevelchangeColormap(NamedTuple):
    c0 = (0.0, "darkred")  # dark green
    c1 = (0.5, "lightyellow")  # olivedrab
    c2 = (1, "darkgreen")  # yellow
    name = "Bed level change"
    type = "mappable"
    vmin = -2
    vmax = 2
    cmap, mappable, norm = continuous_cmap([c0, c1, c2], name, vmin, vmax)


class BottomDepthColormap(NamedTuple):
    c0 = (0, "#182514")
    c1 = (0.143, "#0C672C")
    c2 = (0.286, "#829E06")
    c3 = (0.429, "#E5D37F")
    c4 = (0.5, "#FDFAE6")
    c5 = (0.571, "#C4DAD0")
    c6 = (0.714, "#45A2AE")
    c7 = (0.857, "#1B5A9E")
    c8 = (1, "#172313")
    name = "Bottom depth"
    type = "mappable"
    vmin = -6
    vmax = 8
    cmap, mappable, norm = continuous_cmap(
        [c0, c1, c2, c3, c4, c5, c6, c7, c8], name, vmin, vmax
    )


class BottomDepthHighContrastColormap(NamedTuple):
    c0 = (0, "#182514")
    c1 = (0.143, "#0C672C")
    c2 = (0.286, "#829E06")
    c3 = (0.429, "#E5D37F")
    c4 = (0.5, "#FDFAE6")
    c5 = (0.571, "#C4DAD0")
    c6 = (0.714, "#45A2AE")
    c7 = (0.857, "#1B5A9E")
    c8 = (1, "#172313")
    name = "Bottom depth"
    type = "mappable"
    vmin = -2
    vmax = 8
    cmap, mappable, norm = continuous_cmap(
        [c0, c1, c2, c3, c4, c5, c6, c7, c8], name, vmin, vmax
    )


class PorosityColormap(NamedTuple):
    c0 = (0.0, "darkred")  # dark green
    c1 = (0.5, "khaki")  # olivedrab
    c2 = (1, "seagreen")  # yellow
    name = "Unconsolidated porosity"
    type = "mappable"
    vmin = 0.25
    vmax = 0.35
    cmap, mappable, norm = continuous_cmap([c0, c1, c2], name, vmin, vmax)


class DepositionageColormap(NamedTuple):
    c0 = (0.0, "lightgray")
    c1 = (0.25, "gold")
    c2 = (0.5, "darkorange")
    c3 = (0.75, "crimson")
    c4 = (1, "magenta")
    name = "Age (timestep) of deposition"
    type = "mappable"
    vmin = 0
    vmax = 320
    cmap, mappable, norm = continuous_cmap([c0, c1, c2, c3, c4], name, vmin, vmax)
