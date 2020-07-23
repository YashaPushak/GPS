# Change Log

All notable changes to this project will be documented in this file.

## [1.2.0] - 2020-07-xx

### Added

 - GPS now exposes a new python interface for target algorithm runners/wrappers. This allows GPS to directly
   call target algorithm runs without using command line calls and reading from output files written to the 
   disk. The new interface also supports pre-initialization of datasets/instances, avoiding the need to load
   large amounts of identical instance data prior to performing every single target algorithm run.

### Changed
 - GPS uses a new permutation test implmentation that is ~10x faster.

## [1.1.1] - 2020-08-05

### Fixed
 - Previous version of GPS contained a bug causing any configuration that was censored a single time using
   the user-specified running time cutoff to be treated as if they had been censored due to an adaptive cap.
   For large running time cutoffs, this rarely affects the performance of GPS, in fact, in may provide a
   small speedup as GPS will reject bad configurations more quickly. However, if the running time cutoff is
   small enough to occasionally censor the runs of good configurations, then the output from GPS will likely
   be quite poor, since GPS will effectively be random rejecting configurations. This bug did not exist in the
   original version of GPS studied in the 2020 GECCO paper: "Golden Parameter Search: Exploiting Structure to
   Quickly Configure Parameters in Parallel".

## [1.1.0] - 2020-07-17

### Added
 - GPS now supports solution quality optimization! See `examples/artificial-classifier` for an example on how to use it. More information is available in `README.md`.
 - GPS now has a changelog.

## [1.0.1] - 2020-07-16

### Added
 - New instructions for setting up a redis database installation, provided by Marie Anastacio.
 - Several minor bugfixes and additions to the documentation.

## [1.0.0] - 2020-07-02

### Added
- First public-ready version of GPS!
