# Decision Rationale Semantics

Adaptiv-X stores explainability data in the `Health` submodel to make the hybrid ML + FMU decision auditable. The values below are updated on every health assessment.

## ExplainabilityBundle

Path: `Health/ExplainabilityBundle`

Properties:
- `DecisionRationale` (`urn:adaptivx:concept:decisionrationale:1.0`) — human-readable explanation.
- `DetectedPattern` (`urn:adaptivx:concept:detectedpattern:1.0`) — categorical ML label (`normal`, `minor_anomaly`, `major_anomaly`).
- `FusionMethod` (`urn:adaptivx:concept:fusionmethod:1.0`) — fusion algorithm identifier (e.g., `weighted_v1`).
- `ConfidenceInterval` (`urn:adaptivx:concept:confidenceinterval:1.0`) — confidence margin (e.g., `±5.0%`).
- `FMUResidual` (`urn:adaptivx:concept:fmuresidual:1.0`) — residual used for physics explainability.
- `ModelVersion` (`urn:adaptivx:concept:modelversion:1.0`) — ML model version string.
- `FMUVersion` (`urn:adaptivx:concept:fmuversion:1.0`) — FMU version string.

These properties are intentionally compact and stable so downstream systems can use them for audit trails and trust checks without parsing free-form logs.
