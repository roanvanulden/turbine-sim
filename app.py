Bouw een Streamlit Community Cloud app voor een real-time offshore windturbine simulator.
Lever output als 2 bestanden: (1) app.py en (2) requirements.txt.
De app moet direct deploybaar zijn op Streamlit Community Cloud.

Repo/Deploy eisen:
- app.py en requirements.txt staan in de root van de repo.
- requirements.txt bevat minimaal: streamlit, numpy, matplotlib
- Geen Docker, geen extra scripts nodig.
- Geen config.toml nodig; gebruik standaard Streamlit instellingen (geen CORS/XSRF tweaks).

Functionele eisen (11.DD.200 simulator):
- Turbine: direct drive, rated power 11 MW (toon elektrisch vermogen in kW).
- Rotor diameter: 200 m (R=100 m).
- Hub height: 125 m (alleen informatief).
- Real-time dynamiek met discrete tijdstappen dt en Streamlit session_state.

UI (sidebar):
1) Windsnelheid V (m/s) slider: 0–30, stap 0.1
2) Windrichting (°) slider: 0–359, stap 1
3) Pitch β (°) slider: -2 tot 25, stap 0.1 (handmatig instelbaar)
4) Generator efficiency η (%) slider: 85–99, stap 0.1
5) dt (s) slider: 0.05–1.0
6) Yaw rate limit (°/s) slider: 0.1–2.0
7) Run/Pause toggle + Reset button

Simulatie (per rerun 1 timestep als Run aan staat):
State in st.session_state:
- omega (rad/s)
- yaw_abs (deg) absolute nacelle yaw (mag doorlopen >360)
- cable_pos (deg) accumuleert yaw changes (kabeltwist)
- unwinding (bool)

Fysica:
- Aerodynamisch vermogen: P_aero = 0.5*rho*A*Cp(lambda,beta)*V_eff^3
  - A=pi*R^2, R=100
  - rho = 1.225 (mag ook slider)
- Tip speed: v_tip = omega*R
- TSR: lambda = v_tip / max(V_eff, 0.1)
- Cp(lambda,beta): gebruik standaard empirisch Cp-model (lambda_i formule), clamp 0..0.50
- Rotor dynamiek direct drive: J*domega/dt = T_aero - T_gen - B*omega
  - Kies stabiele T_gen aanpak zodat omega niet divergeert
  - Begrens elektrisch vermogen op 11 MW
  - J en B mogen sliders of vaste defaults zijn, maar simulatie moet stabiel blijven

Yaw + windrichting:
- Nacelle yaw beweegt richting windrichting met yaw_rate limit en een kleine deadband
- Misalignment = wrap(wind_dir - nacelle_dir)
- V_eff = V * cos(misalign)^(1.5), en 0 bij |misalign|>90°

Cable twist management:
- Max 2.5 turns = 900°: als |cable_pos| > 900°, unwinding=True
- Bij unwinding: yaw automatisch terug naar cable_pos=0 (sneller dan normaal, bv 2x yaw_rate)
- Als |cable_pos| < 1°: unwinding=False

Visualisatie (matplotlib):
- 2D scene: zee + toren + nacelle + rotor met 3 bladen
- Rotor animatie: blades roteren met snelheid gebaseerd op rpm/omega (sneller bij meer wind)
- Windpijl + label: “Wind: X.X m/s @ Y°”
- Golven (sinus) worden visueel hoger bij hogere wind (geen invloed op fysica)
- Toon ook: nacelle yaw, misalignment, cable_pos in turns

Live metrics (st.metric):
- Elektrisch vermogen (kW)
- Rotor speed (rpm)
- Tip speed (m/s)
- TSR (lambda)
- Cp
- Effectieve wind (m/s)
- Status: normaal / unwinding / cable limit overschreden

Technische eisen:
- Geen infinite while-loops.
- Als Run actief: voer 1 timestep uit en gebruik een korte time.sleep (bv 0.02–0.05s) zodat animatie “leeft”.
- Alles in één app.py (geen extra modules nodig).
- Voeg onderaan app.py een comment met “requirements.txt inhoud”.

Lever als output:
1) app.py (complete, runnable)
2) requirements.txt
