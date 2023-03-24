import pandas as pd


def compute_metroscore(transit_sedf, drive_sedf, bonus_weight=2.0, return_all=False):
    """
    Computes the row-wise metroscore for each computed service area.

    :param transit_sedf: SEDF with shapes of transit service areas and unique names of
    format "<Facility ID> : <FromBreak> - <ToBreak>".
    :type transit_sedf: pandas.DataFrame
    :param drive_sedf: SEDF with shapes of drive-time service areas and unique names
    matching those in `transit_sedf`.
    :type drive_sedf: pandas.DataFrame
    :param bonus_weight: float of weightage to give to transit bonus., defaults to 2.0
    :type bonus_weight: float, optional
    :param return_all: whether to return all columns (including intermediate steps) or
    just the final metroscore., defaults to False
    :type return_all: bool, optional
    :return: Pandas DataFrame with schema:
    {
        "Name": (str) unique service area names of format "<Facility ID> : <FromBreak> - <ToBreak>",
        "Metroscore": (float) metroscore of service area
    }
    :rtype: pandas.DataFrame
    """
    # merge transit and drive sedfs
    joined_sa = pd.merge(
        left=transit_sedf[["Name", "SHAPE"]],
        right=drive_sedf[["Name", "SHAPE"]],
        on="Name",
        how="inner",
        suffixes=("_transit", "_drive"),
    ).astype({"SHAPE_transit": "geometry", "SHAPE_drive": "geometry"})

    # compute preliminaries
    joined_sa["area(D)"] = joined_sa.SHAPE_drive.geom.area
    joined_sa["area(D - T)"] = joined_sa.SHAPE_drive.geom.difference(
        joined_sa.SHAPE_transit
    ).geom.area
    joined_sa["area(T - D)"] = joined_sa.SHAPE_transit.geom.difference(
        joined_sa.SHAPE_drive
    ).geom.area.fillna(
        0.0
    )  # when the difference is a null set arcgis returns NaN

    # compute TDTC and TB
    joined_sa["TDTC"] = (joined_sa["area(D)"] - joined_sa["area(D - T)"]) / joined_sa["area(D)"]
    joined_sa["TB"] = joined_sa["area(T - D)"] / joined_sa["area(D)"]

    # compute final metroscore
    joined_sa["Metroscore"] = joined_sa["TDTC"] + (bonus_weight * joined_sa["TB"])

    if return_all:
        return joined_sa
    else:
        return joined_sa[["Name", "Metroscore"]]
