import numpy as np
import pyvista as pv
from pyvista import CellType
import xarray as xr
from itertools import product


def to_pv_model(xc, yc, array, bottom, file, binary=True):
    x, y = np.meshgrid(np.float32(yc), np.float32(xc))
    pv_model = pv.StructuredGrid(x, y, array)
    pv_top = pv_model.points.copy()
    pv_bottom = pv_model.points.copy()
    pv_bottom[:, -1] = bottom
    pv_model.points = np.vstack((pv_top, pv_bottom))
    pv_model.dimensions = [*pv_model.dimensions[0:2], 2]
    data_flat = projected_array.flatten(order="F")
    pv_model.point_data["values"] = np.hstack((data_flat, data_flat))

    # To pv.UnstructuredGrid by removing NaN cells from the StructuredGrid
    pv_model = pv_model.threshold()
    pv_model.save(file, binary=binary)


if __name__ == "__main__":
    ds = xr.open_dataset(
        r"n:\Projects\11209000\11209074\B. Measurements and calculations\test_results\MS_12_10\MS2_12_10plusNewSedClasses_rerun_mod - coarse-sand_sed_and_obj_data.nc"
    )
    g = 1
    x = 121
    y = 100

    grids = []
    for x, y in product(range(60, 200), range(100, 160)):
        current_surface = ds.zcor[-1, x, y].values
        preserved = ds.preserved_thickness[:-1, x, y].values
        if all(preserved == 0):
            continue
        archel = ds.archel[1:, x, y].values

        voxels = []
        accumulated_thickness = 0
        number_of_cells = 0
        archel_values = []
        for i, thickness in enumerate(preserved[::-1]):
            if thickness > 0:
                z_low = current_surface - accumulated_thickness - thickness
                z_high = current_surface - accumulated_thickness
                voxel = np.array(
                    [
                        [x * g, y * g, z_low],
                        [x * g + g, y * g, z_low],
                        [x * g, y * g + g, z_low],
                        [x * g + g, y * g + g, z_low],
                        [x * g, y * g, z_high],
                        [x * g + g, y * g, z_high],
                        [x * g, y * g + g, z_high],
                        [x * g + g, y * g + g, z_high],
                    ]
                )
                voxels.append(voxel)
                number_of_cells += 1
                accumulated_thickness += thickness
                archel_values.append(archel[-i - 1])

        points = np.vstack(voxels)
        cells_voxel = np.arange(number_of_cells * 8).reshape([number_of_cells, 8])
        grid = pv.UnstructuredGrid({CellType.VOXEL: cells_voxel}, points)
        grid.cell_data["Archel"] = archel_values
        grids.append(grid)

    block = pv.MultiBlock(grids)
    grid_comb = block.combine()
    grid_comb.save(file, binary=True)

    [ds[da].nbytes / 1e9 for da in ds.data_vars]
    xc = ds.dimen_x.values
    yc = ds.dimen_y.values
    bottom = -10

    i = len(ds.dimen_t)
    file = (
        r"n:\Projects\11209000\11209074\B. Measurements and calculations\test_results\MS_12_10"
        + f"\\test_{i}.vtk"
    )
    array = ds["zcor"][-1, :, :].values
    projected_array = ds["archel"][-1, :, :].values
    print("writing timestep last")
    to_pv_model(xc, yc, array, bottom, file, binary=True)
