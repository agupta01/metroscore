from collections import namedtuple

from shapely.geometry import Point, Polygon, contains

Coordinate = namedtuple("Coordinates", ["lon", "lat"])


def make_random_points(polygon, N=10):
    """
    Creates `N` random points within the polygon `polygon`.

    :param polygon: Polygon to generate points within.
    :type polygon: arcgis.geometry.Polygon
    :param N: Number of points to generate.
    :type N: int
    :return: List of (longitude, latitude) points.
    :rtype: list[tuple[float, float]]
    """
    import numpy as np
    from arcgis.geometry import Point, project

    # check if in 4326 spatial reference, if not, project to it
    if not polygon.spatial_reference or polygon.spatial_reference["latestWkid"] != 4326:
        polygon = project(
            geometries=[polygon],
            in_sr=polygon.spatial_reference,
            out_sr={"wkid": 4326, "latestWkid": 4326},
        )[0]

    points = []
    minx, miny, maxx, maxy = polygon.extent
    while len(points) < N:
        pnt = Point({"x": np.random.uniform(minx, maxx), "y": np.random.uniform(miny, maxy)})
        if polygon.contains(pnt):
            points.append(tuple(pnt.coordinates()))
    return points


def cast_to_point(coord: Coordinate) -> Point:
    return Point(coord.lon, coord.lat)


def make_random_points(polygon: Polygon, N: int = 10) -> list[Coordinate]:
    """Creates `N` random points within the polygon `polygon`.

    Args:
        polygon (Polygon): shapely.geometry.Polygon
        N (int, optional): Number of points to generate. Defaults to 10.

    Returns:
        list[Coordinate]: List of Coordinate (longitude, latitude) points.
    """
    import numpy as np

    geoj = polygon.json()
    points = []
    min_x, min_y = geoj["bbox"][0]
    max_x, max_y = geoj["bbox"][1]
    while len(points) < N:
        point = Coordinate(lon=np.random.uniform(min_x, max_x), lat=np.random.uniform(min_y, max_y))
        if contains(polygon, cast_to_point(point)):
            points.append(point)
    return points


def make_hex_points(polygon: Polygon, N: int = 10) -> list[Coordinate]:
    """Creates `N` points that form a tessellating hex pattern within the provided `polygon`.

    Args:
        polygon (Polygon): shapely.geometry.Polygon
        N (int, optional): Number of points to generate. Defaults to 10.

    Returns:
        list[Coordinate]: List of Coordinate (longitude, latitude) points.
    """
    pass  # TODO: implement


def make_grid_points(polygon, N=10):
    """
    Creates `N` points evenly spaced in a grid overlaid on the polygon `polygon`.

    :param polygon: Polygon to generate points within.
    :type polygon: arcgis.geometry.Polygon
    :param N: Number of points to generate.
    :type N: int
    :return: List of (longitude, latitude) points.
    :rtype: list[tuple[float, float]]
    """
    import numpy as np
    from arcgis.geometry import Point, project

    # check if in 4326 spatial reference, if not, project to it
    if not polygon.spatial_reference or polygon.spatial_reference["latestWkid"] != 4326:
        polygon = project(
            geometries=[polygon],
            in_sr=polygon.spatial_reference,
            out_sr={"wkid": 4326, "latestWkid": 4326},
        )[0]

    w0, l0, w1, l1 = polygon.extent
    width = w1 - w0
    length = l1 - l0
    extent_area = width * length
    # check ratio of extent rectangle area to polygon area, pad N by that amount
    # (we expect approx. that many points to be outside) the polygon and we want N points inside the polygon
    N = N * (extent_area / polygon.area)

    # compute rows and columns, this is done via the solution to the system N_w * N_l = N; N_w/N_l = w/l
    Nw = int(np.round(np.sqrt((width * N) / length)))
    Nl = int(np.round((length / width) * Nw))

    # build grid
    grid_w = np.linspace(w0, w1, Nw)
    grid_l = np.linspace(l0, l1, Nl)
    grid = []

    for x in grid_w:
        for y in grid_l:
            pnt = Point({"x": x, "y": y})
            if polygon.contains(pnt):
                grid.append(tuple(pnt.coordinates()))
    return grid
