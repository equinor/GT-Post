from configparser import ConfigParser
from pathlib import Path

import numpy as np
from rasterio.features import rasterize
from shapely import buffer
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import nearest_points
from skimage import measure


def get_template_name(input_path: str | Path) -> str:
    """
    Get the name of a D3D-GT template from the input.ini file.

    Parameters
    ----------
    input_path : str | Path
        Input D3D-GT folder, where input.ini is located.

    Returns
    -------
    str
        Name of the D3D-GT template.
    """
    input_ini = ConfigParser()
    input_ini.read(Path(input_path).joinpath("input.ini"))
    template_name = input_ini["template"]["value"].lower().replace(" ", "_")
    return template_name


def get_dx_dy(xvalues: np.ndarray) -> (int, int):
    """
    Get grid spacing. Assumes spacing is the same along x and y dimensions.

    Parameters
    ----------
    xvalues : np.ndarray
        (y) array with x-coordinates

    Returns
    -------
    int, int
        Grid resolution along x and y axis
    """
    diff = np.diff(xvalues[xvalues > 0])[0]
    return diff, diff


def get_model_bound(mean_depth: np.ndarray) -> Polygon:
    """
    Get position of initial coastline.

    Parameters
    ----------
    mean_depth : np.ndarray
        (x, y) Array of mean depth at first D3D model timestep

    Returns
    -------
    Polygon
        shapely.geometry.Polygon object around the margins of the model.
    """
    contours = measure.find_contours(mean_depth, -999)
    boundary = Polygon(contours[0]).buffer(-1)
    return boundary


def get_mouth_midpoint(
    mean_water_depth: np.array, dimension_n: np.array, dimension_m: np.array
) -> list[int, int]:
    """
    Get x and y position of the river mouth.

    Parameters
    ----------
    mean_water_depth : np.array
        Array of mean water depth at the first timestep (MEAN_H1 data var in trim file).
    dimension_n : np.array
        Array of n-dimension cells (N data var in trim file).
    dimension_m : np.array
        Array of m-dimension cells (M data var in trim file).

    Returns
    -------
    list
        list with mouth midpoint x-position and mouth y-position.
    """
    x_mouth = int(np.ceil(np.mean(np.where(mean_water_depth[1, :] == -999.0))))
    y_values = np.array(
        [
            np.count_nonzero(mean_water_depth[i, :] == -999.0)
            for i in range(len(dimension_m))
        ]
    )
    y_values[:2] = 0
    y_values[-2:] = 0
    y_mouth = len(dimension_m) - np.argmax(y_values[::-1]) - 1
    return [x_mouth, y_mouth]


def get_river_width_at_mouth(mean_water_depth: np.array, mouth_midpoint: list) -> int:
    """
    Get the total width of the fluvial part of the model domain

    Parameters
    ----------
    mean_water_depth : np.array
        Array of mean water depth at the first timestep (MEAN_H1 data var in trim file).
    mouth_midpoint : list
        Delta mouth midpoint: result of utils.get_mouth_midpoint.

    Returns
    -------
    int
        River width in number of grid cells.
    """
    line = mean_water_depth[mouth_midpoint[1] - 1, :]
    left_side = np.argmax(line > 0)
    right_side = len(line) - np.argmax(line[::-1] > 0)
    width = right_side - left_side
    return width


def get_deltafront_contour_depth(bottom_depth, slope, model_boundary):
    """
    Test different contour depths to find the depth contour that has the highest slope
    on average. This is the contour that best follows the steepest part of the foreset
    and is used to bound the delta and for classification of architectural elements.

    Parameters
    ----------
    bottom_depth : _type_
        _description_
    slope : _type_
        _description_
    """
    contour_depths = [2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8]
    foreset_contours = []
    timesteps = bottom_depth.shape[0]
    model_inner_boundary = buffer(model_boundary, -16)
    model_inner_grid = rasterize(
        [(model_inner_boundary, 1)],
        out_shape=(slope[0, :, :].shape[1], slope[0, :, :].shape[0]),
    ).transpose()
    for i in np.arange(20, timesteps, 5):
        slope_mean = []
        bottom_depth_i = np.copy(bottom_depth[i, :, :])
        bottom_depth_i[model_inner_grid == 0] = np.nan
        slope_i = slope[i, :, :]
        slope_i[model_inner_grid == 0] = np.nan
        for contour_depth in contour_depths:
            contours = measure.find_contours(bottom_depth[i, :, :], contour_depth)
            selected_contour = contours[np.argmax([len(c) for c in contours])]
            selected_contour = np.round(selected_contour).astype(np.int64)
            sampled_slopes = slope_i[selected_contour[:, 0], selected_contour[:, 1]]
            slope_mean.append(np.nanmean(sampled_slopes))
        foreset_contours.append(contour_depths[np.nanargmax(slope_mean)])

    foreset_fit = np.polyfit(np.arange(20, timesteps, 5), foreset_contours, 2)
    t = np.arange(0, timesteps, 1)
    interpolated_foreset_depth = (
        foreset_fit[0] * t**2 + foreset_fit[1] * t + foreset_fit[2]
    )
    return interpolated_foreset_depth


def numpy_mode(array):
    vals, counts = np.unique(array, return_counts=True)
    index = np.argmax(counts)
    return vals[index]


def join_linestrings_to_polygon(linestring_a, linestring_b, reverse=False):
    if reverse:
        linestring_a = linestring_a.reverse()
    xs = np.hstack([linestring_a.xy[0], linestring_b.xy[0]])
    ys = np.hstack([linestring_a.xy[1], linestring_b.xy[1]])
    polygon = Polygon([(x, y) for x, y in zip(xs, ys)])
    return polygon


def snap_linestring_to_polygon(
    linestring,
    model_boundary,
    mouth_position,
    river_width,
    snap_distance=5,
    overshoot=True,
):
    """
    Snap a linestring on both sides of the delta to the model boundary if it comes
    within snap_distance cells. Cut off the rest of the linestring (after the first
    time the line came within snap_distance of the coast).

    Parameters
    ----------
    linestring : _type_
        Line of e.g. delta lower or upper edge
    snap_distance : int, optional
        Snapping sensitivity in number of cells, by default 12
    """
    coordinates = []
    split_point = np.argmin(np.abs(np.array(linestring.xy[1]) - mouth_position[0]))
    mouth_left = mouth_position[0] - river_width / 2
    mouth_right = mouth_position[0] + river_width / 2

    for x, y in zip(
        linestring.xy[0][:split_point][::-1], linestring.xy[1][:split_point][::-1]
    ):
        point = Point(x, y)
        if point.distance(model_boundary.exterior) > snap_distance:
            coordinates.append(point.coords[0])
        elif y > mouth_left and y < mouth_right:
            coordinates.append(point.coords[0])
        else:
            break

    coordinates = coordinates[::-1]

    for x, y in zip(linestring.xy[0][split_point:], linestring.xy[1][split_point:]):
        point = Point(x, y)
        if point.distance(model_boundary.exterior) > snap_distance:
            coordinates.append(point.coords[0])
        elif y > mouth_left and y < mouth_right:
            coordinates.append(point.coords[0])
        else:
            break

    coordinates.insert(
        0, nearest_points(Point(coordinates[0]), model_boundary.exterior)[1]
    )
    coordinates.append(
        nearest_points(Point(coordinates[-1]), model_boundary.exterior)[1]
    )
    ls = LineString(coordinates)
    if overshoot:
        ls = extend_linestring(ls)
    return ls


def extend_linestring(linestring, length=2):
    dx_start = (
        (linestring.xy[0][0] - linestring.xy[0][1])
        if (linestring.xy[0][0] != linestring.xy[0][1])
        else linestring.xy[0][0] - linestring.xy[0][2]
    )
    dx_end = (
        (linestring.xy[0][-1] - linestring.xy[0][-2])
        if (linestring.xy[0][-1] != linestring.xy[0][-2])
        else linestring.xy[0][-1] - linestring.xy[0][-3]
    )
    dy_start = (
        (linestring.xy[1][0] - linestring.xy[1][1])
        if (linestring.xy[1][0] != linestring.xy[1][1])
        else linestring.xy[1][0] - linestring.xy[1][2]
    )
    dy_end = (
        (linestring.xy[1][-1] - linestring.xy[1][-2])
        if (linestring.xy[1][-1] != linestring.xy[1][-2])
        else linestring.xy[1][-1] - linestring.xy[1][-3]
    )

    start_length_factor = length / np.sqrt(dx_start**2 + dy_start**2)
    end_length_factor = length / np.sqrt(dx_end**2 + dy_end**2)

    dx_start *= start_length_factor
    dy_start *= start_length_factor
    dx_end *= end_length_factor
    dy_end *= end_length_factor

    coor_start_x = linestring.xy[0][0] + dx_start
    coor_start_y = linestring.xy[1][0] + dy_start
    coor_end_x = linestring.xy[0][-1] + dx_end
    coor_end_y = linestring.xy[1][-1] + dy_end

    coors = [(x, y) for x, y in zip(linestring.xy[0], linestring.xy[1])]
    coors.insert(0, tuple([coor_start_x, coor_start_y]))
    coors.append(tuple([coor_end_x, coor_end_y]))
    ls = LineString(coors)
    return ls


def skeleton_endpoints(skeleton):
    # Find row and column locations that are non-zero
    (rows, cols) = np.nonzero(skeleton)

    # Initialize empty list of co-ordinates
    skel_coords = []

    # For each non-zero pixel...
    for r, c in zip(rows, cols):
        # Extract an 8-connected neighbourhood
        (col_neigh, row_neigh) = np.meshgrid(
            np.array([c - 1, c, c + 1]), np.array([r - 1, r, r + 1])
        )

        # Cast to int to index into image
        col_neigh = col_neigh.astype("int")
        row_neigh = row_neigh.astype("int")

        # Convert into a single 1D array and check for non-zero locations
        pix_neighbourhood = skeleton[row_neigh, col_neigh].ravel() != 0

        # If the number of non-zero locations equals 2, add this to
        # our list of co-ordinates
        if np.sum(pix_neighbourhood) == 2:
            skel_coords.append((r, c))
    return skel_coords


def create_circular_mask(h, w, center=None, radius=None):
    if center is None:  # use the middle of the image
        center = (int(w / 2), int(h / 2))
    if radius is None:  # use the smallest distance between the center and image walls
        radius = min(center[0], center[1], w - center[0], h - center[1])

    y, x = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((y - center[0]) ** 2 + (x - center[1]) ** 2)

    mask = dist_from_center <= radius
    return mask
