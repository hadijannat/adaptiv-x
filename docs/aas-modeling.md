# AAS Modeling Guide

This document describes the AAS submodel designs used in Adaptiv-X.

## Overview

Adaptiv-X uses three submodel types:

| Submodel | Standard | Purpose |
|----------|----------|---------|
| Health | Custom draft | Real-time asset condition |
| Capability | Custom draft | Process capabilities with assurance |
| SimulationModels | IDTA 02005 | FMU reference |

## Health Submodel (Custom Draft)

Continuously updated by `adaptiv-monitor`.

### Elements

```yaml
Health:
  HealthIndex:
    type: Property
    valueType: xs:int
    range: 0-100
    semanticId: 0173-1#02-AAZ842#001
    description: Overall health derived from ML + physics fusion
    
  HealthConfidence:
    type: Property
    valueType: xs:double
    range: 0.0-1.0
    description: Confidence level of assessment
    
  AnomalyScore:
    type: Property
    valueType: xs:double
    range: 0.0-1.0
    description: ML-detected anomaly (0=normal, 1=anomaly)
    
  PhysicsResidual:
    type: Property
    valueType: xs:double
    range: 0.0-1.0
    description: Deviation from physics model
    
  LastUpdate:
    type: Property
    valueType: xs:dateTime
    
  ExplainabilityBundle:
    type: SubmodelElementCollection
    elements:
      - DecisionRationale: string
      - ModelVersion: string
      - FMUVersion: string
```

## Capability Submodel (Custom Draft)

Aligned with German capability-based engineering discourse.

### Assurance States

Following the German capability literature:

| State | Meaning |
|-------|---------|
| `assured` | Capability guaranteed at specified quality |
| `offered` | Capability available but not guaranteed |
| `notAvailable` | Capability degraded or unavailable |

### Elements

```yaml
Capabilities:
  ProcessCapability:Milling:
    type: SubmodelElementCollection
    semanticId: 0173-1#01-AKJ975#017
    elements:
      SurfaceFinishGrade:
        type: Property
        valueType: xs:string
        values: A | B | C
        semanticId: 0173-1#02-AAG920#004
        
      ToleranceClass:
        type: Property
        valueType: xs:string
        example: "±0.02mm"
        semanticId: 0173-1#02-AAE583#006
        
      AssuranceState:
        type: Property
        valueType: xs:string
        values: assured | offered | notAvailable
        semanticId: urn:adaptivx:concept:assurancestate:1.0
        
      EnergyCostPerPart_kWh:
        type: Property
        valueType: xs:double
        semanticId: 0173-1#02-AAT812#001
        
      Evidence:
        type: SubmodelElementCollection
        elements:
          - HealthIndexLink: ReferenceElement
          - SimulationModelLink: ReferenceElement
```

## SimulationModels Submodel (IDTA 02005)

Standard-compliant FMU reference.

### Structure

```yaml
SimulationModels:
  SimulationModel:BearingWear:
    type: SubmodelElementCollection
    semanticId: https://admin-shell.io/idta/SimulationModels/SimulationModel/1/0
    elements:
      ModelName: "BearingWear"
      ModelDescription: "Physics of bearing wear"
      
      ModelFile:
        type: SubmodelElementCollection
        elements:
          ModelFileVersion:
            elements:
              ModelVersionId: "1.0.0"
              DigitalFile:
                type: File
                contentType: application/zip
                value: http://minio:9000/adaptivx-fmu/bearing_wear.fmu
```

## Semantic References

### ECLASS IRDIs Used

| IRDI | Property |
|------|----------|
| 0173-1#02-AAZ842#001 | Health Index |
| 0173-1#02-AAG920#004 | Surface Roughness |
| 0173-1#02-AAE583#006 | Tolerance Class |
| 0173-1#02-AAT812#001 | Energy Consumption |
| 0173-1#02-AAM632#002 | DateTime |
| 0173-1#01-AKJ975#017 | Milling Process |

### Custom URNs

For concepts not in ECLASS:

- `urn:adaptivx:concept:assurancestate:1.0`
- `urn:adaptivx:concept:healthconfidence:1.0`
- `urn:adaptivx:concept:anomalyscore:1.0`
- `urn:adaptivx:concept:physicsresidual:1.0`

## Best Practices

1. **Use existing IRDI** from ECLASS when available
2. **Create ConceptDescriptions** for all custom properties
3. **Include bilingual descriptions** (en/de)
4. **Reference evidence** to enable auditability
5. **Follow IEC 61360** for data specifications
