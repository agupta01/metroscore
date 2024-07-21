import pandas as pd


def compute_metroscore(transit_areas, drive_areas, bonus_weight=2.0, return_all=False):
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
        left=transit_areas.to_crs(3857),
        right=drive_areas.to_crs(3857),
        on="cutoffs",  # TODO: join on location, TOD, cutoff
        how="inner",
        suffixes=("_transit", "_drive"),
    )

    # compute preliminaries
    joined_sa["area(D)"] = joined_sa["geometry_drive"].area
    joined_sa["area(D - T)"] = (
        joined_sa["geometry_drive"].difference(joined_sa["geometry_transit"]).area
    )
    joined_sa["area(T - D)"] = (
        joined_sa["geometry_transit"].difference(joined_sa["geometry_drive"]).area
    )

    # compute TDTC and TB
    joined_sa["TDTC"] = (joined_sa["area(D)"] - joined_sa["area(D - T)"]) / joined_sa[
        "area(D)"
    ]
    joined_sa["TB"] = joined_sa["area(T - D)"] / joined_sa["area(D)"]

    # compute final metroscore
    joined_sa["Metroscore"] = joined_sa["TDTC"] + (bonus_weight * joined_sa["TB"])

    if return_all:
        return joined_sa
    else:
        return joined_sa[["cutoff", "Metroscore"]]  # TODO: return location, TOD as well
