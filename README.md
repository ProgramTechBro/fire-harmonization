# Emberlog

**Twenty-six years of fire, counted the same way.**

Emberlog turns 26 years of NASA satellite fire data into one consistent record for Pakistan and India, forecasts next week's burning, and shows where the smoke is heading.

Built for the **2026 NASA Space Apps Challenge**: *Harmonization of MODIS and VIIRS Hot Spots*.

| | |
|---|---|
| **Live app** |  https://fire-harmonization-production.up.railway.app/#home |
| **Demo video (30 s)** | https://drive.google.com/file/d/1xfilRgd6_1-Vky6csCH6CqBkhwvaXAOG/view?usp=share_link |
| **Slides** | https://docs.google.com/presentation/d/1xf488d8STlGTT_p6cn4OW_a5BNr2dHvA/edit?usp=share_link&ouid=112191552424606846556&rtpof=true&sd=true |

---

## The problem

NASA has tracked fires from space since 2000 with two generations of sensors:

- **MODIS** (Terra and Aqua, 2000 onward): about 86,500 fires a year over Pakistan and India
- **VIIRS S-NPP** (2012 onward): about 472,900 fires a year over the same places

VIIRS sees small fires that MODIS misses, so it counts about **5.5 times more**. Put the two records side by side and burning appears to explode in 2012, purely because the sensor changed. That makes it impossible to say fairly whether burning in 2025 is worse than in 2005.

This matters most in **Punjab**, where rice-straw burning every October and November drives the winter smog that closes schools in Lahore and Delhi.

## What Emberlog does

- **One harmonized record (2000–2025).** A machine-learning model rewrites the MODIS years in VIIRS terms, so the whole record uses one consistent unit.
- **Burning calendar.** For any area: a week-by-year heatmap, the main burning seasons, unusually heavy or quiet weeks, and the long-term trend.
- **Next-week forecast.** The chance of fire and expected number of fires for each of 5,381 boxes (about 25 km each).
- **Plain-English explanations.** Every forecast says why, for example: *"Very high risk mainly because over the past 5 years it averaged 380 fires in this week, it had about 101 fires around this week last year and it already has 61 fires this week."*
- **Smoke warning.** Meteomatics wind data shows whether smoke from predicted fires is likely to drift toward cities such as Lahore or Delhi.

## Results

All results are on **2024–2025**, data the models never saw during training (train 2012–2021, tune 2022–2023, test 2024–2025).

**Harmonization (MODIS → VIIRS), compared with multiplying MODIS by a fixed ratio**

| Measure | Fixed ratio | Emberlog |
|---|---|---|
| Error per box (MAE) | 1.48 | **1.16** (22% lower) |
| Box-level accuracy (R²) | 0.51 | **0.68** |
| Weekly total accuracy (R²) | 0.91 | **0.93** |
| Punjab weekly accuracy (R²) | 0.59 | **0.66** |

**Next-week fire forecast**

| Method | ROC-AUC | Fires caught (recall) | F1 |
|---|---|---|---|
| Repeat this week | 0.78 | 64% | 0.64 |
| Five-year average for the week | 0.86 | 63% | 0.65 |
| **Emberlog** | **0.91** | **77%** | **0.71** |

## How it works

1. **Collect.** NASA FIRMS active-fire detections for Pakistan and India: MODIS Collection 6.1 (2000–2025) and VIIRS S-NPP 375 m (2012–2025), about 8.5 million points. Only vegetation fires are kept, and low-confidence detections are removed.
2. **Grid.** Both countries are split into 0.25° boxes (about 25 km). Fires are counted per box per week: 5,381 fire-prone boxes × 1,314 weeks.
3. **Harmonize.** A LightGBM model learns, from 2012–2025 when both satellites were flying, how many fires VIIRS would have seen given MODIS counts, fire power, brightness and the box's seasonal pattern. A second model covers November 2000 to June 2002, when only Terra was flying. Together they fill 2000–2011 in VIIRS terms.
4. **Forecast.** A second pair of LightGBM models predicts next week's chance of fire and number of fires per box. They use only the past: recent weeks, the eight neighbouring boxes, the same week last year, the five-year average for that week, and the time of year.
5. **Explain.** SHAP values show how much each factor pushed a box's risk up or down, and the app turns the strongest ones into a sentence.
6. **Serve.** Forecasts and calendars are precomputed into a compact, memory-mapped bundle, so the whole app runs on a small free server.

## Tech stack

- **Data and ML:** Python, pandas, NumPy, LightGBM, SHAP, scikit-learn, Matplotlib
- **Backend:** FastAPI, Uvicorn
- **Frontend:** React, Vite, Leaflet, Recharts, Lucide icons, Inter typeface
- **Maps:** NASA Black Marble via GIBS, Esri World Dark Gray, OpenStreetMap
- **Weather:** Meteomatics Weather API
- **Deployment:** Docker, Railway (auto-deploys every push to `main`)

## Project structure

```
step1_prepare.py      clean and merge MODIS and VIIRS CSVs
step2_explore.py      yearly, monthly and Punjab charts
step3_grid.py         0.25° grid, weekly counts per box
step4_harmonize.py    harmonization models (MODIS -> VIIRS)
step5_forecast.py     next-week forecast models
step6_explain.py      SHAP explanations
step7_export.py       export data and models for the web app
features.py           shared feature code
web_data/             exported data and models
backend/              FastAPI app and precomputed bundle
frontend/             React app
Dockerfile            builds the website and API into one container
render.yaml           optional Render configuration
```

## Run it locally

Backend:

```
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.precompute
uvicorn app.main:app --reload --port 8000
```

On Windows, use `venv\Scripts\activate` and `copy .env.example .env`. On macOS, LightGBM also needs `brew install libomp`. Add Meteomatics credentials to `backend/.env` to enable weather; the app works without them.

Frontend, in a second terminal:

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

To rebuild the models from raw data, download the FIRMS country yearly files into `data/modis/` and `data/viirs/`, then run `step1_prepare.py` to `step7_export.py` in order, followed by `python -m app.precompute` in `backend`.

## Limitations

- The forecast learns from history, so sudden changes in behaviour can fool it. In autumn 2024, burning in Punjab fell far below past years and the model over-predicted the peak.
- Estimates before mid-2002 rest on one satellite (Terra) and are less certain than later years.
- Satellites only see fires burning when they pass overhead; fires lit after a pass can be missed.
- The smoke warning is an indicator of where smoke is heading, not an air-quality measurement.

## Data and credits

- NASA FIRMS active fire data: https://firms.modaps.eosdis.nasa.gov/
- NASA MODIS: https://modis.gsfc.nasa.gov/
- NASA Black Marble: https://blackmarble.gsfc.nasa.gov/
- NASA GIBS: https://nasa-gibs.github.io/gibs-api-docs/
- Meteomatics Weather API: https://www.meteomatics.com/
- Base map © Esri, HERE, Garmin; map data © OpenStreetMap contributors

## Team

Muhammad Hassan · Waqar Ahmed · Zohaib Ahmed ·  Sakhi Ghulam

## Use of Super Intelligence (SI)

We used Claude (Anthropic) as an AI coding and writing assistant. It generated much of the code for our data pipeline, models, backend and frontend, and helped draft the slides and project text.

The project itself was driven by our team. We:

- chose the MODIS/VIIRS harmonization challenge and framed it around Punjab crop burning and the Lahore smog crisis
- downloaded and prepared 26 years of NASA FIRMS data for Pakistan and India
- ran every training and evaluation step on our own machines, checked results against baselines, and decided which models to keep (for example, we tested season-trend features, found they made the Punjab forecast worse, and reverted them)
- reviewed the outputs, identified the model's limits (such as the 2024 over-prediction) and chose to report them openly
- set up the project on GitHub, tested the app locally, and deployed it on Railway

All data is real NASA FIRMS (MODIS, VIIRS) and Meteomatics data. No images, audio or video in this project are SI-generated; charts are drawn from our own model results and screenshots are of our live app.
