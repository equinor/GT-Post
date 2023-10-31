import numpy as np
import pyvista as pv
import xarray as xr


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
        r"n:\Projects\11209000\11209074\B. Measurements and calculations\test_results\Roda_051\Sed_and_Obj_data_comp3.nc"
    )
    [ds[da].nbytes / 1e9 for da in ds.data_vars]
    xc = ds.dimen_x.values
    yc = ds.dimen_y.values
    bottom = -10

    for i in ds.dimen_t.values:
        file = (
            r"n:\Projects\11209000\11209074\B. Measurements and calculations\test_results\Roda_051"
            + f"\\Roda_051_{i}.vtk"
        )
        array = ds["zcor"][i, :, :].values
        projected_array = ds["archel"][i, :, :].values
        print(f"writing timestep {i}")
        to_pv_model(xc, yc, array, bottom, file, binary=True)
