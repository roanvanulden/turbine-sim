import time
import math
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

# ----------------------------
# Helpers
# ----------------------------
def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def wrap_deg_0_360(deg: float) -> float:
    return deg % 360.0

def wrap_deg_signed(deg: float) -> float:
    """Wrap to [-180, 180)."""
    d = (deg + 180.0) % 360.0 - 180.0
    return d

def cp_model(tsr: float, pitch_deg: float) -> float:
    """
    Simple empirical Cp model (not manufacturer-grade).
    Based on a common approximation used in wind turbine demos.
    """
    beta = pitch_deg
    lam = max(tsr, 0.01)
    # Lambda_i formulation
    inv_lami = 1.0/(lam + 0.08*beta) - 0.035/(beta**3 + 1.0)
    lami = 1.0/max(inv_lami, 1e-6)
    cp = 0.22*(116.0/lami - 0.4*beta - 5.0) * math.exp(-12.5/lami)
    return clamp(cp, 0.0, 0.50)

# ----------------------------
# Streamlit setup
# ----------------------------
st.set_page_config(page_title="Turbine Sim v2", layout="wide")
st.title("Offshore Windturbine Simulator (11.DD.200) – v2")

# Sidebar
st.sidebar.header("Controls")

wind_ms = st.sidebar.slider("Windsnelheid (m/s)", 0.0, 30.0, 10.0, 0.1)
wind_dir = st.sidebar.slider("Windrichting (°)", 0, 359, 270, 1)
pitch_deg = st.sidebar.slider("Pitch (°)", -2.0, 25.0, 2.0, 0.1)
gen_eff = st.sidebar.slider("Generator efficiency (%)", 85.0, 99.0, 96.0, 0.1)

st.sidebar.divider()
dt = st.sidebar.slider("Timestep dt (s)", 0.05, 1.0, 0.15, 0.05)
yaw_rate_lim = st.sidebar.slider("Yaw rate limit (°/s)", 0.1, 2.0, 0.7, 0.1)
yaw_deadband = st.sidebar.slider("Yaw deadband (°)", 0.0, 10.0, 2.0, 0.5)

st.sidebar.divider()
rho = st.sidebar.slider("Luchtdichtheid ρ (kg/m³)", 1.00, 1.30, 1.225, 0.005)

# Rotor dynamics tuning (keep stable defaults)
J = st.sidebar.slider("Rotor inertie J (kg·m²) (demo)", 2.0e7, 2.0e8, 7.0e7, 1.0e7)
B = st.sidebar.slider("Demping B (N·m·s)", 1.0e5, 2.0e6, 7.0e5, 1.0e5)

# Turbine constants
R = 100.0               # m (diameter 200 m)
A = math.pi * R**2      # swept area
rated_kw = 11000.0      # 11 MW
tsr_opt = 8.0           # demo-optimum TSR
rpm_max = 12.0          # demo cap (DD-ish)
omega_max = rpm_max * 2.0 * math.pi / 60.0

# ----------------------------
# Session state init
# ----------------------------
if "running" not in st.session_state:
    st.session_state.running = False

if "omega" not in st.session_state:
    st.session_state.omega = 0.6  # rad/s (small nonzero)

if "yaw_abs" not in st.session_state:
    st.session_state.yaw_abs = float(wind_dir)  # start aligned

if "cable_pos" not in st.session_state:
    st.session_state.cable_pos = 0.0  # degrees

if "unwinding" not in st.session_state:
    st.session_state.unwinding = False

if "rotor_angle" not in st.session_state:
    st.session_state.rotor_angle = 0.0  # radians

# Controls row
c_run, c_reset, c_info = st.columns([1, 1, 3])

with c_run:
    st.session_state.running = st.toggle("Run", value=st.session_state.running)

with c_reset:
    if st.button("Reset"):
        st.session_state.running = False
        st.session_state.omega = 0.6
        st.session_state.yaw_abs = float(wind_dir)
        st.session_state.cable_pos = 0.0
        st.session_state.unwinding = False
        st.session_state.rotor_angle = 0.0
        st.rerun()

with c_info:
    st.caption(
        "v2: yaw + cable twist + rotor dynamiek + Cp/TSR + betere visual. "
        "Model is didactisch (geen echte Siemens controller)."
    )

# ----------------------------
# One simulation step
# ----------------------------
def step_sim():
    omega = float(st.session_state.omega)
    yaw_abs = float(st.session_state.yaw_abs)
    cable_pos = float(st.session_state.cable_pos)
    unwinding = bool(st.session_state.unwinding)

    nacelle_dir = wrap_deg_0_360(yaw_abs)
    misalign = wrap_deg_signed(float(wind_dir) - nacelle_dir)

    # Cable twist logic
    cable_limit = 900.0  # degrees (2.5 turns)
    if abs(cable_pos) > cable_limit:
        unwinding = True

    # Yaw step
    if unwinding:
        # Drive cable_pos back to 0 by yawing opposite the current cable_pos sign
        desired_delta = -cable_pos  # want cable_pos -> 0
        # Convert to signed yaw command direction
        cmd_sign = 0.0
        if abs(desired_delta) > 1.0:
            cmd_sign = 1.0 if desired_delta > 0 else -1.0

        yaw_rate = min(2.0 * yaw_rate_lim, 3.0)  # faster unwind, but cap
        delta_yaw = cmd_sign * yaw_rate * dt

        # If close enough, stop unwinding
        if abs(cable_pos) < 1.0:
            unwinding = False
            delta_yaw = 0.0
    else:
        # Normal yaw toward wind direction with deadband + rate limit
        if abs(misalign) <= yaw_deadband:
            delta_yaw = 0.0
        else:
            delta_yaw = clamp(misalign, -yaw_rate_lim*dt, yaw_rate_lim*dt)

    # Apply yaw change
    yaw_abs += delta_yaw
    cable_pos += delta_yaw

    # Update nacelle & misalignment after yaw
    nacelle_dir = wrap_deg_0_360(yaw_abs)
    misalign = wrap_deg_signed(float(wind_dir) - nacelle_dir)

    # Effective wind due to misalignment loss
    if abs(misalign) >= 90.0:
        v_eff = 0.0
    else:
        loss = (math.cos(math.radians(abs(misalign))) ** 1.5)
        v_eff = float(wind_ms) * loss

    # Aero power + Cp
    tip_speed = omega * R
    tsr = tip_speed / max(v_eff, 0.1)
    cp = cp_model(tsr, float(pitch_deg))

    p_aero_w = 0.5 * float(rho) * A * cp * (v_eff ** 3)
    p_aero_kw = p_aero_w / 1000.0

    # Aerodynamic torque
    omega_for_torque = max(omega, 0.2)  # avoid crazy torque at near-zero omega
    t_aero = p_aero_w / omega_for_torque

    # Generator control (stable demo):
    # Aim for omega_target based on TSR_opt and v_eff, capped by omega_max
    omega_target = clamp((tsr_opt * max(v_eff, 0.1)) / R, 0.0, omega_max)

    # Compute desired electrical power (capped) and convert to torque
    p_elec_kw_cap = min(rated_kw, p_aero_kw * (float(gen_eff) / 100.0))
    p_elec_w = p_elec_kw_cap * 1000.0

    # Torque from power + a proportional term to track omega_target
    k_p = 4.0e6  # demo gain, stable with J/B defaults
    t_from_power = p_elec_w / omega_for_torque
    t_track = k_p * (omega - omega_target)

    # Generator torque cannot be negative in this simple model (no motoring)
    t_gen = clamp(t_from_power + t_track, 0.0, 2.0e8)

    # Rotor dynamics
    omega_dot = (t_aero - t_gen - float(B) * omega) / float(J)
    omega = clamp(omega + omega_dot * dt, 0.0, omega_max)

    # Rotor angle integrate
    st.session_state.rotor_angle = (st.session_state.rotor_angle + omega * dt) % (2.0 * math.pi)

    # Save state
    st.session_state.omega = omega
    st.session_state.yaw_abs = yaw_abs
    st.session_state.cable_pos = cable_pos
    st.session_state.unwinding = unwinding

    # Outputs for UI
    rpm = omega * 60.0 / (2.0 * math.pi)
    tip_speed = omega * R
    tsr = tip_speed / max(v_eff, 0.1)

    status = "NORMAL"
    if unwinding:
        status = "UNWINDING"
    elif abs(cable_pos) > cable_limit:
        status = "CABLE LIMIT"

    return {
        "nacelle_dir": nacelle_dir,
        "misalign": misalign,
        "v_eff": v_eff,
        "cp": cp,
        "p_aero_kw": p_aero_kw,
        "p_elec_kw": p_elec_kw_cap,
        "rpm": rpm,
        "tip_speed": tip_speed,
        "tsr": tsr,
        "status": status,
        "cable_turns": cable_pos / 360.0,
    }

# Run one step if running
if st.session_state.running:
    out = step_sim()
else:
    # still compute outputs based on current state for display
    # (without stepping)
    omega = float(st.session_state.omega)
    yaw_abs = float(st.session_state.yaw_abs)
    nacelle_dir = wrap_deg_0_360(yaw_abs)
    misalign = wrap_deg_signed(float(wind_dir) - nacelle_dir)

    if abs(misalign) >= 90.0:
        v_eff = 0.0
    else:
        v_eff = float(wind_ms) * (math.cos(math.radians(abs(misalign))) ** 1.5)

    tip_speed = omega * R
    tsr = tip_speed / max(v_eff, 0.1)
    cp = cp_model(tsr, float(pitch_deg))
    p_aero_kw = 0.5 * float(rho) * A * cp * (v_eff ** 3) / 1000.0
    p_elec_kw = min(rated_kw, p_aero_kw * (float(gen_eff) / 100.0))

    cable_limit = 900.0
    status = "UNWINDING" if st.session_state.unwinding else "NORMAL"
    if abs(st.session_state.cable_pos) > cable_limit:
        status = "CABLE LIMIT"

    out = {
        "nacelle_dir": nacelle_dir,
        "misalign": misalign,
        "v_eff": v_eff,
        "cp": cp,
        "p_aero_kw": p_aero_kw,
        "p_elec_kw": p_elec_kw,
        "rpm": omega * 60.0 / (2.0 * math.pi),
        "tip_speed": tip_speed,
        "tsr": tsr,
        "status": status,
        "cable_turns": float(st.session_state.cable_pos) / 360.0,
    }

# ----------------------------
# Layout
# ----------------------------
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Live metrics")
    st.metric("Elektrisch vermogen (kW)", f"{out['p_elec_kw']:,.0f}")
    st.metric("Rotor speed (rpm)", f"{out['rpm']:.2f}")
    st.metric("Tip speed (m/s)", f"{out['tip_speed']:.1f}")
    st.metric("TSR λ", f"{out['tsr']:.2f}")
    st.metric("Cp", f"{out['cp']:.3f}")

    st.divider()
    st.write("**Yaw / kabel**")
    st.write(f"Nacelle yaw: **{out['nacelle_dir']:.1f}°**")
    st.write(f"Misalignment: **{out['misalign']:.1f}°**")
    st.write(f"Effectieve wind (yaw loss): **{out['v_eff']:.2f} m/s**")
    st.write(f"Cable twist: **{out['cable_turns']:.2f} turns** (max ±2.50)")
    st.write(f"Status: **{out['status']}**")

with col2:
    st.subheader("Visualisatie (v2)")

    fig, ax = plt.subplots(figsize=(7.6, 4.4))

    # Sea + waves (visual only)
    x = np.linspace(0, 10, 700)
    wave_amp = 0.06 + 0.012 * float(wind_ms)
    wave_freq = 1.3 + 0.03 * float(wind_ms)
    phase = time.time() * 0.9
    y = wave_amp * np.sin(2 * np.pi * (x / 10.0) * wave_freq - phase)
    ax.plot(x, y, linewidth=2)

    # Turbine geometry (normalized scene)
    base_x = 6.0
    base_y = 0.0
    tower_h = 2.3
    nac_len = 0.55
    hub_r = 0.40

    # Tower
    ax.plot([base_x, base_x], [base_y, base_y + tower_h], linewidth=10)

    # Nacelle orientation (yaw)
    yaw_rad = math.radians(out["nacelle_dir"])
    nac_x2 = base_x + nac_len * math.cos(yaw_rad)
    nac_y2 = base_y + tower_h + nac_len * math.sin(yaw_rad)

    # Nacelle line
    ax.plot([base_x, nac_x2], [base_y + tower_h, nac_y2], linewidth=10)

    # Hub position
    hub_x, hub_y = nac_x2, nac_y2

    # Rotor circle
    circle = plt.Circle((hub_x, hub_y), hub_r, fill=False, linewidth=2)
    ax.add_patch(circle)

    # Blades (3) rotating
    ang0 = float(st.session_state.rotor_angle)
    for k in range(3):
        a = ang0 + k * 2 * math.pi / 3
        ax.plot(
            [hub_x, hub_x + hub_r * math.cos(a)],
            [hub_y, hub_y + hub_r * math.sin(a)],
            linewidth=4
        )

    # Wind arrow (direction)
    wd = math.radians(float(wind_dir))
    ax.arrow(
        1.0, 2.6,
        1.2 * math.cos(wd), 1.2 * math.sin(wd),
        head_width=0.14,
        length_includes_head=True
    )
    ax.text(0.6, 3.2, f"Wind: {float(wind_ms):.1f} m/s @ {int(wind_dir)}°")

    # Show misalignment info near turbine
    ax.text(6.9, 2.9, f"Yaw: {out['nacelle_dir']:.0f}°")
    ax.text(6.9, 2.65, f"Misalign: {out['misalign']:+.0f}°")
    ax.text(6.9, 2.40, f"Cable: {out['cable_turns']:+.2f} turns")
    ax.text(6.9, 2.15, f"Status: {out['status']}")

    ax.set_xlim(0, 10)
    ax.set_ylim(-0.6, 3.6)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("Offshore scene (yaw + rotor dynamics + cable twist)")

    st.pyplot(fig)

# If running: rerun for animation feel (no infinite loop)
if st.session_state.running:
    time.sleep(0.03)
    st.rerun()

# requirements.txt:
# streamlit
# numpy
# matplotlib
