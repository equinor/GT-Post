import numba
import numpy as np


def get_d50input(sedfile, sedtype, rho_p, sedfile_line):
    """calculate the d50 for sediment input:
    if the sedtype is not mud, then directly read d50;
    if the sedtype is mud, using stokes to calculate d50
    """
    d50input = []
    rhof = 1000
    mu = 0.001
    g = 9.81
    """
        basic parameters for stokes equation:
        rho_f = 1000 fluid density
        rho_p: specific density, reading from sed_file
        g:9.81
        mu: 0.001 dynamic viscosity
    """
    # get the number of sediment fraction
    for stype in range(len(sedtype)):
        if sedtype[stype] == "mud":
            linetoread = sedfile_line[stype] + 3
            with open(sedfile, encoding="cp1252") as fobj:
                line = fobj.readlines()
                svelocity = float(line[linetoread].split()[2])
                d50c = np.sqrt(18 * mu * svelocity / g / (rho_p[stype] - rhof))
                d50input.append(d50c)
        if sedtype[stype] == "sand":
            linetoread = sedfile_line[stype] + 2
            with open(sedfile, encoding="cp1252") as fobj:
                line = fobj.readlines()
                d50c = float(line[linetoread].split()[2])
                d50input.append(d50c)
    return d50input


def calculate_fraction(rho_db: np.array, dmsedcum_final: np.array) -> np.array:
    """
    Calculate the volumetric fraction of sediment.
    This function computes the volumetric fraction of sediment by dividing the cumulative
    sediment mass by the dry bed density and normalizing the result.

    Parameters
    ----------
    rho_db : np.array
        Array of dry bed densities.
    dmsedcum_final : np.array
        Array of cumulative sediment mass.

    Returns
    -------
    np.array
        Array of volumetric fractions of sediment.
    """
    vfraction = np.zeros_like(dmsedcum_final)
    old_err_state = np.seterr(divide="ignore", invalid="ignore")

    # derive the volumetric sed flux by dividing by dry bed density
    dvsedcum = dmsedcum_final / rho_db[:, np.newaxis, np.newaxis]

    dvsedcum[dmsedcum_final <= 0] = 0
    sumsedvcum = np.sum(dvsedcum, axis=1)

    vfraction = np.divide(
        dvsedcum,
        sumsedvcum[:, np.newaxis, :, :],
        where=sumsedvcum[:, np.newaxis, :, :] != 0,
    )
    vfraction[np.isnan(vfraction) == 1] = 0
    # go back to original error state
    np.seterr(**old_err_state)
    return vfraction


def calculate_sand_fraction(sedtype: list, vfraction: np.array) -> np.array:
    """
    Calculate the sand fraction from the given sediment types and volume fractions.

    Parameters
    ----------
    sedtype : list
        A list of sediment types.
    vfraction : np.array
        A numpy array representing the volume fractions of different sediment types.
    Returns
    -------
    np.array
        A numpy array containing the summed volume fractions of sand, with mud fractions set to zero.
    """
    vfrac = vfraction.copy()
    num_stypes = np.shape(vfrac)[1]
    for stype in range(num_stypes):
        if sedtype[stype] == "mud":
            vfrac[:, stype, :, :] = 0
    return np.sum(vfrac, axis=1).astype(np.float32)


def calculate_sorting(diameters: np.ndarray, percentage2cal: list) -> np.ndarray:
    """
    Calculate the sorting parameter of sediment grain size distribution using Folks
    (1968) method.

    Parameters
    ----------
    diameters : np.ndarray
        A multi-dimensional array of sediment grain diameters.
    percentage2cal : list
        A list of percentage values used to calculate the sorting parameter.
        It should contain the values 10, 16, 84, and 90.

    Returns
    -------
    np.ndarray
        The calculated sorting parameter for the given sediment grain size distribution.

    Notes
    -----
    The sorting parameter is calculated using the formula:
    sorting = (phi_84 - phi_16) / 4 + (phi_90 - phi_10) / 6.6
    where phi_x is the grain size at the xth percentile in grain size phi.
    """
    index10 = percentage2cal.index(10)
    index16 = percentage2cal.index(16)
    index84 = percentage2cal.index(84)
    index90 = percentage2cal.index(90)
    # using Folks 1968 for calculate sorting parameter.
    diameters_phi = -np.log2(diameters)
    sorting = (
        diameters_phi[:, :, :, index84] - diameters_phi[:, :, :, index16]
    ) / 4 + (diameters_phi[:, :, :, index90] - diameters_phi[:, :, :, index10]) / 6.6
    return -sorting


@numba.njit
def calculate_distribution(fraction_data, d50input):
    # Select only relevant xdata
    xdata = d50input[fraction_data > 0]
    xphi = -np.log2(1000 * xdata)
    if len(xdata) > 0:
        xdiff = np.diff(xphi)
        xphi = np.hstack(
            (
                np.array([xphi[0] - 0.5], dtype=np.float32),
                xphi[:-1] + (0.5 * xdiff),
                np.array([xphi[-1] + 0.5], dtype=np.float32),
            )
        )
        # cdf value
        cdf = np.cumsum(fraction_data[fraction_data > 0])
        cdf = np.hstack((np.array([0], dtype=np.float32), cdf))
        # linear fit
        xnew = np.arange(-1, 8, 0.1)
        ynew = np.interp(xnew, xphi, cdf)
        fraction_data = np.diff(ynew)
        xnewd50 = (2 ** (-(xnew[1:]))) / 1000

        if np.abs(np.sum(fraction_data) - 1) < 0.1:
            # weighted distribution
            minval = np.min(fraction_data[(fraction_data > 0.001).nonzero()])
            amount = np.zeros(len(xnewd50), dtype=np.int32)

            for i, d50 in enumerate(xnewd50):
                amount[i] = np.int32(np.round(fraction_data[i] / minval))

            total_samples = np.sum(amount)
            cumsum_samples = np.cumsum(amount)
            d50distributed = np.zeros(total_samples, dtype=np.float32)

            for i, d50 in enumerate(xnewd50[:-2]):
                d50distributed[cumsum_samples[i] : cumsum_samples[i + 1]] = np.full(
                    cumsum_samples[i + 1] - cumsum_samples[i], d50
                )

            phidistributed = -np.log2(1000 * d50distributed)
            phidistributed = phidistributed[np.isfinite(phidistributed)]

            # Standard deviation of the sed distribution
            averaged = np.nanmean(d50distributed)
            averagep = np.nanmean(phidistributed)
            distr_sdev = np.nanstd(phidistributed)
            # Porosity based on empirical fit by Takebayashi & Fujita (2014)
            poros = 0.38 * (
                (3.7632 * (distr_sdev**-0.7552))
                / (1 + (3.7632 * (distr_sdev**-0.7552)))
            )
            # Coefficient of variation of sed distribution
            c_dp = distr_sdev / averagep
            # Skewness of the sediment distribution
            skw = (
                (1 / len(d50distributed)) * np.sum((d50distributed - averaged) ** 3)
            ) / (
                ((1 / len(d50distributed)) * np.sum((d50distributed - averaged) ** 2))
                ** (1.5)
            )
            # Turtuosity based on porosity after Ahmadi et al. (2011)
            turt = np.sqrt(
                ((2 * poros) / (3 * (1 - 1.209 * ((1 - poros) ** (2 / 3))))) + (1 / 3)
            )
            firstel = (averaged**2 * poros**3) / (72 * turt * ((1 - poros) ** 2))
            secel = ((skw * c_dp + 3 * c_dp**2 + 1) ** 2) / ((1 + c_dp**2) ** 2)
            perm = firstel * secel
        else:
            # This occurs if the sum of fractions is not equal to 1 with a tolerance of 0.01
            perm = np.nan
            poros = np.nan
    else:
        perm = np.nan
        poros = np.nan
        xnew = np.arange(-1, 8, 0.1)
        ynew = np.full_like(xnew, np.nan)
    return (ynew, xnew, poros, perm)


@numba.njit(parallel=True)
def calculate_diameter(d50input, percentage2cal, vfraction):
    if len(vfraction.shape) == 4:
        nt, nlyr, nx, ny = vfraction.shape

    diameters = np.zeros((nt, nx, ny, len(percentage2cal)))
    porosity = np.zeros((nt, nx, ny))
    permeability = np.zeros_like(porosity)
    diameters[0] = np.nan
    porosity[0] = np.nan
    permeability[0] = np.nan
    for it in numba.prange(nt):
        for ix in numba.prange(nx):
            for iy in numba.prange(ny):
                fraction_data = vfraction[it, :, ix, iy]
                # return the phi value needs to be changed back to meters
                (
                    cdf,
                    xvalue,
                    porosity[it, ix, iy],
                    permeability[it, ix, iy],
                ) = calculate_distribution(fraction_data, d50input)
                # If poro/perm returns nan, find the last known value from previous time steps
                # This is then still the poros/perm at the surface
                # dmsedcum_final += 1
                if np.isnan(porosity[it, ix, iy]):
                    lastknown_idxs = (porosity[:, ix, iy] > 0.0).nonzero()[-1]
                    if len(lastknown_idxs) != 0:
                        porosity[it, ix, iy] = porosity[lastknown_idxs[-1], ix, iy]
                        permeability[it, ix, iy] = permeability[
                            lastknown_idxs[-1], ix, iy
                        ]
                for ipercen in range(len(percentage2cal)):
                    diameters[it, ix, iy, ipercen] = 2 ** (
                        -xvalue[
                            np.argmin(
                                np.abs(cdf - (1 - (0.01 * percentage2cal[ipercen])))
                            )
                        ]
                    )
                    # set diameter to zero if there is no deposition
                    # because in the models, we don't have 2000mm,
                    # if it is equals to 2000, then there it assigns to the value
                    # below it
                    if diameters[it, ix, iy, ipercen] == 2:
                        if it > 0:
                            diameters[it, ix, iy, ipercen] = diameters[
                                it - 1, ix, iy, ipercen
                            ]
                        else:
                            diameters[it, ix, iy, ipercen] = 0
                    else:
                        pass
    return (diameters, porosity, permeability)
