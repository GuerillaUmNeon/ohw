from pathlib import Path
import re
import shutil
from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Billboard One-Hit Wonders", page_icon="🎵", layout="wide")

DATA_DIR = Path("data")
DATA_PATH = DATA_DIR / "hot100.csv"

ONE_ARTIST_WITH_THE = {"Tyler, The Creator"}


def extract_featuring(artist_str: object) -> tuple[str, str]:
    s = "" if pd.isna(artist_str) else str(artist_str).strip().strip('"')
    featuring = []

    def capture_parenthetical(match: re.Match) -> str:
        featuring.append(match.group(1).strip())
        return ""

    s = re.sub(
        r"\s*[\(\[]\s*(.*?(?:feat\.?|featuring|ft\.?|with|w/|duet|co-starring).*?)\s*[\)\]]?",
        capture_parenthetical,
        s,
        flags=re.IGNORECASE,
    ).strip()

    inline = re.search(
        r"\s+(?:feat\.?|featuring|ft\.?|with|w/|duet|co-starring)\s+(.+)$",
        s,
        flags=re.IGNORECASE,
    )
    if inline:
        featuring.append(inline.group(1).strip())
        s = s[: inline.start()].strip()

    featuring_text = ", ".join(dict.fromkeys(x for x in featuring if x))
    return s, (f"feat. {featuring_text}" if featuring_text else "")


def split_artists(artist_str: object) -> list[str]:
    s = "" if pd.isna(artist_str) else str(artist_str).strip().strip('"')
    if not s:
        return []
    if s in ONE_ARTIST_WITH_THE:
        return [s]

    s = re.sub(
        r"\s*[\(\[].*?(?:feat\.?|featuring|ft\.?|with|w/|duet|co-starring).*?[\)\]]?",
        "",
        s,
        flags=re.IGNORECASE,
    ).strip()
    s = re.sub(
        r"\s+(?:feat\.?|featuring|ft\.?|with|w/|duet|co-starring)\s+.*$",
        "",
        s,
        flags=re.IGNORECASE,
    ).strip()

    if " " not in s and re.match(r"^[A-Za-z0-9|_\-./&]+$", s):
        return [s]

    s = re.sub(r"\s*&\s*", ", ", s)
    s = re.sub(r"\s+[xX×±]\s+", ", ", s)
    s = re.sub(r"\s*\+\s*", ", ", s)
    s = re.sub(r"\s*/\s*", ", ", s)

    parts = [part.strip(" &,\t\n") for part in s.split(",") if part.strip(" &,\t\n")]
    return parts if parts else [s]


def prepare_data(path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Rank"] = pd.to_numeric(df["Rank"], errors="coerce")
    df = df.dropna(subset=["Date", "Song", "Artist", "Rank"])
    df = df[df["Rank"] <= 40].copy()
    df["Year"] = df["Date"].dt.year
    df["Decade"] = (df["Year"] // 10) * 10

    extracted = df["Artist"].apply(extract_featuring)
    df["BaseArtist"] = extracted.map(lambda value: value[0])
    df["Featuring"] = extracted.map(lambda value: value[1])
    has_feat = df["Featuring"].ne("")
    df.loc[has_feat, "Song"] = (
        df.loc[has_feat, "Song"].astype(str) + " (" + df.loc[has_feat, "Featuring"] + ")"
    )

    df["ArtistList"] = df["BaseArtist"].apply(split_artists)
    exploded = df.explode("ArtistList", ignore_index=True).rename(columns={"ArtistList": "ArtistIndividual"})
    exploded["ArtistIndividual"] = exploded["ArtistIndividual"].astype("string").str.strip()
    exploded = exploded.dropna(subset=["ArtistIndividual"])
    exploded = exploded[exploded["ArtistIndividual"].ne("")].copy()

    artist_stats = (
        exploded.sort_values("Date")
        .groupby("ArtistIndividual", as_index=False)
        .agg(
            total_weeks_top40=("Song", "size"),
            best_rank=("Rank", "min"),
            song=("Song", "last"),
            last_date=("Date", "max"),
            year=("Year", "last"),
            decade=("Decade", "last"),
        )
    )
    song_counts = exploded.groupby("ArtistIndividual")["Song"].nunique()
    artist_stats["OneHitWonder"] = artist_stats["ArtistIndividual"].map(song_counts.eq(1))
    ohw_artists = set(artist_stats.loc[artist_stats["OneHitWonder"], "ArtistIndividual"])
    exploded["OneHitWonder"] = exploded["ArtistIndividual"].isin(ohw_artists)

    yearly = (
        exploded[exploded["OneHitWonder"]]
        .groupby("Year", as_index=False)["ArtistIndividual"]
        .nunique()
        .rename(columns={"ArtistIndividual": "one_hit_wonder_artists"})
    )
    yearly_all = exploded.groupby("Year", as_index=False)["ArtistIndividual"].nunique().rename(columns={"ArtistIndividual": "total_artists"})
    yearly = yearly_all.merge(yearly, on="Year", how="left").fillna(0)

    decade = (
        exploded[exploded["Decade"] > 1950]
        .groupby("Decade", as_index=False)["ArtistIndividual"]
        .nunique()
        .rename(columns={"ArtistIndividual": "total_artists"})
    )
    decade_ohw = (
        exploded[(exploded["Decade"] > 1950) & exploded["OneHitWonder"]]
        .groupby("Decade", as_index=False)["ArtistIndividual"]
        .nunique()
        .rename(columns={"ArtistIndividual": "one_hit_wonder_artists"})
    )
    decade = decade.merge(decade_ohw, on="Decade", how="left").fillna(0)

    return exploded, artist_stats, yearly, decade


@st.cache_data
def load_data(path_string: str):
    return prepare_data(Path(path_string))


def fmt_date(dt: pd.Timestamp) -> str:
    return dt.strftime("%-d %B %Y")


st.title("Billboard One-Hit Wonders")
st.caption("Billboard Top 40 analysis; the 1950s are excluded from decade charts.")

if not DATA_PATH.exists():
    st.error(
        f"Data file not found: {DATA_PATH}.\n\n"
        "Update the dataset by running:\n\n"
        "```bash\n"
        "python update_data.py\n"
        "```"
    )
    st.stop()

try:
    hot100, artist_stats, yearly, decade = load_data(str(DATA_PATH))
except Exception as exc:
    st.exception(exc)
    st.stop()

ohw_stats = artist_stats[artist_stats["OneHitWonder"]].copy()
ohw_stats = ohw_stats.sort_values(["total_weeks_top40", "best_rank"], ascending=[False, True])

c1, c2, c3 = st.columns(3)
c1.metric("Artists", f"{artist_stats['ArtistIndividual'].nunique():,}")
c2.metric("One-hit wonders", f"{ohw_stats['ArtistIndividual'].nunique():,}")
c3.metric("Top 40 rows", f"{len(hot100):,}")

st.subheader("Longest-running one-hit wonders")
st.dataframe(
    ohw_stats[["ArtistIndividual", "song", "best_rank", "total_weeks_top40", "last_date"]]
    .rename(columns={
        "ArtistIndividual": "Artist",
        "song": "Song",
        "best_rank": "Best rank",
        "total_weeks_top40": "Top 40 weeks",
        "last_date": "Last chart date",
    })
    .assign(**{"Last chart date": lambda df: df["Last chart date"].map(fmt_date)})
    .head(200),
    use_container_width=True,
    hide_index=True,
)

st.subheader("One-hit wonders by year")
year_chart = yearly.copy()
year_chart["Year"] = year_chart["Year"].astype(str)
st.altair_chart(
    alt.Chart(year_chart).mark_line(point=True).encode(
        x=alt.X("Year:N", sort=None),
        y=alt.Y("one_hit_wonder_artists:Q", title="One-hit-wonder artists"),
        tooltip=["Year:N", "one_hit_wonder_artists:Q", "total_artists:Q"],
    ).properties(height=380),
    use_container_width=True,
)

st.subheader("One-hit wonders by decade")
decade_chart = decade.copy()
decade_chart["Decade"] = decade_chart["Decade"].astype(str) + "s"
st.altair_chart(
    alt.Chart(decade_chart).mark_bar().encode(
        x=alt.X("Decade:N", sort=None),
        y=alt.Y("one_hit_wonder_artists:Q", title="One-hit-wonder artists"),
        tooltip=[
            "Decade:N",
            alt.Tooltip("one_hit_wonder_artists:Q", title="One-hit-wonder artists"),
            alt.Tooltip("total_artists:Q", title="All artists"),
        ],
    ).properties(height=380),
    use_container_width=True,
)

st.subheader("Longest-running one-hit wonders per period")
period_mode = st.radio(
    "Group by",
    ["Year", "Decade"],
    horizontal=True,
    index=0,
)

if period_mode == "Year":
    grouped = (
        ohw_stats.sort_values(["year", "total_weeks_top40", "best_rank"], ascending=[True, False, True])
        .groupby("year", as_index=False)
        .first()
        .rename(columns={"year": "Year"})
    )
    grouped["Year"] = grouped["Year"].astype(str)
    st.dataframe(
        grouped[["Year", "ArtistIndividual", "song", "best_rank", "total_weeks_top40", "last_date"]]
        .rename(columns={
            "Year": "Year",
            "ArtistIndividual": "Artist",
            "song": "Song",
            "best_rank": "Best rank",
            "total_weeks_top40": "Top 40 weeks",
            "last_date": "Last chart date",
        })
        .assign(**{"Last chart date": lambda df: df["Last chart date"].map(fmt_date)})
        .sort_values("Year", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
else:
    ohw_decade = ohw_stats[ohw_stats["decade"] > 1950].copy()
    grouped = (
        ohw_decade.sort_values(["decade", "total_weeks_top40", "best_rank"], ascending=[True, False, True])
        .groupby("decade", as_index=False)
        .first()
        .rename(columns={"decade": "Decade"})
    )
    grouped["Decade"] = grouped["Decade"].astype(str) + "s"
    st.dataframe(
        grouped[["Decade", "ArtistIndividual", "song", "best_rank", "total_weeks_top40", "last_date"]]
        .rename(columns={
            "Decade": "Decade",
            "ArtistIndividual": "Artist",
            "song": "Song",
            "best_rank": "Best rank",
            "total_weeks_top40": "Top 40 weeks",
            "last_date": "Last chart date",
        })
        .assign(**{"Last chart date": lambda df: df["Last chart date"].map(fmt_date)})
        .sort_values("Decade", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

st.markdown("---")
st.caption(
    f"Dataset by ludmin available at [https://www.kaggle.com/datasets/ludmin/billboard](https://www.kaggle.com/datasets/ludmin/billboard). "
    f"Last version date: {datetime.fromtimestamp(DATA_PATH.stat().st_mtime).strftime('%-d %B %Y')}."
)