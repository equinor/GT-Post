import numpy as np


class BathymetryValidationError(Exception):
    pass


"""
BATHYMETRY BUILDER IS WORK IN PROGRESS AND NOT TO BE USED YET
"""


class BathymetryBuilder:

    def __init__(
        self,
        initial_grid: np.ndarray,
        nan_value: int | float = -999.0,
        basin_slope: float = 0.1,
        fluvial_slope: float = 0.01,
        coast_angle: float = 0,
        fluvial_length: int = 100,
        fluvial_width: int = 20,
        channel_depth: float = 4,
        floodplain_depth: float = 0.5,
        channel_floodplain_ratio: float = 0.2,
        channel_count: int = 1,
        channel_separation: bool = False,
    ):
        self.grid = np.full_like(initial_grid, channel_depth)
        self.nx, self.ny = self.grid.shape
        self.nan_value = nan_value
        self.basin_slope = basin_slope
        self.fluvial_slope = fluvial_slope
        self.coast_angle = coast_angle
        self.fluvial_length = fluvial_length
        self.fluvial_width = fluvial_width
        self.channel_depth = channel_depth
        self.floodplain_depth = floodplain_depth
        self.channel_floodplain_ratio = channel_floodplain_ratio
        self.channel_count = channel_count
        self.channel_separation = channel_separation
        self.combined_fluvial_width = self.fluvial_width * self.channel_count
        self.nancount_fluvial = int((self.nx - self.combined_fluvial_width) / 2)

        self.__validate()

    def __validate(self):
        validation_errors = ""
        if self.coast_angle > 45 or self.coast_angle < 0:
            validation_errors += "- coast_angle must be between 0 and 45 degrees\n"
        if self.fluvial_length > np.ceil(self.ny / 3) or self.fluvial_length < 10:
            validation_errors += (
                f"- fluvial_length must be between 10 and {np.ceil(self.ny/3)}\n"
            )
        if self.channel_count < 1 or self.channel_count > 4:
            validation_errors += "- channel_count must be between 1 and 4 channels\n"
        if self.channel_separation and self.channel_count == 1:
            validation_errors += (
                "- Cannot have channel separation when channel_count = 1\n"
            )
        if self.combined_fluvial_width > np.ceil(self.nx / 2):
            validation_errors += (
                f"- Combined river width must be smaller than {np.ceil(self.nx / 2)}\n"
            )

        if len(validation_errors) > 0:
            raise BathymetryValidationError(validation_errors)

    def computational_grid_mask(self):
        self.grid[: self.nancount_fluvial, : self.fluvial_length + 1] = self.nan_value
        self.grid[-self.nancount_fluvial :, : self.fluvial_length + 1] = self.nan_value

    def add_funnel_coastline(self):
        if self.coast_angle > 0:
            dy_coastline_cells = int(
                np.ceil(self.nancount_fluvial * np.tan(np.deg2rad(self.coast_angle)))
            )

            dxdy = self.nancount_fluvial / dy_coastline_cells

            for i in range(dy_coastline_cells):
                coastline_cells_i = int(np.round(self.nancount_fluvial - (i * dxdy)))
                self.grid[:coastline_cells_i, self.fluvial_length + 1 + i] = -5
                self.grid[-coastline_cells_i:, self.fluvial_length + 1 + i] = -5

    def add_channels_and_floodplains(self):
        # TODO: perhaps make separation obstacles in different method...
        self.combined_fluvial_width
        channel_width = int(
            np.round(self.fluvial_width * self.channel_floodplain_ratio)
        )
        floodplain_single_side_width = int(
            np.round((self.fluvial_width - channel_width) / 2)
        )
        if self.channel_separation:
            obstacle_width = int(np.ceil(0.4 * floodplain_single_side_width))
            fluvial_single_row = np.hstack(
                [
                    np.full(obstacle_width, self.nan_value),
                    np.full(
                        floodplain_single_side_width - obstacle_width,
                        self.floodplain_depth,
                    ),
                    np.full(channel_width, self.channel_depth),
                    np.full(
                        floodplain_single_side_width - obstacle_width,
                        self.floodplain_depth,
                    ),
                    np.full(obstacle_width, self.nan_value),
                ]
            )
            fluvial_row_data = np.hstack(
                [fluvial_single_row for c in range(self.channel_count)]
            )
        else:
            fluvial_single_row = np.hstack(
                [
                    np.full(floodplain_single_side_width, self.floodplain_depth),
                    np.full(channel_width, self.channel_depth),
                    np.full(floodplain_single_side_width, self.floodplain_depth),
                ]
            )
            fluvial_row_data = np.hstack(
                [fluvial_single_row for c in range(self.channel_count)]
            )

        fluvial_start_idx = int(
            np.round((self.nx / 2) - (self.combined_fluvial_width / 2))
        )

        for i in range(self.fluvial_length):
            self.grid[
                fluvial_start_idx : fluvial_start_idx + self.combined_fluvial_width, i
            ] = fluvial_row_data

    def make_bathymetry(self) -> np.ndarray:
        self.computational_grid_mask()
        self.add_funnel_coastline()
        self.add_channels_and_floodplains()
