import numpy as np

from metroscore.service_areas import floyd_warshall_fast, floyd_warshall_slow


def test_floyd_warshall_small_matrix():
    INPUT = np.array(
        [
            [0.0, np.inf, -2.0, np.inf],
            [4.0, 0.0, 3.0, np.inf],
            [np.inf, np.inf, 0.0, 2.0],
            [np.inf, -1.0, np.inf, 0.0],
        ]
    )

    OUTPUT = np.array(
        [[0.0, -1.0, -2.0, 0.0], [4.0, 0.0, 2.0, 4.0], [5.0, 1.0, 0.0, 2.0], [3.0, -1.0, 1.0, 0.0]]
    )

    assert np.allclose(floyd_warshall_fast(INPUT), OUTPUT)
    assert np.allclose(floyd_warshall_slow(INPUT), OUTPUT)
