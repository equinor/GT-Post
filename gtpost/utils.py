import numpy as np
from shapely import LineString, Polygon, frechet_distance, length, total_bounds
from skimage import measure


def get_dx_dy(dataset):
    """
    Get horizontal and vertical grid spacing
    """
    xvals = dataset.XZ[:, 0].values
    diff = np.diff(xvals[xvals > 0])[0]
    return diff, diff


def get_model_bound(dataset):
    """
    Get position of initial coastline
    """
    contours = measure.find_contours(dataset.MEAN_H1[1, :, :].values, -999)
    boundary = Polygon(contours[0])
    return boundary


def get_mouth_midpoint(dataset):
    """
    Get x and y position of the river mouth.
    """
    x_mouth = int(len(dataset.N) / 2 - 1)
    y_values = np.array(
        [
            np.count_nonzero(dataset.MEAN_H1[1, i, :] == -999.0)
            for i in range(len(dataset.M))
        ]
    )
    y_values[y_values == len(dataset.N)] = 0
    y_mouth = len(dataset.M) - np.argmax(y_values[::-1])
    return [x_mouth, y_mouth]


def get_river_width_at_mouth(dataset, mouth_midpoint):
    line = dataset.MEAN_H1[1, mouth_midpoint[1] - 1, :].values
    width = len(line[line > 0])
    return width


def join_linestrings_to_polygon(linestring_a, linestring_b, reverse=False):
    if reverse:
        linestring_a = linestring_a.reverse()
    xs = np.hstack([linestring_a.xy[0], linestring_b.xy[0]])
    ys = np.hstack([linestring_a.xy[1], linestring_b.xy[1]])
    polygon = Polygon([(x, y) for x, y in zip(xs, ys)])
    return polygon


def extend_linestring(linestring, length_fraction=0.05):
    coor_start_x = linestring.xy[0][0] + (
        (linestring.xy[0][0] - linestring.xy[0][1]) * length_fraction
    )
    coor_start_y = linestring.xy[1][0] + (
        (linestring.xy[1][0] - linestring.xy[1][1]) * length_fraction
    )

    coor_end_x = linestring.xy[0][-1] + (
        (linestring.xy[0][-1] - linestring.xy[0][-2]) * length_fraction
    )
    coor_end_y = linestring.xy[1][-1] + (
        (linestring.xy[1][-1] - linestring.xy[1][-2]) * length_fraction
    )

    coors = [(x, y) for x, y in zip(linestring.xy[0], linestring.xy[1])]
    coors.insert(0, tuple([coor_start_x, coor_start_y]))
    coors.append(tuple([coor_end_x, coor_end_y]))
    ls = LineString(coors)
    return ls
