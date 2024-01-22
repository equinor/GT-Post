import numpy as np

from gtpost.analyze import classifications


def get_stats_per_archel(
    archels: np.ndarray,
    preserved_thickness: np.ndarray,
    d50: np.ndarray,
    fractions: np.ndarray,
    sorting: np.ndarray,
    coastline_y: int,
) -> (float, np.ndarray, np.ndarray, np.ndarray, np.ndarray):
    """
    Derive statistics per architectural element

    Parameters
    ----------
    archels : np.ndarray
        Architectural elements
    preserved_thickness : np.ndarray
        Calculated preserved thickness
    d50 : np.ndarray
        Sediment d50
    fractions : np.ndarray
        Sand fraction array
    sorting : np.ndarray
        Sorting array

    Returns
    -------
    float, np.ndarray, np.ndarray, np.ndarray, np.ndarray
        Total delta volume (float)
        Volume per AE (np.ndarray)
        Weighted average d50 per AE (np.ndarray)
        Weighted average sand fraction per AE (np.ndarray)
        Weighted average sorting per AE (np.ndarray)
    """
    array_length = len(classifications.ArchEl) - 1
    volumes = np.zeros(array_length)
    archel_d50s = np.zeros(array_length)
    archel_fractions = np.zeros(array_length)
    archel_sorting = np.zeros(array_length)
    for i in range(1, len(classifications.ArchEl)):
        idxs = (preserved_thickness[:, coastline_y:, :] > 0) & (
            archels[:, coastline_y:, :] == i
        )
        preserved_thickness_sel = preserved_thickness[:, coastline_y:, :][idxs]
        if len(preserved_thickness_sel) != 0:
            volumes[i - 1] = np.sum(preserved_thickness_sel)
            archel_d50s[i - 1] = np.average(
                d50[:, coastline_y:, :][idxs], weights=preserved_thickness_sel
            )
            archel_fractions[i - 1] = np.average(
                fractions[:, coastline_y:, :][idxs], weights=preserved_thickness_sel
            )
            archel_sorting[i - 1] = np.nanmean(sorting[:, coastline_y:, :][idxs])
        else:
            archel_d50s[i - 1] = 0
            archel_fractions[i - 1] = 0
            archel_sorting[i - 1] = 0
    delta_volume, archel_volumes = volume_stats(volumes)
    return delta_volume, archel_volumes, archel_d50s, archel_fractions, archel_sorting


def get_diameter_distributions(
    archels: np.array,
    preserved_thickness: np.ndarray,
    d50: np.ndarray,
    coastline_y: int,
) -> (list, list):
    """
    Get distribution of grain size classes per architectural element

    Parameters
    ----------
    archels : np.ndarray
        Architectural elements
    list : _type_
        _description_

    Returns
    -------
    list, list
        Distribution of grain size classes
        Weights (for weighted histograms)
    """
    d50_distributions = []
    d50_distribution_weights = []
    for i in range(1, len(classifications.ArchEl)):
        idxs = (preserved_thickness[:, coastline_y:, :] > 0) & (
            archels[:, coastline_y:, :] == i
        )
        d50_distr = d50[:, coastline_y:, :][idxs]
        d50_distr_weights = preserved_thickness[:, coastline_y:, :][idxs]
        d50_distributions.append(d50_distr)
        d50_distribution_weights.append(d50_distr_weights)

    idxs_total = preserved_thickness[:, coastline_y:, :] > 0
    d50_total = d50[:, coastline_y:, :][idxs_total]
    d50_total_weights = preserved_thickness[:, coastline_y:, :][idxs_total]
    d50_distributions.insert(0, d50_total)
    d50_distribution_weights.insert(0, d50_total_weights)

    return d50_distributions, d50_distribution_weights


def volume_stats(volumes: np.array) -> (np.array, np.array):
    total_deposited_volume = np.sum(volumes)
    volume_percentages = (volumes / total_deposited_volume) * 100
    return total_deposited_volume, volume_percentages
