# Billboard One-Hit Wonders

Interactive Streamlit app that analyzes Billboard Hot 100 data to identify and explore one‑hit wonders.

- Defines a one‑hit wonder as an artist with exactly one distinct song in the Top 40.
- Splits collaboration credits (e.g. `&`, `X`, `+`, `/`, commas) into individual artists.
- Moves featuring/duet/with credits from the artist field into the song title.
- Aggregates stats per artist, year, and decade.
- Visualizes:
  - Longest‑running one‑hit wonders.
  - Number of one‑hit wonders per year.
  - Number of one‑hit wonders per decade (1960s onward).
  - Longest‑running one‑hit wonder per year or per decade.

Dataset: [ludmin/billboard on Kaggle](https://www.kaggle.com/datasets/ludmin/billboard).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Update the dataset

From the project root:

```bash
python update_data.py
```

This downloads the latest `ludmin/billboard` dataset into `data/` and keeps only `data/hot100.csv`.

## Run the app

```bash
streamlit run app.py
```

Then open the URL shown in your terminal (usually http://localhost:8501).

## Project structure

- `app.py` – Streamlit application.
- `update_data.py` – Script to download/update the dataset.
- `requirements.txt` – Python dependencies.
- `data/hot100.csv` – Billboard Hot 100 data (created by `update_data.py`).

## Notes

- The 1950s are excluded from decade charts.
- Stylized artist names like `M|A|R|R|S` are kept as a single artist.
- “Last version date” in the footer reflects the last time you ran `update_data.py` (based on `data/hot100.csv` modification time).