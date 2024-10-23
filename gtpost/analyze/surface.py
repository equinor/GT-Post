from typing import List

import numpy as np
from rasterio.features import rasterize
from scipy import ndimage
from scipy.signal import convolve2d
from shapely import offset_curve
from shapely.geometry import LineString, MultiLineString, Polygon
from shapely.ops import split
from skimage import measure, morphology
from skimage.morphology import skeletonize

import gtpost.utils as utils
from gtpost.analyze import window_ops
from gtpost.analyze.classifications import ArchEl, SubEnv


def slope(array: np.ndarray):
    slopex = np.gradient(array, axis=1)
    slopey = np.gradient(array, axis=2)
    slope = np.abs(slopex * slopey)
    return slope


def detect_depositional_environments(
    bottom_depth: np.ndarray,
    mouth_position: List[int],
    river_width: int,
    model_boundary: Polygon,
    foreset_depth: np.ndarray,
    df_average_width: float,
) -> np.ndarray:
    """
    Detect broad categories of depositional environments, namely: delta top, delta front
    and prodelta. These environments are later used to confine architectural elements.

    Parameters
    ----------
    bottom_depth : np.ndarray
        Array of bottom depth, used for getting depth contour at the foreset.
    mouth_position : List[int]
        Position of river mouth (delta apex)
    model_boundary : Polygon
        Bounding polygon of the model domain
    foreset_depth : np.ndarray
        Array with expected depth of the (steepest part of) the foreset
    df_average_width : float
        Average (expected) width of the deltafront.

    Returns
    -------
    np.ndarray
        Environments delta top, delta front and prodelta.
    """
    environments = np.zeros_like(bottom_depth, dtype=np.int32)
    foreset_contours = []
    for t in range(bottom_depth.shape[0] - 1):
        t += 1
        bottom_depth_now = window_ops.numba_window_average(bottom_depth[t, :, :], 7)
        foreset_contours = measure.find_contours(bottom_depth_now, foreset_depth[t])
        foreset_contour = foreset_contours[
            np.argmax([len(c) for c in foreset_contours])
        ]
        foreset_contour = LineString(foreset_contour)
        foreset_contour = utils.snap_linestring_to_polygon(
            foreset_contour,
            model_boundary,
            mouth_position,
            river_width,
            overshoot=True,
            snap_distance=8,
        )
        topset_contour = offset_curve(foreset_contour, df_average_width / 2)
        if type(topset_contour) is MultiLineString:
            topset_contour = [
                g for g in topset_contour.geoms if g.crosses(model_boundary)
            ][0]

        environments_t = delta_areas_from_boundaries(
            foreset_contour, topset_contour, model_boundary, environments[t - 1, :, :]
        )
        environments[t, :, :] = environments_t

        foreset_contours.append(foreset_contour)

    return environments, foreset_contours


def delta_areas_from_boundaries(
    foreset_contour: LineString,
    topset_contour: LineString,
    model_boundary: Polygon,
    environments: np.ndarray,
) -> np.ndarray:
    """
    Use delta front topset and foreset contours to classify depostioonal environments

    Parameters
    ----------
    foreset_contour : LineString
        Contour line of the delta foreset
    topset_contour : LineString
         Contour line of the delta topset
    model_boundary : Polygon
        Bounding polygon of the model domain
    environments : np.ndarray
        Environments array, to be filled with depositional enviroment encoding

    Returns
    -------
    np.ndarray
        Complete environments array
    """
    areas_deep_marine = split(model_boundary, foreset_contour)
    areas_deep_marine = list(areas_deep_marine.geoms)
    # Take the polygon above the delta lower edge. This is the deep marine polygon
    deep_marine_polygon = areas_deep_marine[
        np.argmax(np.array([c.centroid.x for c in areas_deep_marine]))
    ]

    delta_edge_polygon = utils.join_linestrings_to_polygon(
        foreset_contour, topset_contour, reverse=True
    )

    # Rasterize areas to subenvironments
    environments_new = rasterize(
        [
            (model_boundary, SubEnv.deltatop.value),
            (delta_edge_polygon, SubEnv.deltafront.value),
            (deep_marine_polygon, SubEnv.prodelta.value),
        ],
        out_shape=(environments.shape[1], environments.shape[0]),
        dtype=np.int32,
    ).transpose()
    return environments_new


def detect_channel_network(dataset, subenvironment, resolution, config):
    # Unpack config settings
    channel_detection_method = config["classification"]["channel_detection_method"]
    channel_detection_range = int(
        config["classification"]["channel_detection_windowsize"]
    )
    channel_detection_sensitivity = -1 + float(
        config["classification"]["channel_detection_sensitivity"]
    )

    channels = np.full_like(subenvironment, False).astype(bool)
    channel_skel = np.full_like(subenvironment, False).astype(bool)
    channel_width = np.zeros_like(channels).astype(np.float32)
    channel_depth = np.zeros_like(channels).astype(np.float32)

    for t in range(subenvironment.shape[0] - 1):
        t += 1
        subenvironment_now = subenvironment[t, :, :]
        min_depth_now = dataset.MEAN_H1[t, :, :].values
        max_flow_now = dataset.MAX_UV[t, :, :].values

        if channel_detection_method == "local":
            channels_now = channel_detection_local(
                min_depth_now,
                max_flow_now,
                subenvironment_now,
                channel_detection_range,
                channel_detection_sensitivity,
            )
            channels_now = morphology.remove_small_objects(channels_now, min_size=100)
            channels_now = morphology.binary_closing(channels_now, morphology.disk(2))
        elif channel_detection_method == "static":
            channels_now = channel_detection_static(
                min_depth_now,
                max_flow_now,
                subenvironment_now,
                channel_detection_sensitivity,
            )
            channels_now = morphology.remove_small_objects(channels_now, min_size=100)

        channels[t, :, :] = channels_now
        channel_skel[t, :, :] = skeletonize(channels_now)
        channel_width[t, :, :] = resolution * ndimage.distance_transform_edt(
            channels_now.astype(int)
        )
        channel_depth[t, :, :] = channels_now.astype(int) * (
            dataset["DPS"].values[t, :, :] + dataset["S1"].values[t, :, :]
        )

    return (channels, channel_skel, channel_width, channel_depth)


def channel_detection_local(depth, flow, subenvironment, range, sensitivity):
    # Get local (within channel detection range window) differences for flow and
    # water depth.
    depth[subenvironment != 1] = np.nan
    depth[depth > 500] = np.nan
    local_depth = window_ops.numba_window_difference_between_minimum(depth, range)
    flow[subenvironment != 1] = np.nan
    flow[flow < -500] = np.nan
    local_flow = window_ops.numba_window_difference_between_minimum(flow, range)

    # Detect active channels and parameters (skeleton, width, depth)
    channels_now = np.full_like(subenvironment, False).astype(bool)
    channels_now[(local_depth < sensitivity) & (local_flow < sensitivity)] = True

    return channels_now


def channel_detection_static(depth, max_flow, subenvironment, sensitivity):
    channel_depth_requirement = 2.5 * -sensitivity
    channel_max_flow_requirement = 3 * -sensitivity
    channel_min_max_flow_requirement = 1.2 * -sensitivity
    depth[subenvironment != 1] = np.nan
    depth[depth > 500] = np.nan
    max_flow[subenvironment != 1] = np.nan
    max_flow[max_flow < -500] = np.nan
    channels_now = np.full_like(subenvironment, False).astype(bool)

    channels_now[
        (
            (max_flow > channel_max_flow_requirement)
            | (depth > channel_depth_requirement)
        )
        & (max_flow > channel_min_max_flow_requirement)
    ] = True

    return channels_now


def detect_elements(
    subenvironment: np.ndarray,
    channels: np.ndarray,
    channel_skeleton: np.ndarray,
    bottom_depth: np.ndarray,
    deposit_height: np.ndarray,
    sand_fraction: np.ndarray,
    foreset_depth: np.ndarray,
    config: dict,
) -> np.ndarray:
    """Detect Architectural Elements

    Parameters
    ----------
    subenvironment : np.ndarray
        Previously determined subenvironments
    channels : np.ndarray
        Previously determined channels
    channel_skeleton : np.ndarray
        Channel skeleton
    bottom_depth : np.ndarray
        Bottom depth array (t, x, y)
    deposit_height : np.ndarray
        Deposit height array (t, x, y)
    sand_fraction : np.ndarray
        Sand fraction array (t, x, y)
    foreset_depth : np.ndarray
        Average foreset depth (t)
    config : ConfigParser object (dict-like behaviour)
        ConfigParser object with classification settings

    Returns
    -------
    np.ndarray
        Array with architectural elements (t, x, y)
    """
    # Unpack config settings
    delta_top_subaqeous_depth = float(
        config["classification"]["delta_top_subaqeous_depth"]
    )
    delta_front_min_sandfrac = float(
        config["classification"]["deltafront_detection_minimal_sandfraction"]
    )
    mouthbar_search_radius = int(
        config["classification"]["mouthbar_detection_search_radius"]
    )
    mouthbar_critical_bl_change_df = float(
        config["classification"]["mouthbar_detection_critical_bl_change_df"]
    )
    mouthbar_critical_bl_change_ch = float(
        config["classification"]["mouthbar_detection_critical_bl_change_ch"]
    )
    mouthbar_critical_bl_change_dt = float(
        config["classification"]["mouthbar_detection_critical_bl_change_ch"]
    )

    archels = np.zeros_like(subenvironment)
    mask = np.zeros_like(subenvironment[0, :, :], dtype=bool)
    mb_kernel = np.ones((mouthbar_search_radius, mouthbar_search_radius))
    for t in range(subenvironment.shape[0] - 1):
        t += 1
        subenvironment_now = subenvironment[t, :, :]
        bed_chg_now = deposit_height[t, :, :]
        ch_skel_now = channel_skeleton[t, :, :]

        # Prodelta = depositional environment prodelta
        archels[t, :, :][
            (subenvironment_now == SubEnv.prodelta.value)
        ] = ArchEl.prodelta.value

        # Delta front = depositional environment delta edge
        archels[t, :, :][
            subenvironment_now == SubEnv.deltafront.value
        ] = ArchEl.deltafront.value
        archels[t, :, :][
            (subenvironment_now == SubEnv.prodelta.value)
            & (sand_fraction[t, :, :] > delta_front_min_sandfrac)
        ] = ArchEl.deltafront.value

        # Delta top = depositional environment delta top
        archels[t, :, :][
            subenvironment_now == SubEnv.deltatop.value
        ] = ArchEl.dtaqua.value
        archels[t, :, :][
            (subenvironment_now == SubEnv.deltatop.value)
            & (bottom_depth[t, :, :] < delta_top_subaqeous_depth)
        ] = ArchEl.dtair.value

        # Channels / Abandoned channels = depositional environment channels
        archels[t, :, :][channels[t, :, :]] = ArchEl.channel.value

        # Mouth bars
        # First find end points of channels. Mouthbars may only be classified around
        # these points within the (user-set) mouthbar search radius.
        channel_endpoints = utils.skeleton_endpoints(ch_skel_now)
        channel_endpoints = [ch for ch in channel_endpoints if ch[0] > 10]
        delta_top = np.ma.masked_where(
            archels[t, :, :] == ArchEl.dtaqua.value, mask
        ).mask.astype(np.int32)
        delta_front = np.ma.masked_where(
            archels[t, :, :] == ArchEl.deltafront.value, mask
        ).mask.astype(np.int32)
        ch_endpoint_allowed_area = convolve2d(
            delta_top + delta_front, mb_kernel, mode="same", boundary="wrap"
        )
        channel_endpoints = [
            ce
            for ce, p in zip(
                channel_endpoints,
                [ch_endpoint_allowed_area[c[0], c[1]] for c in channel_endpoints],
            )
            if p > mouthbar_search_radius * 4
        ]
        mb_mask = np.zeros_like(subenvironment_now, dtype=bool)
        for channel_endpoint in channel_endpoints:
            channel_end_mask = utils.create_circular_mask(
                subenvironment_now.shape[0],
                subenvironment_now.shape[1],
                channel_endpoint,
                mouthbar_search_radius / 2,
            )
            channel_end_mask = np.ma.masked_where(
                (archels[t, :, :] != ArchEl.dtair.value)
                & (archels[t, :, :] != ArchEl.prodelta.value)
                & channel_end_mask
                & (bottom_depth[t, :, :] < foreset_depth[t] / 1.5),
                mask,
            ).mask.astype(bool)
            mb_mask += channel_end_mask

        # Generate final mouthbar mask
        mouthbars = np.ma.masked_where(
            (
                mb_mask
                & (archels[t, :, :] == ArchEl.deltafront.value)
                & (bed_chg_now > mouthbar_critical_bl_change_df)
            )
            | (
                mb_mask
                & (archels[t, :, :] == ArchEl.dtaqua.value)
                & (bed_chg_now > mouthbar_critical_bl_change_dt)
            )
            | (
                mb_mask
                & (archels[t, :, :] == ArchEl.channel.value)
                & (bed_chg_now > mouthbar_critical_bl_change_ch)
            ),
            mask,
        )

        # MB elements cleanup and smoothening
        if isinstance(mouthbars.mask, np.ndarray):
            mouthbars = morphology.binary_closing(mouthbars.mask, morphology.disk(4))
            mouthbars = morphology.remove_small_objects(mouthbars, min_size=10)
        else:
            mouthbars = mouthbars.data

        # Assign MB element
        archels[t, :, :][mouthbars] = ArchEl.mouthbar.value

    return archels
