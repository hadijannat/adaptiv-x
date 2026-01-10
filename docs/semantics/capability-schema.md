# Capability Submodel Schema

This document defines the canonical Capability Submodel used by Adaptiv-X for routing and negotiation. The schema is intentionally small, semantically anchored, and aligned with capability-based engineering practice.

## Submodel metadata

- `idShort`: `Capabilities`
- `semanticId`: `urn:adaptivx:submodel:capability:1.0`
- `administration`: versioned (`1.1.0` in current assets)

## Core element set (ProcessCapability:Milling)

Path: `Capabilities/ProcessCapability:Milling`

Required properties:
- `SurfaceFinishGrade` (`urn:adaptivx:concept:surfacefinishgrade:1.0`) — grade A/B/C used by the dispatcher.
- `ToleranceClass` (`0173-1#02-AAE583#006`) — tolerance class string (e.g., `±0.02mm`).
- `AssuranceState` (`urn:adaptivx:concept:assurancestate:1.0`) — `assured`, `offered`, `notAvailable`.
- `EnergyCostPerPart_kWh` (`0173-1#02-AAT812#001`) — energy consumption per part.

Optional properties:
- `CarbonFootprintGPerPart` (`urn:adaptivx:concept:carbonfootprint:1.0`) — estimated CO2 footprint.
- `MaxSpindleSpeed_rpm` (`urn:adaptivx:concept:maxspindlespeed:1.0`).
- `MaxFeedRate_mmPerMin` (`urn:adaptivx:concept:maxfeedrate:1.0`).

## Evidence links

Path: `Capabilities/ProcessCapability:Milling/Evidence`

Reference elements linking capability state to supporting evidence:
- `HealthIndexLink` → `Health` submodel `HealthIndex`
- `SimulationModelLink` → `SimulationModels` submodel `SimulationModel:*`

## Example (idShort path)

```
Capabilities/ProcessCapability:Milling/AssuranceState
```

The dispatcher relies on these idShort paths. Any changes to naming must be reflected in `libs/aas_contract`.
