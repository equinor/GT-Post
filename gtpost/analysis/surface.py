from typing import List

import matplotlib.pyplot as plt
import numpy as np
from rasterio.features import rasterize
from scipy import ndimage
from scipy.signal import convolve2d
from shapely import minimum_bounding_radius, offset_curve
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import linemerge, nearest_points, split
from skimage import measure, morphology
from skimage.morphology import local_minima, skeletonize

import gtpost.utils as utils
from gtpost.analysis import window_ops

# constants
delta_front_width = 12
delta_front_min_sandfrac = 0.01
channel_detection_sensitivity = -0.3
mouthbar_critical_bl_change = -0.4
mouthbar_minimal_bl_change = -0.1
prodelta_minimal_depth = 5


def detect_depositional_environments(
    array: np.ndarray,
    mouth_position: List[int],
    model_boundary: Polygon,
) -> np.ndarray:
    init_coast = np.array(
        [
            [mouth_position[1] - 2, array.shape[2]],
            [mouth_position[1] - 2, mouth_position[0]],
            [mouth_position[1] - 2, 0],
        ]
    )
    lower_edge = init_coast
    upper_edge = init_coast
    environments = np.zeros_like(array, dtype=np.int32)
    for t in range(array.shape[0] - 1):
        t += 1
        # Moving window averaging for smoother lower edgde of delta
        array_avg = window_ops.numba_window_average(array[t, :, :])
        contours = measure.find_contours(
            array_avg, np.median(array_avg[array_avg > 0] / 10)
        )
        # contours = [c for c in contours if np.nanmin(c[:, 0]) < mouth_position[1]]
        contour_polygons = [LineString(c) for c in contours]
        if len(contour_polygons) > 0:
            # Take the contour with the biggest radius
            contour_radii = [minimum_bounding_radius(c) for c in contour_polygons]
            lower_edge = contour_polygons[contour_radii.index(max(contour_radii))]
            lower_edge = offset_curve(lower_edge, 4)
            if lower_edge.coords[0][0] < mouth_position[1]:
                lower_edge = list(split(lower_edge, model_boundary).geoms)[0]
            else:
                # Split function does not work properly if the end/start point of the
                # contour is located offshore.
                lower_edge_half1 = list(split(lower_edge, model_boundary).geoms)[0]
                lower_edge_half2 = list(
                    split(lower_edge.reverse(), model_boundary).geoms
                )[0]
                xs = lower_edge_half1.xy[1][::-1] + lower_edge_half2.xy[1]
                ys = lower_edge_half1.xy[0][::-1] + lower_edge_half2.xy[0]
                lower_edge = utils.extend_linestring(
                    LineString([[y, x] for y, x in zip(ys, xs)])
                )
        else:
            lower_edge = LineString(lower_edge)
            lower_edge = LineString(upper_edge)

        upper_edge = offset_curve(lower_edge, delta_front_width)
        upper_edge = snap_linestring_to_polygon(
            upper_edge, model_boundary, mouth_position
        )

        environments_t = delta_areas_from_boundaries(
            lower_edge, upper_edge, model_boundary, environments[t - 1, :, :]
        )
        environments[t, :, :] = environments_t

    return environments


def delta_areas_from_boundaries(
    lower_edge: LineString,
    upper_edge: LineString,
    model_boundary: Polygon,
    environments: np.ndarray,
) -> np.ndarray:
    areas_deep_marine = split(model_boundary, lower_edge)
    areas_deep_marine = list(areas_deep_marine.geoms)
    # Take the polygon above the delta lower edge. This is the deep marine polygon
    deep_marine_polygon = areas_deep_marine[
        np.argmax(np.array([c.centroid.x for c in areas_deep_marine]))
    ]

    delta_edge_polygon = utils.join_linestrings_to_polygon(
        lower_edge, upper_edge, reverse=True
    )

    # Rasterize areas: 1 = Delta top; 2 = Abandoned channels (added later); 3 = Active
    # channels (added later); 3= Delta front; and 4 = Prodelta.
    environments_new = rasterize(
        [
            (model_boundary, 1),
            (delta_edge_polygon, 4),
            (deep_marine_polygon, 5),
        ],
        out_shape=(environments.shape[1], environments.shape[0]),
        dtype=np.int32,
    ).transpose()
    # Assuming a prograding/aggrading delta: do not allow delta front to be overwritten
    # by Prodelta to prevent retreat of the delta front.
    # environments_new[(environments == 4) & (environments_new == 5)] = 4
    return environments_new


def detect_channel_network(dataset, dep_env, bed_level_change, resolution):
    channels = np.full_like(dep_env, False).astype(bool)
    channel_skel = np.full_like(dep_env, False).astype(bool)
    channel_width = np.zeros_like(channels).astype(np.float32)
    channel_depth = np.zeros_like(channels).astype(np.float32)

    for t in range(dep_env.shape[0] - 1):
        t += 1
        dep_env_now = dep_env[t, :, :]
        bed_level_change_now = bed_level_change[t, :, :]
        min_depth_now = dataset.MEAN_H1[t, :, :].values
        max_flow_now = dataset.MAX_UV[t, :, :].values

        min_depth_now[dep_env_now != 1] = np.nan
        min_depth_now[min_depth_now > 500] = np.nan
        local_depth = window_ops.numba_window_difference_between_minimum(
            min_depth_now, 15
        )
        max_flow_now[dep_env_now != 1] = np.nan
        max_flow_now[max_flow_now < -500] = np.nan
        local_flow = window_ops.numba_window_difference_between_minimum(
            max_flow_now, 15
        )

        # Detect active channels and parameters (skeleton, width, depth)
        channels_now = np.full_like(dep_env_now, False).astype(bool)
        abandoned_channels_now = np.full_like(dep_env_now, False).astype(bool)
        channels_now[
            (local_depth < channel_detection_sensitivity)
            & (local_flow < channel_detection_sensitivity)
            & (bed_level_change_now > -0.6)
        ] = True
        channels_now[dep_env_now != 1] = False
        channels_now = morphology.remove_small_objects(channels_now, min_size=150)
        channels_now = morphology.binary_closing(channels_now, morphology.disk(2))
        channels[t, :, :] = channels_now
        channel_skel[t, :, :] = skeletonize(channels_now)
        channel_width[t, :, :] = resolution * ndimage.distance_transform_edt(
            channels_now.astype(int)
        )
        channel_depth[t, :, :] = channels_now.astype(int) * (
            dataset["DPS"].values[t, :, :] + dataset["S1"].values[t, :, :]
        )
        # Detect abandoned channels if it was a channel recently and is still a local
        # depression (i.e. underfilled)
        if t > 10:
            was_channel_recently = channels[t - 10 : t, :, :].max(axis=0) * np.invert(
                channels_now
            )
            underfilled = local_depth < -0.5
            abandoned_channels_now = (
                was_channel_recently * underfilled * (dep_env_now == 1)
            )
            abandoned_channels_now = morphology.remove_small_objects(
                abandoned_channels_now, min_size=50
            )
            abandoned_channels_now = morphology.binary_closing(
                abandoned_channels_now, morphology.disk(2)
            )

        # Finally assign channel environments
        dep_env[t, :, :][abandoned_channels_now] = 2
        dep_env[t, :, :][channels_now] = 3

    return (dep_env, channels, channel_skel, channel_width, channel_depth)


def detect_elements(dep_env, channel_skeleton, bed_level_change):
    """
    Detect architectural elements

    Prodelta = 6
    Delta front = 5
    Mouthbars = 4
    Abandoned channels = 3
    Active channels = 2
    Delta top = 1

    Parameters
    ----------
    dataset : _type_
        _description_
    dep_env : _type_
        _description_
    slope : _type_
        _description_
    """
    archels = np.zeros_like(dep_env)
    mask = np.zeros_like(dep_env[0, :, :], dtype=np.bool_)
    mb_kernel = np.ones((12, 12))
    mb_recent = np.zeros_like(dep_env)
    for t in range(dep_env.shape[0] - 1):
        t += 1
        dep_now = dep_env[t, :, :]
        bed_chg_now = bed_level_change[t, :, :]
        ch_skel_now = channel_skeleton[t, :, :]

        # Prodelta = depositional environment prodelta
        archels[t, :, :][dep_now == 5] = 6

        # Delta front = depositional environment delta edge
        archels[t, :, :][dep_now == 4] = 5

        # Delta top = depositional environment delta top
        archels[t, :, :][dep_now == 1] = 1

        # CHannels / Abandoned channels = depositional environment channels
        archels[t, :, :][dep_now == 3] = 3
        archels[t, :, :][dep_now == 2] = 2

        # Mouth bars
        # channels = np.ma.masked_where(dep_now == 3, mask).mask.astype(np.int32)
        delta_front = np.ma.masked_where(dep_now == 4, mask).mask.astype(np.int32)
        mb_proximity_ch = convolve2d(
            ch_skel_now, mb_kernel, mode="same", boundary="wrap"
        )
        mb_proximity_df = convolve2d(
            delta_front, mb_kernel, mode="same", boundary="wrap"
        )
        mb_allowed_area = mask.copy()
        mb_allowed_area[(mb_proximity_ch * mb_proximity_df) > 0] = True
        mb_allowed_area = morphology.binary_closing(mb_allowed_area, morphology.disk(4))

        mouthbars = np.ma.masked_where(
            (mb_allowed_area & (bed_chg_now < mouthbar_minimal_bl_change)),
            mask,
        )
        if isinstance(mouthbars.mask, np.ndarray):
            mouthbars = morphology.binary_closing(mouthbars.mask, morphology.disk(6))
            mouthbars = morphology.remove_small_objects(mouthbars, min_size=100)
        else:
            mouthbars = mouthbars.data

        mb_recent[t, :, :][mouthbars] = 4
        if t > 5:
            recently_active_mb = np.mean(mb_recent[t - 5 : t, :, :], axis=0)
            archels[t, :, :][(recently_active_mb > 2) & mb_allowed_area] = 4
            archels[t, :, :][mouthbars] = 4
        else:
            archels[t, :, :][mouthbars] = 4

    return archels


## Util funcs


def snap_linestring_to_polygon(
    linestring,
    model_boundary,
    mouth_position,
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

    for x, y in zip(
        linestring.xy[0][:split_point][::-1], linestring.xy[1][:split_point][::-1]
    ):
        point = Point(x, y)
        if point.distance(model_boundary.exterior) > snap_distance:
            coordinates.append(point.coords[0])
        else:
            break

    coordinates = coordinates[::-1]

    for x, y in zip(linestring.xy[0][split_point:], linestring.xy[1][split_point:]):
        point = Point(x, y)
        if point.distance(model_boundary.exterior) > snap_distance:
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
        ls = utils.extend_linestring(ls)
    return ls


if __name__ == "__main__":
    contours = 0
    array = 0
    ls = 0
    t = 0
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    # plt.imshow(test)
    # plt.imshow(slope[60, :, :], vmin=0.001, vmax=0.01)
    plt.imshow(array_avg, alpha=1, cmap="Greys", vmin=0, vmax=0.0000001)
    plt.imshow(channels_now, alpha=1, cmap="Greys")
    plt.imshow(ch_skel_now, alpha=1, cmap="Greys")
    plt.imshow(dep_now, alpha=1, cmap="Greys", vmin=0, vmax=5)

    cts = [LineString(c) for c in contours]
    fig, ax = plt.subplots()
    # ax.plot(linestring.xy[1], linestring.xy[0])
    # ax.imshow(array[t, :, :])
    # ax.imshow(array_avg, vmin=0, vmax=1e-7)
    ax.imshow(environments_t)
    ax.plot(lower_edge.xy[1], lower_edge.xy[0])
    ax.plot(upper_edge.xy[1], upper_edge.xy[0])
    for ct in cts:
        ax.plot(ct.xy[1], ct.xy[0])

    t = 60
    fig, ax = plt.subplots()
    # ax.imshow(environments)
    array[t, :, :].plot.imshow(ax=ax, cmap=plt.cm.YlGnBu, alpha=0.7)
    # ax.plot(model_boundary.exterior.xy[1], model_boundary.exterior.xy[0])
    ax.plot(upper_edge.xy[1], upper_edge.xy[0])
    ax.plot(lower_edge.xy[1], lower_edge.xy[0])
    ax.plot(delta_edge_polygon.exterior.xy[1], delta_edge_polygon.exterior.xy[0])
    ax.plot(areas.exterior.xy[1], areas.exupper_edgeterior.xy[0])
    ax.plot(delta_top_polygon.exterior.xy[1], delta_top_polygon.exterior.xy[0])
    ax.plot(deep_marine_polygon.exterior.xy[1], deep_marine_polygon.exterior.xy[0])
