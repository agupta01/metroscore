# metroscore

Metroscore is a Python package for analyzing transit quality in a region. 

### Abstract
In recent years, rideshare alternatives have significantly impacted public transit ridership in large American cities by offering speed and convenience. To address this issue, transit agencies require a measure of transit mode preference to determine when and where riders choose public transit over car-based options. This paper introduces Metroscore, an arcpy-powered API that computes a multidimensional preference statistic for transit agencies to evaluate their services in comparison to car-based transit. Metroscore allows transit planners to input their own networks or build one for their city and analyze the effects of potential changes on the transit system under various spatiotemporal constraints. The methodology is illustrated through case studies on three major cities: Cincinnati, San Diego, and New York. With Metroscore, transit agencies can make informed decisions regarding the development of transit services, respond to the growing popularity of rideshare options, and provide strong evidence to support transit expansion proposals. Metroscore is available as an open-source, pip-installable package, with opportunities for feedback and collaboration on future developments. This paper not only introduces the innovative tool, but also highlights its potential in improving transit quality and fostering sustainable urban mobility.

# Installation

## Prerequisites

1. `arcgis`
2. `arcpy`. This is installed with ArcGIS Pro and is required to generate transit service areas.

## Install using pip

```bash
pip install metroscore
```

## Install from source

```bash
git clone https://github.com/agupta01/metroscore.git
cd metroscore
pip install -e .
```


# Getting Started

## Datasets

1. **GTFS**: public transit agencies frequently publish their transit schedules in the [General Transit Feed Specification (GTFS)](https://developers.google.com/transit/gtfs/reference) format. This is a standard format for describing transit schedules and routes. `metroscore` uses the GTFS format to generate transit service areas.
2. **Streets**: In order for the network to know where people can and cannot walk, you will need a polyline dataset of streets. This dataset should also have a field called `RestrictPedestrians` to indicate whether pedestrians are allowed to walk on that street. If this field is not present, you should think about how to generate this using the existing fields (one approach, for example, might be to look at street speed, if available).


## Building a transit network dataset

> **Pro tip:** Generate your network dataset on ArcGIS desktop, as this will allow you to visually inspect the quality of it. `metroscore` has a function to do this using arcpy, but it assumes a certain data structure and quality and may fail without warning.

Follow the instructions [here](https://pro.arcgis.com/en/pro-app/latest/help/analysis/networks/create-and-use-a-network-dataset-with-public-transit-data.htm) to generate a transit network dataset. This will generate a network dataset that can be used to generate transit service areas.

## Selecting points

In order to run, metroscore needs one or more candidate points to score. These points can be manually selected or generated using the functions in `metroscore.point_selection`. For example, to make a grid of approximately 100 points inside San Diego,

```python
# get san diego boundary
sd_boundary = gis.content.get("4a27b8717df945298546fdf3456b0a16")
sd_poly = sd_boundary.layers[0].query("NAME = 'SAN DIEGO'").sdf.iloc[0].SHAPE
points = make_grid_points(sd_poly, N=100)
len(points)
```
87

## Generating service areas
Next, one must generate driving and transit service areas for each point. This is done using the `metroscore.service_areas` module. For example, to generate a 30 minute driving service area for each point,

```python
time = datetime.datetime(2019, 1, 1, 8, 0, 0)
duration = [30]
metro_sdf = get_metro_service_areas(nd_path, points, cutoffs=duration, time_of_day=time)
drive_sdf = get_drive_time_service_areas(points, cutoffs=duration, time_of_day=time)
```

## Scoring points
Finally, we can use the `metroscore.analysis` module to generate metroscores. This will generate a metroscore for every service area generated inn the previous step (that is, for every point, duration and time combination). To do this,

```python
mts_df = sd_mts_loc = compute_metroscore(metro_sdf, drive_sdf)
```

The resultant dataframe will have a column called "Metroscore" and another column named "Name" with each row being of the form "<Location ID> : 0 - <Duration>". You may then groupby or average across the different dimensions to analyze the metroscore results. To get the overall metroscore, simply average the Metroscore column as follows:

```python
mts_df.Metroscore.mean()
```
0.045
