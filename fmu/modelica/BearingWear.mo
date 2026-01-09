/*
 * BearingWear.mo - Modelica Model for Bearing Wear Physics
 * 
 * Purpose: Physics-based model for predicting vibration and power loss
 *          due to bearing wear in CNC milling machines.
 * 
 * Usage: Export as FMI 2.0 Co-Simulation FMU for runtime validation
 *        of ML-based anomaly detection (hybrid AI approach).
 * 
 * Part of Adaptiv-X: Capability-Based Self-Healing Digital Twin
 */

model BearingWear "Bearing wear physics for vibration prediction"
  
  // ========================================================================
  // INPUTS - Operating conditions and wear state
  // ========================================================================
  
  input Real omega(unit="rad/s", min=0) 
    "Spindle angular velocity";
  
  input Real load(unit="N", min=0) 
    "Cutting load / radial force on bearing";
  
  input Real wear(min=0, max=1) 
    "Normalized wear level (0=new, 1=end-of-life)";
  
  // ========================================================================
  // OUTPUTS - Predicted physical behavior
  // ========================================================================
  
  output Real vib_rms_expected(unit="mm/s") 
    "Expected RMS vibration velocity";
  
  output Real power_loss_expected(unit="W") 
    "Expected power loss due to friction";
  
  output Real temperature_rise_expected(unit="K")
    "Expected bearing temperature rise above ambient";
  
  // ========================================================================
  // PARAMETERS - Model coefficients (calibrated from test data)
  // ========================================================================
  
  // Vibration model: vib = base + k1*omega + k2*load + k3*wear + k4*wear*omega
  parameter Real vib_base(unit="mm/s") = 0.5 
    "Baseline vibration for new bearing at rest";
  parameter Real k1 = 0.001 
    "Speed coefficient [mm/s per rad/s]";
  parameter Real k2 = 0.002 
    "Load coefficient [mm/s per N]";
  parameter Real k3 = 3.0 
    "Wear coefficient [mm/s per unit wear]";
  parameter Real k4 = 0.005 
    "Wear-speed interaction coefficient";
  
  // Power loss model: P = base + c1*load*omega + c2*wear*load
  parameter Real power_base(unit="W") = 50 
    "Baseline friction power loss";
  parameter Real c1 = 0.0001 
    "Load-speed power coefficient";
  parameter Real c2 = 0.5 
    "Wear-load power coefficient";
  
  // Temperature model: dT = thermal_resistance * power_loss
  parameter Real thermal_resistance(unit="K/W") = 0.02 
    "Thermal resistance bearing-to-ambient";
  
equation
  
  // ========================================================================
  // VIBRATION MODEL
  // Linear model with wear-speed interaction term
  // Captures: baseline + speed effect + load effect + wear effect + coupling
  // ========================================================================
  vib_rms_expected = vib_base + k1*omega + k2*load + k3*wear + k4*wear*omega;
  
  // ========================================================================
  // POWER LOSS MODEL
  // Friction increases with load/speed and degrades with wear
  // ========================================================================
  power_loss_expected = power_base + c1*load*omega + c2*wear*load;
  
  // ========================================================================
  // TEMPERATURE MODEL
  // Simple thermal resistance model for bearing heating
  // ========================================================================
  temperature_rise_expected = thermal_resistance * power_loss_expected;

  annotation(
    Documentation(info="<html>
<h3>Bearing Wear Physics Model</h3>
<p>This model predicts expected vibration, power loss, and temperature rise
based on operating conditions (speed, load) and current wear state.</p>

<h4>Applications:</h4>
<ul>
  <li>Physics-based plausibility checking for ML anomaly detection</li>
  <li>Residual computation: actual - expected values</li>
  <li>Condition-based maintenance prediction</li>
</ul>

<h4>Usage in Adaptiv-X:</h4>
<p>The FMU is loaded by the <code>adaptiv-monitor</code> service to compute
expected vibration. The residual between measured and expected vibration
is used to validate ML anomaly scores, implementing hybrid AI.</p>
</html>"),
    experiment(
      StopTime=10,
      Interval=0.01,
      Tolerance=1e-6
    )
  );
  
end BearingWear;
