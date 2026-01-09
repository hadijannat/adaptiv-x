# FMU Export Directory

This directory contains pre-compiled FMU binaries.

## bearing_wear.fmu

The bearing wear physics model exported as FMI 2.0 Co-Simulation FMU.

### Generating the FMU

If you have OpenModelica installed:

```bash
cd ../modelica
omc ../scripts/export_fmu.mos
mv BearingWear.fmu ../export/bearing_wear.fmu
```

### FMU Contents

The FMU is a ZIP archive containing:
- `modelDescription.xml` - Interface specification
- `binaries/` - Platform-specific libraries
- `resources/` - Additional model resources

### Inputs

| Variable | Unit | Description |
|----------|------|-------------|
| `omega` | rad/s | Spindle angular velocity |
| `load` | N | Cutting load |
| `wear` | 0-1 | Normalized wear level |

### Outputs

| Variable | Unit | Description |
|----------|------|-------------|
| `vib_rms_expected` | mm/s | Expected RMS vibration |
| `power_loss_expected` | W | Expected power loss |
| `temperature_rise_expected` | K | Expected temperature rise |

### Usage with FMPy

```python
from fmpy import simulate_fmu

result = simulate_fmu(
    'bearing_wear.fmu',
    start_values={
        'omega': 100.0,  # rad/s
        'load': 500.0,   # N
        'wear': 0.3      # 30% worn
    },
    output=['vib_rms_expected', 'power_loss_expected']
)
```
