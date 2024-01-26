from itertools import product

import numpy as np
import pyvista as pv
import xarray as xr
from pyvista import CellType


def to_voxel_model(
    dataset,
    xbnds,
    ybnds,
    res=1,
    displayed_variables=[
        "archel",
        "diameter",
        "fraction",
        "sorting",
        "porosity",
        "permeability",
        "deposition_age",
    ],
):
    grids = []
    for x, y in product(range(xbnds[0], xbnds[1]), range(ybnds[0], ybnds[1])):
        preserved = dataset.preserved_thickness[:-1, y, x].values
        # If no material was ever preserved at this location, skip to next location.
        if all(preserved == 0):
            continue

        current_surface = dataset.zcor[-1, y, x].values
        variable_data = {}
        variable_cell_data = {}
        for displayed_variable in displayed_variables:
            variable_data[displayed_variable] = dataset[displayed_variable][
                1:, y, x
            ].values
            variable_cell_data[displayed_variable] = []

        voxels = []
        accumulated_thickness = 0
        number_of_cells = 0
        for i, thickness in enumerate(preserved[::-1]):
            if thickness > 0:
                z_low = current_surface - accumulated_thickness - thickness
                z_high = current_surface - accumulated_thickness
                voxel = np.array(
                    [
                        [x * res, y * res, z_low],
                        [x * res + res, y * res, z_low],
                        [x * res, y * res + res, z_low],
                        [x * res + res, y * res + res, z_low],
                        [x * res, y * res, z_high],
                        [x * res + res, y * res, z_high],
                        [x * res, y * res + res, z_high],
                        [x * res + res, y * res + res, z_high],
                    ]
                )
                voxels.append(voxel)
                number_of_cells += 1
                accumulated_thickness += thickness
                for displayed_variable in displayed_variables:
                    variable_cell_data[displayed_variable].append(
                        variable_data[displayed_variable][-i - 1]
                    )

        points = np.vstack(voxels)
        cells_voxel = np.arange(number_of_cells * 8).reshape([number_of_cells, 8])
        grid = pv.UnstructuredGrid({CellType.VOXEL: cells_voxel}, points)

        for displayed_variable in displayed_variables:
            grid.cell_data[displayed_variable] = variable_cell_data[displayed_variable]
        grids.append(grid)

    blocks = pv.MultiBlock(grids)
    final_grid = blocks.combine()

    return final_grid


def to_surface_model(dataset, bottom_level, projected_variable="archel"):
    xc = dataset.dimen_x.values
    yc = dataset.dimen_y.values
    x, y = np.meshgrid(np.float32(yc), np.float32(xc))
    grid = pv.StructuredGrid(x, y, dataset["zcor"][-1, :, :].values)
    pv_top = grid.points.copy()
    pv_bottom = grid.points.copy()
    pv_bottom[:, -1] = bottom_level
    grid.points = np.vstack((pv_top, pv_bottom))
    grid.dimensions = [*grid.dimensions[0:2], 2]
    data_flat = dataset[projected_variable][-1, :, :].values.flatten(order="F")
    grid.point_data["values"] = np.hstack((data_flat, data_flat))

    # To pv.UnstructuredGrid by removing NaN cells from the StructuredGrid
    final_grid = grid.threshold()
    return final_grid


if __name__ == "__main__":
    ds = xr.open_dataset(
        r"n:\Projects\11209000\11209074\B. Measurements and calculations\test_results\MS_12_10\MS2_12_10plusNewSedClasses_rerun_mod - coarse-sand_sed_and_obj_data.nc"
    )
    save_file_voxels = r"n:\Projects\11209000\11209074\B. Measurements and calculations\test_results\MS_12_10\MS2_12_10_voxel.vtk"
    save_file_surface = r"n:\Projects\11209000\11209074\B. Measurements and calculations\test_results\MS_12_10\MS2_12_10_surface.vtk"
    voxel_model = to_voxel_model(ds, (100, 120), (100, 120))
    voxel_model.save(save_file_voxels, binary=True)

    surface_model = to_surface_model(ds, -10)
    surface_model.save(save_file_surface, binary=True)
