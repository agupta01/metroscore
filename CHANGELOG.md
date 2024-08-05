Changelog
=========

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

## [v1.0.0-rc.1](https://github.com/agupta01/metroscore/releases/tag/v1.0.0-rc.1) - 2024-08-05

## Added
- Rewrite with OSS packages
- Add Metroscore object

## Changed
- README

## [v0.2.0](https://github.com/agupta01/metroscore/releases/tag/v0.2.0) - 2023-03-24

## Added
- `make_grid_points` function to generate a grid of points within a polygon (useful for metroscore heatmaps)
- Support for time-of-day metroscore analysis

## Removed
- Functions in `metroscore` module

## Changed
- Functions now organized in submodules: `point_selection`, `service_areas`, `analysis`
- New "Metroscore 101" tutorial in docs

## Fixed
- Point generation now works for polygons in non-epsg:4326 projections
- Network datasets in non-epsg:4326 projections are now supported
- Drive time service areas use faster ArcGIS functional backend

## [v0.1.1](https://github.com/agupta01/metroscore/releases/tag/v0.1.1) - 2023-03-16

## Fixed
- Release process

## [v0.1.0](https://github.com/agupta01/metroscore/releases/tag/v0.1.0) - 2023-03-16

## Added
- Function to generate random points within a polygon
- Function to generate public transit service areas
- Function to generate drive-time service areas
- Function to compute metroscore per service area
