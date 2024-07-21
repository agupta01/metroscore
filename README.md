# metroscore

Metroscore is a Python package for analyzing transit quality in a region. It compares the accessibility of driving to the accessibility of public transit options (walking, biking, & public transit) for any given time, place, and trip length. The result is a collection of analyses for a region that can be analyzed to understand how spatial and temporal constraints affect transit performance.

# Installation

## From pip

Metroscore is available on the Python Package Index (PyPi). To install, run:

```bash
pip install metroscore
```

## From source

```bash
git clone https://www.github.com/agupta01/metroscore
cd metroscore
pip install -r requirements.txt
pip install -e .
```

# Getting Started

The following describes the most basic usage of Metroscore. For advanced usage, including configuration options, please see the [docs](https://metroscore.readthedocs.io).

## Datasets

1. **GTFS**: public transit agencies frequently publish their transit schedules in the [General Transit Feed Specification (GTFS)](https://developers.google.com/transit/gtfs/reference) format. This is a standard format for describing transit schedules and routes. `metroscore` uses the GTFS format to generate transit service areas.


## Building a transit network dataset

The first step of running any Metroscore analysis is to build the transit and drive datasets. To do so:

```python
from metroscore.metroscore import Metroscore
m = Metroscore(name="Brooklyn, NY")
m.build_drive()
m.build_transit(metro="./data/mta_metro_gtfs", bus="./data/mta_bus_gtfs")
```

## Running an analysis

With a built object, you can now pass in points, times of day, and trip durations to run an analysis:

```python
from metroscore.utils import start_time_to_seconds
start_times = list(map(start_time_to_seconds, ["7AM", "12PM", "4PM", "9PM"]))
results = m.compute(
    points=[(<lat>, <lon>), (<lat>, <lon>), ...],
    time_of_days=start_times,
    cutoffs=[600, 1200, 1800, 2400, 3000] # 10, 20, 30, 40, 50 minutes
)
```

Results may either be read directly as the return value of `compute()`, or by getting the `_results` object from the Metroscore object.

## Reading results

```python
m.get_score(location=(<lat>, <lon>), time_of_day=start_time_to_seconds("7AM"), cutoff=600)
```
