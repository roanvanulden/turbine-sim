# Turbine Simulator (11.DD.200) – Streamlit Dashboard

## Doel
Een interactieve simulatie (dashboard) van een offshore windturbine waarbij je parameters kunt aanpassen en direct het effect ziet op o.a. vermogen (kW), rotor rpm, tip speed en gedrag (yaw + cable twist).

## Turbine basis
- Type: Direct Drive
- Rated power: 11 MW (11000 kW)
- Rotor diameter: 200 m (R = 100 m)
- Hub height: 125 m (informatief)

## Controls (UI)
- Windsnelheid (m/s)
- Windrichting (°)
- Pitch (°) handmatig instelbaar
- Generator efficiency (%)
- (later) dt, yaw-rate limit, J, B etc.

## Model (gepland)
- Aerodynamisch vermogen:
  P_aero = 0.5 * rho * A * Cp(lambda, beta) * V_eff^3
- TSR:
  lambda = (omega * R) / V_eff
- Yaw:
  nacelle draait richting windrichting met rate limit
  V_eff neemt af bij misalignment
- Cable twist:
  max 2.5 turns = 900°
  bij overschrijding: automatisch unwind terug naar 0

## Visualisatie
- 2D offshore scene met:
  - zee + golven (golven hoger bij meer wind, visueel)
  - turbine + rotor (3 bladen)
  - windpijl met m/s + richting
  - rotor animatie: sneller bij hogere rpm

## Bestanden
- `app.py` – Streamlit app (code)
- `requirements.txt` – dependencies
- `README.md` – projectbeschrijving

## Install/deploy
Streamlit Community Cloud:
- repo bevat `app.py` en `requirements.txt` in de root
- deploy `app.py` als entrypoint

## requirements.txt
```txt
streamlit
numpy
matplotlib
