import numpy as np

from gtpost.analyze import classifications

type ModelResult = None


def constrain_dchannel(modelresult: ModelResult, prediction_result: np.ndarray):
    # Water depth must be > 0 m to justify a channel prediction
    # TODO: add condition for dchannel to become tchannel
    prediction_result[
        (prediction_result == classifications.ArchEl.dchannel.value)
        & (modelresult.bottom_depth < -2)
    ] = classifications.ArchEl.undefined.value

    should_be_tchannel = (
        np.max(modelresult.dataset["MAX_UV"][:, 1, :].values, axis=1) < 0.3
    )
    # Only update dchannel to tchannel where should_be_tchannel is True (on time axis)
    for t_idx, should_convert in enumerate(should_be_tchannel):
        if should_convert:
            mask = prediction_result[t_idx] == classifications.ArchEl.dchannel.value
            prediction_result[t_idx][mask] = classifications.ArchEl.tchannel.value

    return prediction_result


def constrain_tchannel(modelresult: ModelResult, prediction_result: np.ndarray):
    # Water depth must be > 0 m to justify a channel prediction
    prediction_result[
        (prediction_result == classifications.ArchEl.tchannel.value)
        & (modelresult.bottom_depth < 0)
    ] = classifications.ArchEl.undefined.value
    return prediction_result


def constrain_mouthbar(modelresult: ModelResult, prediction_result: np.ndarray):
    # Limit the depth at which mouth bars are expected, based on the delta front depth
    prediction_result[
        (prediction_result == classifications.ArchEl.mouthbar.value)
        & (modelresult.bottom_depth > 4)
        & (modelresult.deposit_height < 0.05)
    ] = classifications.ArchEl.undefined.value
    return prediction_result


def constrain_dtundef(modelresult: ModelResult, prediction_result: np.ndarray):
    # split delta top into an undefined and bay fill unit
    prediction_result[
        (prediction_result == classifications.ArchEl.dtundef.value)
        & (modelresult.bottom_depth > 0)
    ] = classifications.ArchEl.dtbayfill.value
    return prediction_result


def constrain_beachridge(modelresult: ModelResult, prediction_result: np.ndarray):
    # A beach ridge must lie above the water level for it to be valid
    prediction_result[
        (prediction_result == classifications.ArchEl.beachridge.value)
        & (modelresult.bottom_depth > 0)
    ] = classifications.ArchEl.undefined.value
    return prediction_result


def constrain_beach(modelresult: ModelResult, prediction_result: np.ndarray):
    # Beach with more than 1 m water depth should be classified as upper shoreface
    # Below -2 m water depth, beach is undefined.
    prediction_result[
        (prediction_result == classifications.ArchEl.beach.value)
        & (modelresult.bottom_depth > 1.5)
    ] = classifications.ArchEl.ushoreface.value
    prediction_result[
        (prediction_result == classifications.ArchEl.beach.value)
        & (modelresult.bottom_depth < -1.5)
    ] = classifications.ArchEl.dtundef.value
    return prediction_result
