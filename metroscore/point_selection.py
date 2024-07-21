from collections import namedtuple
from typing import List

from shapely import contains
from shapely.geometry import Point, Polygon

Coordinate = namedtuple("Coordinate", ["lon", "lat"])


def cast_to_point(coord: Coordinate) -> Point:
    return Point(coord.lon, coord.lat)


def make_random_points(polygon: Polygon, N: int = 10) -> List[Coordinate]:
    """Creates `N` random points within the polygon `polygon`.

    Args:
        polygon (Polygon): shapely.geometry.Polygon
        N (int, optional): Number of points to generate. Defaults to 10.

    Returns:
        List[Coordinate]: List of Coordinate (longitude, latitude) points.
    """
    import numpy as np

    geoj = polygon.json()
    points: List[Coordinate] = []
    min_x, min_y = geoj["bbox"][0]
    max_x, max_y = geoj["bbox"][1]
    while len(points) < N:
        point = Coordinate(
            lon=np.random.uniform(min_x, max_x),
            lat=np.random.uniform(min_y, max_y),
        )
        if contains(polygon, cast_to_point(point)):
            points.append(point)
    return points


def make_hex_points(polygon: Polygon, N: int = 10) -> List[Coordinate]:
    """Creates `N` points that form a tessellating hex pattern within the provided `polygon`.

    Args:
        polygon (Polygon): shapely.geometry.Polygon
        N (int, optional): Number of points to generate. Defaults to 10.

    Returns:
        List[Coordinate]: List of Coordinate (longitude, latitude) points.
    """
    # TODO: implement
    return []
