import xarray as xr

from gtpost.analyze import classifications

# Compression parameters
ENCODINGS = {
    "d50_per_sedclass": {"zlib": True, "complevel": 9},
    "xcor": {"zlib": True, "complevel": 9},
    "ycor": {"zlib": True, "complevel": 9},
    "zcor": {"zlib": True, "complevel": 9},
    "subsidence": {"zlib": True, "complevel": 9},
    "preserved_thickness": {"zlib": True, "complevel": 9},
    "diameter": {"zlib": True, "complevel": 9},
    "fraction": {"zlib": True, "complevel": 9},
    "sorting": {"zlib": True, "complevel": 9},
    "porosity": {"zlib": True, "complevel": 9},
    "permeability": {"zlib": True, "complevel": 9},
    "vfractions": {"zlib": True, "complevel": 9},
    "mfractions": {"zlib": True, "complevel": 9},
    "archel": {"zlib": True, "complevel": 9},
    "subenv": {"zlib": True, "complevel": 9},
}


def create_sed_and_obj_dataset(p):
    data_vars = dict(
        d50_per_sedclass=(
            "dimen_f",
            p.d50_input,
            dict(
                long_name="D50 values defining each sediment class",
                variable_type="D3D output",
                units="meter",
            ),
        ),
        xcor=(
            ("dimen_x", "dimen_y"),
            p.dataset.XCOR.values,
            dict(
                long_name="x coordinates of cells",
                variable_type="D3D output",
                units="meter",
            ),
        ),
        ycor=(
            ("dimen_x", "dimen_y"),
            p.dataset.YCOR.values,
            dict(
                long_name="y coordinates of cells",
                variable_type="D3D output",
                units="meter",
            ),
        ),
        zcor=(
            ("dimen_t", "dimen_x", "dimen_y"),
            p.zcor,
            dict(
                long_name="z coordinates of cells",
                variable_type="D3D output",
                units="meter",
            ),
        ),
        subsidence=(
            ("dimen_t", "dimen_x", "dimen_y"),
            p.subsidence,
            dict(
                long_name="Subsidence in meter per timestep and location",
                variable_type="D3D output",
                units="meter",
            ),
        ),
        preserved_thickness=(
            ("dimen_t", "dimen_x", "dimen_y"),
            p.preserved_thickness,
            dict(
                long_name="Final preserved thickness of deposits",
                variable_type="calculated",
                units="meter",
            ),
        ),
        deposition_age=(
            ("dimen_t", "dimen_x", "dimen_y"),
            p.deposition_age,
            dict(
                long_name="Timestep at which deposition took place",
                variable_type="calculated",
                units="-",
            ),
        ),
        diameter=(
            ("dimen_t", "dimen_x", "dimen_y"),
            p.d50,
            dict(
                long_name="Overall D50 value for cell, based on combination of classes",
                variable_type="calculated",
                units="meter",
            ),
        ),
        fraction=(
            ("dimen_t", "dimen_x", "dimen_y"),
            p.sandfraction,
            dict(
                long_name="fraction of sediment that is sand",
                variable_type="calculated",
                units="-",
            ),
        ),
        sorting=(
            ("dimen_t", "dimen_x", "dimen_y"),
            p.sorting,
            dict(
                long_name="Sorting value based on Folks 1968",
                variable_type="calculated",
                units="-",
            ),
        ),
        porosity=(
            ("dimen_t", "dimen_x", "dimen_y"),
            p.porosity,
            dict(
                long_name="Porosity based on Takebayashi and Fujita 2014",
                variable_type="calculated",
                units="-",
            ),
        ),
        permeability=(
            ("dimen_t", "dimen_x", "dimen_y"),
            p.permeability,
            dict(
                long_name="Permeability based on Panda & Lake 1994",
                variable_type="calculated",
                units="m2",
            ),
        ),
        vfractions=(
            ("dimen_t", "dimen_f", "dimen_x", "dimen_y"),
            p.vfraction,
            dict(
                long_name="volume fraction of each grain size class per cell",
                variable_type="D3D output",
                units="fraction",
            ),
        ),
        mfractions=(
            ("dimen_t", "dimen_f", "dimen_x", "dimen_y"),
            p.dmsedcum_final,
            dict(
                long_name="mass fraction of each grain size class per cell",
                variable_type="D3D output",
                units="fraction",
            ),
        ),
        archel=(
            ("dimen_t", "dimen_x", "dimen_y"),
            p.architectural_elements,
            dict(
                long_name="architectural element",
                variable_type="calculated",
                units="nr 0 to 6",
            ),
        ),
        subenv=(
            ("dimen_t", "dimen_x", "dimen_y"),
            p.subenvironment,
            dict(
                long_name="subenvironment",
                variable_type="calculated",
                units="nr 0 to 3",
            ),
        ),
    )
    ds = xr.Dataset(data_vars)
    ds["subenv"].attrs["encoding"] = classifications.subenvironment_codes
    ds["subenv"].attrs["names"] = classifications.subenvironment_names
    ds["archel"].attrs["encoding"] = classifications.archel_codes
    ds["archel"].attrs["names"] = classifications.archel_names

    return ds
