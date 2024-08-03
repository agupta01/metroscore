Tutorial
==============

Prerequisites
-------------

``metroscore``. To install this, see the installation instructions.

Datasets
--------

1. **GTFS**: public transit agencies frequently publish their transit schedules in the `General Transit Feed Specification (GTFS) <https://developers.google.com/transit/gtfs/reference>`_ format. This is a standard format for describing transit schedules and routes. ``metroscore`` uses the GTFS format to generate transit service areas.

Building a transit network dataset
----------------------------------

The first step of running any Metroscore analysis is to build the transit and drive datasets. To do so:

.. code-block:: python

    from metroscore.metroscore import Metroscore
    m = Metroscore(name="Brooklyn, NY")
    m.build_drive()
    m.build_transit(metro="./data/mta_metro_gtfs", bus="./data/mta_bus_gtfs")

Running an analysis
-------------------

With a built object, you can now pass in points, times of day, and trip durations to run an analysis:

.. code-block:: python

    from metroscore.utils import start_time_to_seconds
    start_times = list(map(start_time_to_seconds, ["7AM", "12PM", "4PM", "9PM"]))
    results = m.compute(
        points=[(<lat>, <lon>), (<lat>, <lon>), ...],
        time_of_days=start_times,
        cutoffs=[600, 1200, 1800, 2400, 3000] # 10, 20, 30, 40, 50 minutes
    )

Results may either be read directly as the return value of ``compute()``, or by getting the ``_results`` object from the Metroscore object.

Reading results
---------------

.. code-block:: python

    m.get_score(location=(<lat>, <lon>), time_of_day=start_time_to_seconds("7AM"), cutoff=600)