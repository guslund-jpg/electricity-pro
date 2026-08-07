# Changelog

## [Unreleased]

### Added

- Added an optional Monthly Peak Hour Time sensor mirrored from a configured
  Home Assistant timestamp source.

### Changed

- Clarified the existing mirrored Energy sensor as Energy Today while keeping
  its stable unique ID and recorded history compatible with existing setups.

### Documentation

- Consolidated release planning into the canonical root roadmap and aligned
  the v0.9 scope with its Daily Statistics and Dashboard Experience milestone.

## [0.8.0] - 2026-08-07

### Added

- Added an optional Good Time to Use Electricity insight based on a configured
  Effective Price threshold.
- Added an Effective Price sensor with optional fixed grid-fee and tax/markup
  adjustments per kWh.
- Added a Cost This Month sensor derived from the configured cumulative Cost
  Today source.
- Added an Energy This Month sensor derived from the configured cumulative
  energy source.
- Added persistent monthly accumulation with calendar-month and source-meter
  reset handling.

### Fixed

- Seed Cost This Month with the available Cost Today value on first setup.

### Changed

- Clarified that Effective Price grid-fee and tax/markup inputs should include
  VAT, with guidance for the standard Swedish 2026 energy tax.

## [0.7.0] - 2026-08-02

### Added

- Cost Today
- Remaining Cost Today
- Peak Power Today
- Monthly Peak Hour Consumption
- Three-phase Current (L1/L2/L3)
- Three-phase Voltage (L1/L2/L3)

### Improved

- Provider abstraction
- Configuration flow
- Documentation
- Dashboard example

### Quality

- 144 automated tests
- Home Assistant verification

## [0.6.0] - Foundation Release 2026-07-26

### Added

- Initial public release of Electricity Pro.
- Provider abstraction framework.
- Home Assistant integration foundation.
- Core electricity entities and sensors.
- Project architecture documentation.
- Continuous Integration (CI) workflows.
- Comprehensive automated test suite.
- Contributor documentation.
- Initial project design templates.
- Three-phase current sensors (L1, L2, L3)
- Support for ampere and milliampere source sensors
- Comprehensive provider and sensor tests
- Added optional Voltage L1, Voltage L2 and Voltage L3 sensors.
- Added normalization for volt and millivolt source sensors.
- Added an optional Monthly Peak Hour Consumption sensor.
- Added support for Wh and kWh source values.

### Changed

- Improved project structure and package organisation.
- Standardised naming and coding conventions.
- Improved documentation throughout the project.

### Fixed

- Various stability and reliability improvements prior to the public release.
- Periodic refresh of remaining cost sensor.

### Documentation

- Added `README.md`
- Added `CONTRIBUTING.md`
- Added `CHANGELOG.md`
- Added project design documentation.

---
