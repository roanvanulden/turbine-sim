import time
import math
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

st.set_page_config(page_title="Turbine Sim", layout="wide")

st.title("Offshore Windturbine Simulator (11.DD.200)")

# Sidebar controls (basis)
st.sidebar.header("Controls")
wind_ms = st.sidebar.slider("Windsnelheid (m/s)", 0.0, 30.0, 10.0, 0.1)
wind_dir = st.sidebar.slider("Windrichting (°)", 0, 359, 270, 1)
pitch_deg = st.sidebar.slider("Pitch (°)", -2.0, 25.0, 2.0, 0.1)
gen_eff = st.sidebar.slider("Generator efficiency (%)", 85.0, 99.0, 96.0, 0.1)

# Constants turbine
R = 100.0  # meter (diameter 200m)
A = math.pi * R**2
rho = 1.225
rated_kw = 11000.0

# Super simpele demo-berekening (placeholder)
# Later vervangen door jouw Cp/TSR/yaw/cable model
cp_demo = max(0.0, min(0.45, 0.45 - 0.01 * abs(pitch_deg)))
p_aero_kw = 0.5 * rho * A * cp_demo * (wind_ms ** 3) / 1000.0
p_elec_kw = min(rated_kw, p_aero_kw * (gen_eff / 100.0))

# Fake RPM (placeholder) zodat je al animatie ziet
rpm = min(12.0, wind_ms * 0.7)  # later vervangen door echte dynamics
omega = rpm * 2 * math.pi / 60.0
tip_speed = omega * R
tsr = tip_speed / max(wind_ms, 0.1)

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Live metrics")
    st.metric("Elektrisch vermogen (kW)", f"{p_elec_kw:,.0f}")
    st.metric("Rotor speed (rpm)", f"{rpm:.2f}")
    st.metric("Tip speed (m/s)", f"{tip_speed:.1f}")
    st.metric("TSR λ", f"{tsr:.2f}")
    st.metric("Cp (demo)", f"{cp_demo:.3f}")

with col2:
    st.subheader("Visualisatie (demo)")
    fig, ax = plt.subplots(figsize=(7, 4))

    # Zee + golven (hoogte ~ wind)
    x = np.linspace(0, 10, 400)
    wave_amp = 0.05 + 0.01 * wind_ms
    y = wave_amp * np.sin(2 * np.pi * (x - time.time() * 0.7))
    ax.plot(x, y)

    # Turbine (super basic)
    ax.plot([5, 5], [0, 1.8], linewidth=6)           # toren
    ax.plot([5, 5.4], [1.8, 1.8], linewidth=6)       # nacelle

    # Rotor (cirkel + 3 bladen)
    hub_x, hub_y = 5.4, 1.8
    circle = plt.Circle((hub_x, hub_y), 0.35, fill=False)
    ax.add_patch(circle)

    angle = time.time() * omega  # roteert sneller bij hogere omega
    for k in range(3):
        a = angle + k * 2 * math.pi / 3
        ax.plot([hub_x, hub_x + 0.35 * math.cos(a)],
                [hub_y, hub_y + 0.35 * math.sin(a)], linewidth=3)

    # Wind pijl + label
    wd = math.radians(wind_dir)
    ax.arrow(1, 1.7, 0.8 * math.cos(wd), 0.8 * math.sin(wd),
             head_width=0.12, length_includes_head=True)
    ax.text(0.8, 2.3, f"Wind: {wind_ms:.1f} m/s @ {wind_dir}°")

    ax.set_xlim(0, 10)
    ax.set_ylim(-0.5, 3)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("Demo scene (wordt uitgebreid met yaw/cable/pitch dynamics)")

    st.pyplot(fig)

st.caption("Let op: dit is een minimale werkende basis. Daarna bouwen we jouw volledige model (yaw + cable twist + Cp/TSR + dynamics).")
