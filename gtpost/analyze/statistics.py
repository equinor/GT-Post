import numpy as np


def get_stats_per_archel(
    archels: np.array,
    preserved_thickness: np.array,
    d50: np.array,
    fractions: np.array,
    sorting: np.array,
    coastline_y: int,
):
    volumes = np.zeros(7)
    archel_d50s = np.zeros(7)
    archel_fractions = np.zeros(7)
    archel_sorting = np.zeros(7)
    for i in range(1, 8):
        idxs = (preserved_thickness[:, coastline_y:, :] > 0) & (
            archels[:, coastline_y:, :] == i
        )
        preserved_thickness_sel = preserved_thickness[:, coastline_y:, :][idxs]
        volumes[i - 1] = np.sum(preserved_thickness_sel)
        archel_d50s[i - 1] = np.average(
            d50[:, coastline_y:, :][idxs], weights=preserved_thickness_sel
        )
        archel_fractions[i - 1] = np.average(
            fractions[:, coastline_y:, :][idxs], weights=preserved_thickness_sel
        )
        archel_sorting[i - 1] = np.average(
            sorting[:, coastline_y:, :][idxs], weights=preserved_thickness_sel
        )
    delta_volume, archel_volumes = volume_stats(volumes)
    return delta_volume, archel_volumes, archel_d50s, archel_fractions, archel_sorting


def volume_stats(volumes: np.array):
    total_deposited_volume = np.sum(volumes)
    volume_percentages = (volumes / total_deposited_volume) * 100
    return total_deposited_volume, volume_percentages
