# Architecture

This document describes the technical architecture of Adaptiv-X.

## System Overview

Adaptiv-X implements a closed semantic control loop for Industrial Digital Twins:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ADAPTIV-X RUNTIME                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Vibration     ┌──────────────┐    Health     ┌──────────────┐             │
│   Data ────────▶│   adaptiv-   │──────────────▶│    skill-    │             │
│                 │   monitor    │    Events     │    broker    │             │
│                 │              │               │              │             │
│                 │  ┌────────┐  │               │  ┌────────┐  │             │
│                 │  │ML Model│  │               │  │ Policy │  │             │
│                 │  └────────┘  │               │  │ Engine │  │             │
│                 │  ┌────────┐  │               │  └────────┘  │             │
│                 │  │FMU Sim │  │               │              │             │
│                 │  └────────┘  │               │              │             │
│                 └──────┬───────┘               └──────┬───────┘             │
│                        │                              │                      │
│                        │ Update Health                │ Patch Capability     │
│                        ▼                              ▼                      │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                    BaSyx AAS Environment v2                          │   │
│   │                                                                      │   │
│   │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │   │
│   │  │     Health      │  │   Capability    │  │  SimulationModels   │  │   │
│   │  │    Submodel     │  │    Submodel     │  │   (IDTA 02005)      │  │   │
│   │  │                 │  │                 │  │                     │  │   │
│   │  │ HealthIndex:100 │  │ Grade: A        │  │ FMU: bearing_wear   │  │   │
│   │  │ AnomalyScore:0  │  │ State: assured  │  │                     │  │   │
│   │  └─────────────────┘  └─────────────────┘  └─────────────────────┘  │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                        ▲                              │                      │
│                        │ Query                        │ Query Capabilities   │
│                        │ Capabilities                 ▼                      │
│                 ┌──────────────────────────────────────────────────┐        │
│                 │              job-dispatcher                       │        │
│                 │                                                   │        │
│                 │  • Capability-based routing                       │        │
│                 │  • VDI/VDE 2193 bidding (optional)               │        │
│                 │  • Contract award                                 │        │
│                 └──────────────────────────────────────────────────┘        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components

### adaptiv-monitor

**Purpose**: Hybrid AI health monitoring (ML + Physics)

**Input**: 
- Vibration time series (vib_rms)
- Operating conditions (omega, load)
- Estimated wear level

**Processing**:
1. ML anomaly detection → anomaly_score [0-1]
2. FMU simulation → expected_vib
3. Physics residual = |actual - expected| / expected
4. Health fusion: confidence = 1 - (0.6 * anomaly + 0.4 * residual)

**FMU responsibility**:
- BaSyx stores the SimulationModels submodel and FMU reference.
- `adaptiv-monitor` downloads the FMU and runs it locally with FMPy.

**Output**:
- HealthIndex (0-100)
- HealthConfidence (0-1)
- ExplainabilityBundle

### skill-broker

**Purpose**: Semantic capability reasoning

**Input**: Health events from adaptiv-monitor

**Processing**:
1. Evaluate policy rules against health value
2. Map health thresholds to capability states
3. Apply semantic changes via AAS API

**Policy Rules**:
- health >= 90: `assured`, Grade A
- health >= 80: `offered`, Grade B
- health < 80: `notAvailable`, Grade C

### job-dispatcher

**Purpose**: Capability-based production routing

**Modes**:
1. **Simple**: Query → Filter → Select lowest cost
2. **VDI/VDE 2193**: Request → Bid → Award

**Selection Criteria**:
- AssuranceState == "assured"
- SurfaceFinishGrade meets requirement
- Lowest EnergyCostPerPart

## Data Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                         EVENT FLOW                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Sensor ─────▶ adaptiv-monitor ─────▶ MQTT ─────▶ skill-broker   │
│                     │                               │             │
│                     │ PATCH Health                  │ PATCH       │
│                     ▼                               ▼ Capability  │
│              ┌─────────────────────────────────────────────┐      │
│              │              AAS Repository                  │      │
│              └─────────────────────────────────────────────┘      │
│                     ▲                                             │
│                     │ GET Capabilities                            │
│                     │                                             │
│              job-dispatcher ◀────── Job Request                   │
│                     │                                             │
│                     ▼                                             │
│              Assignment Event                                     │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

## Submodel Structure

### Health Submodel
```
Health
├── HealthIndex: int (0-100)
├── HealthConfidence: float (0-1)
├── AnomalyScore: float (0-1)
├── PhysicsResidual: float (0-1)
├── LastUpdate: dateTime
└── ExplainabilityBundle
    ├── DecisionRationale: string
    ├── ModelVersion: string
    └── FMUVersion: string
```

### Capability Submodel
```
Capabilities
└── ProcessCapability:Milling
    ├── SurfaceFinishGrade: A | B | C
    ├── ToleranceClass: ±0.02mm | ±0.05mm
    ├── AssuranceState: assured | offered | notAvailable
    ├── EnergyCostPerPart_kWh: float
    └── Evidence
        ├── HealthIndexLink -> Health/HealthIndex
        └── SimulationModelLink -> SimulationModels/...
```

## Technology Stack

| Layer | Technology |
|-------|------------|
| AAS Repository | Eclipse BaSyx v2 |
| AAS Discovery | BaSyx Registry (AAS + Submodel) |
| Physics Models | FMI 2.0 / FMPy |
| ML Framework | PyTorch |
| API Framework | FastAPI |
| Message Broker | Mosquitto (MQTT) |
| Object Storage | MinIO |
| Container Runtime | Docker / Kubernetes |
| Identity | Keycloak (OIDC) |
