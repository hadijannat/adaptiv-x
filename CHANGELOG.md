# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial implementation of Adaptiv-X self-healing digital twin
- `adaptiv-monitor` service: Hybrid AI health monitoring (ML + FMU)
- `skill-broker` service: Semantic capability reasoning with policy engine
- `job-dispatcher` service: Capability-based routing with VDI/VDE 2193 bidding
- Health, Capability, and SimulationModels (IDTA 02005) submodels
- Docker Compose infrastructure (BaSyx v2, MQTT, MinIO)
- Automation scripts (bootstrap, seed, demo)
- GitHub Actions CI/CD pipeline
- Comprehensive documentation

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- All containers run as non-root users
- Multi-stage Docker builds for minimal attack surface

## [0.1.0] - 2025-01-01

### Added
- Initial release
