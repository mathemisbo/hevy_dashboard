"""Hevy Workout Dashboard — Streamlit app."""

import os
import warnings
from datetime import date, timedelta
from collections import defaultdict

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from api import fetch_all_data
from data import build_dataframes

warnings.filterwarnings("ignore")

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Hevy Dashboard",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Theme colors ───────────────────────────────────────────────────────────────
ACCENT = "#E84545"
BG = "#0E1117"
CARD_BG = "#1C1F2E"
TEXT = "#FAFAFA"
GRID = "#2A2D3E"
PALETTE = [
    "#E84545", "#F5A623", "#50FA7B", "#8BE9FD",
    "#BD93F9", "#FF79C6", "#FFB86C", "#6272A4",
]

MUSCLE_COLORS = {
    "chest": "#E84545",
    "quadriceps": "#F5A623",
    "shoulders": "#8BE9FD",
    "glutes": "#50FA7B",
    "upper_back": "#BD93F9",
    "hamstrings": "#FF79C6",
    "calves": "#FFB86C",
    "lats": "#6272A4",
    "triceps": "#F1FA8C",
    "biceps": "#44475A",
    "abdominals": "#69FF94",
    "lower_back": "#D6ACFF",
    "full_body": "#FF92DF",
    "abductors": "#A4FFFF",
    "unknown": "#555555",
}

WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* Main background */
    .stApp { background-color: #0E1117; }
    section[data-testid="stSidebar"] { background-color: #12151F; }

    /* Metric cards */
    div[data-testid="metric-container"] {
        background: #1C1F2E;
        border: 1px solid #2A2D3E;
        border-radius: 12px;
        padding: 16px 20px;
    }
    div[data-testid="metric-container"] label { color: #8892A4 !important; font-size: 0.78rem; letter-spacing: 0.08em; text-transform: uppercase; }
    div[data-testid="metric-container"] [data-testid="stMetricValue"] { color: #FAFAFA !important; font-size: 1.9rem; font-weight: 700; }
    div[data-testid="metric-container"] [data-testid="stMetricDelta"] { font-size: 0.82rem; }

    /* Chart containers */
    .chart-card {
        background: #1C1F2E;
        border: 1px solid #2A2D3E;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
    }

    /* Section headers */
    h2 { color: #FAFAFA !important; font-weight: 700; margin-top: 2rem; }
    h3 { color: #CBD5E1 !important; font-weight: 600; }

    /* Sidebar labels */
    .css-16huue1 { color: #8892A4; }

    /* Remove default padding */
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }

    /* Plotly chart border radius */
    .js-plotly-plot { border-radius: 8px; overflow: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── API key (from secrets only — never exposed in UI) ──────────────────────────
api_key = st.secrets.get("HEVY_API_KEY", os.getenv("HEVY_API_KEY", ""))

# ── Fixed units ────────────────────────────────────────────────────────────────
unit_label = "kg"
weight_factor = 1.0


# ── Data loading ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner="Fetching your Hevy data...")
def load_data(key: str):
    raw = fetch_all_data(key, force_refresh=True)
    return build_dataframes(raw)


if not api_key:
    st.info("Enter your Hevy API key in the sidebar to get started.")
    st.stop()

try:
    dfs = load_data(api_key)
except Exception as e:
    st.error(f"Failed to load data: {e}")
    st.stop()

df_w = dfs["workouts"].copy()
df_s = dfs["sets"].copy()
df_prs = dfs["prs"].copy()

# Apply weight conversion


# ── Helper: plotly defaults ────────────────────────────────────────────────────
def fig_defaults(fig, height=350, margin=None):
    m = margin or dict(l=16, r=16, t=40, b=16)
    fig.update_layout(
        height=height,
        margin=m,
        plot_bgcolor=CARD_BG,
        paper_bgcolor=CARD_BG,
        font=dict(color=TEXT, family="Inter, sans-serif", size=12),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
            font=dict(color="#CBD5E1", size=11),
        ),
        xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID),
        yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID),
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    f"<h1 style='font-size:2.2rem;font-weight:800;color:{TEXT};margin-bottom:0'>🏋️ Hevy Workout Dashboard</h1>",
    unsafe_allow_html=True,
)
date_range_str = f"{df_w['date'].min().strftime('%b %d, %Y')} – {df_w['date'].max().strftime('%b %d, %Y')}"
st.markdown(
    f"<p style='color:#8892A4;margin-top:4px;margin-bottom:1.5rem'>{date_range_str}</p>",
    unsafe_allow_html=True,
)

# ── Stats cards ────────────────────────────────────────────────────────────────
def compute_longest_streak(df: pd.DataFrame) -> int:
    workout_dates = sorted(df["date"].dt.date.unique())
    if not workout_dates:
        return 0
    longest = 1
    current = 1
    for i in range(1, len(workout_dates)):
        if (workout_dates[i] - workout_dates[i - 1]).days == 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest


total_workouts = len(df_w)
total_vol_tonnes = df_w["volume_kg"].sum() / 1000
avg_duration = df_w["duration_min"].mean()
longest_streak = compute_longest_streak(df_w)
avg_sets_per_session = df_w["total_sets"].mean()
total_unique_exercises = df_s["exercise"].nunique()

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Workouts", f"{total_workouts}")
c2.metric(f"Volume ({unit_label})", f"{total_vol_tonnes:.1f}t")
c3.metric("Avg Session", f"{avg_duration:.0f} min")
c4.metric("Longest Streak", f"{longest_streak} days")
c5.metric("Sets / Session", f"{avg_sets_per_session:.0f}")
c6.metric("Unique Exercises", f"{total_unique_exercises}")

st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# ROW 1 — Activity Calendar + Workout Frequency by Day
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("## 📅 Training Activity")
col_cal, col_dow = st.columns([3, 1])

# Activity calendar heatmap
with col_cal:
    date_counts = df_w.groupby("date").size().reset_index(name="count")
    date_counts["date"] = pd.to_datetime(date_counts["date"])
    date_counts["week"] = date_counts["date"].dt.isocalendar().week
    date_counts["year"] = date_counts["date"].dt.isocalendar().year
    date_counts["weekday_num"] = date_counts["date"].dt.weekday  # 0=Mon

    # Build full date grid
    min_date = df_w["date"].min()
    max_date = df_w["date"].max()
    all_dates = pd.date_range(min_date, max_date, freq="D")
    grid = pd.DataFrame({"date": all_dates})
    grid["weekday_num"] = grid["date"].dt.weekday
    grid["week_of_year"] = grid["date"].dt.isocalendar().week.astype(int)
    grid["year"] = grid["date"].dt.isocalendar().year.astype(int)
    # Create a sequential week number across years
    grid["year_week"] = grid["year"].astype(str) + "-" + grid["week_of_year"].astype(str).str.zfill(2)
    grid = grid.merge(date_counts[["date", "count"]], on="date", how="left").fillna({"count": 0})

    weeks = sorted(grid["year_week"].unique())
    week_idx = {w: i for i, w in enumerate(weeks)}
    grid["week_pos"] = grid["year_week"].map(week_idx)

    cal_fig = go.Figure(
        go.Heatmap(
            x=grid["week_pos"],
            y=grid["weekday_num"],
            z=grid["count"],
            text=grid["date"].dt.strftime("%b %d"),
            hovertemplate="%{text}<br>%{z} workout(s)<extra></extra>",
            colorscale=[
                [0.0, "#1C2135"],
                [0.01, "#2A3A6E"],
                [0.5, ACCENT],
                [1.0, "#FF8585"],
            ],
            showscale=False,
            xgap=3,
            ygap=3,
        )
    )

    # Add month labels
    month_ticks = []
    month_labels = []
    seen = set()
    for _, row in grid.iterrows():
        m = row["date"].strftime("%b")
        if m not in seen:
            seen.add(m)
            month_ticks.append(row["week_pos"])
            month_labels.append(m)

    cal_fig.update_layout(
        title=dict(text="Workout Calendar", font=dict(size=14, color=TEXT)),
        xaxis=dict(
            tickvals=month_ticks,
            ticktext=month_labels,
            showgrid=False,
            zeroline=False,
            linecolor=CARD_BG,
        ),
        yaxis=dict(
            tickvals=[0, 1, 2, 3, 4, 5, 6],
            ticktext=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            showgrid=False,
            zeroline=False,
            autorange="reversed",
        ),
    )
    fig_defaults(cal_fig, height=200)
    st.plotly_chart(cal_fig, use_container_width=True)

# Day of week heatmap
with col_dow:
    dow_counts = df_w["weekday"].value_counts().reindex(WEEKDAY_ORDER, fill_value=0)
    dow_fig = go.Figure(
        go.Bar(
            x=dow_counts.values,
            y=[d[:3] for d in dow_counts.index],
            orientation="h",
            marker=dict(
                color=dow_counts.values,
                colorscale=[[0, "#1C2135"], [1, ACCENT]],
                showscale=False,
            ),
            text=dow_counts.values,
            textposition="outside",
            hovertemplate="%{y}: %{x} workouts<extra></extra>",
        )
    )
    dow_fig.update_layout(
        title=dict(text="By Day of Week", font=dict(size=14, color=TEXT)),
        yaxis=dict(autorange="reversed", showgrid=False),
        xaxis=dict(showgrid=False, showticklabels=False),
    )
    fig_defaults(dow_fig, height=200)
    st.plotly_chart(dow_fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# ROW 2 — Volume over time + Duration distribution
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("## 📈 Volume & Session Trends")
col_vol, col_dur = st.columns([2, 1])

with col_vol:
    weekly = df_w.copy()
    weekly["week_start"] = weekly["date"] - pd.to_timedelta(weekly["date"].dt.weekday, unit="D")
    weekly_vol = weekly.groupby("week_start")["volume_kg"].sum().reset_index()
    weekly_vol["rolling_avg"] = weekly_vol["volume_kg"].rolling(4, min_periods=1).mean()

    vol_fig = go.Figure()
    vol_fig.add_trace(
        go.Bar(
            x=weekly_vol["week_start"],
            y=weekly_vol["volume_kg"],
            name=f"Weekly Volume ({unit_label})",
            marker_color=ACCENT,
            opacity=0.7,
            hovertemplate="%{x|%b %d}<br>%{y:,.0f} " + unit_label + "<extra></extra>",
        )
    )
    vol_fig.add_trace(
        go.Scatter(
            x=weekly_vol["week_start"],
            y=weekly_vol["rolling_avg"],
            name="4-week avg",
            line=dict(color="#F5A623", width=2.5),
            hovertemplate="%{x|%b %d}<br>Avg: %{y:,.0f} " + unit_label + "<extra></extra>",
        )
    )
    vol_fig.update_layout(
        title=dict(text=f"Weekly Training Volume ({unit_label})", font=dict(size=14, color=TEXT)),
        barmode="overlay",
        showlegend=True,
    )
    fig_defaults(vol_fig, height=300)
    st.plotly_chart(vol_fig, use_container_width=True)

with col_dur:
    dur_fig = go.Figure(
        go.Histogram(
            x=df_w["duration_min"].dropna(),
            nbinsx=20,
            marker=dict(
                color=ACCENT,
                opacity=0.85,
                line=dict(color=CARD_BG, width=1),
            ),
            hovertemplate="%{x:.0f} min<br>%{y} sessions<extra></extra>",
        )
    )
    avg_dur = df_w["duration_min"].mean()
    dur_fig.add_vline(
        x=avg_dur,
        line_dash="dash",
        line_color="#F5A623",
        annotation_text=f"avg {avg_dur:.0f}m",
        annotation_font_color="#F5A623",
        annotation_position="top right",
    )
    dur_fig.update_layout(
        title=dict(text="Session Duration Distribution", font=dict(size=14, color=TEXT)),
        xaxis_title="Minutes",
        yaxis_title="Sessions",
    )
    fig_defaults(dur_fig, height=300)
    st.plotly_chart(dur_fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# ROW 3 — Muscle group radar + Top exercises
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("## 💪 Muscle & Exercise Breakdown")
col_radar, col_exvol = st.columns([1, 2])

with col_radar:
    muscle_vol = (
        df_s[df_s["volume_kg"].notna()]
        .groupby("primary_muscle")["volume_kg"]
        .sum()
        .sort_values(ascending=False)
    )
    # Radar
    cats = list(muscle_vol.index)
    vals = list(muscle_vol.values)
    vals_closed = vals + [vals[0]]
    cats_closed = cats + [cats[0]]

    radar_fig = go.Figure(
        go.Scatterpolar(
            r=vals_closed,
            theta=cats_closed,
            fill="toself",
            fillcolor=f"rgba(232,69,69,0.25)",
            line=dict(color=ACCENT, width=2),
            hovertemplate="%{theta}<br>%{r:,.0f} " + unit_label + "<extra></extra>",
        )
    )
    radar_fig.update_layout(
        polar=dict(
            bgcolor=CARD_BG,
            radialaxis=dict(
                visible=True,
                gridcolor=GRID,
                linecolor=GRID,
                tickfont=dict(color="#8892A4", size=9),
                tickformat=".0f",
            ),
            angularaxis=dict(
                gridcolor=GRID,
                linecolor=GRID,
                tickfont=dict(color=TEXT, size=10),
            ),
        ),
        title=dict(text="Muscle Group Volume", font=dict(size=14, color=TEXT)),
        showlegend=False,
    )
    fig_defaults(radar_fig, height=400, margin=dict(l=80, r=80, t=50, b=50))
    st.plotly_chart(radar_fig, use_container_width=True)

with col_exvol:
    top_ex = (
        df_s[df_s["volume_kg"].notna()]
        .groupby("exercise")["volume_kg"]
        .sum()
        .sort_values(ascending=False)
        .head(15)
        .reset_index()
    )
    top_ex["volume_tonnes"] = top_ex["volume_kg"] / 1000

    # Map exercise to muscle color
    ex_muscles = df_s.drop_duplicates("exercise").set_index("exercise")["primary_muscle"].to_dict()
    top_ex["muscle"] = top_ex["exercise"].map(ex_muscles).fillna("unknown")
    top_ex["color"] = top_ex["muscle"].map(MUSCLE_COLORS).fillna("#555555")

    ex_fig = go.Figure(
        go.Bar(
            x=top_ex["volume_tonnes"],
            y=top_ex["exercise"],
            orientation="h",
            marker_color=top_ex["color"],
            text=top_ex["volume_tonnes"].map(lambda v: f"{v:.1f}t"),
            textposition="outside",
            hovertemplate="%{y}<br>%{x:.2f}t " + unit_label + "<extra></extra>",
        )
    )
    ex_fig.update_layout(
        title=dict(text=f"Top 15 Exercises by Total Volume (tonnes {unit_label})", font=dict(size=14, color=TEXT)),
        yaxis=dict(autorange="reversed"),
        xaxis_title=f"Total Volume (t {unit_label})",
    )
    fig_defaults(ex_fig, height=380)
    st.plotly_chart(ex_fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# ROW 4 — Exercise progression + PRs
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("## 🎯 Exercise Progression & PRs")

exercises_with_data = (
    df_s[df_s["weight_kg"].notna()]
    .groupby("exercise")["weight_kg"]
    .count()
    [lambda x: x >= 3]
    .sort_values(ascending=False)
    .index.tolist()
)

col_prog_select, _ = st.columns([1, 2])
with col_prog_select:
    selected_exercise = st.selectbox(
        "Select exercise to track progression",
        options=exercises_with_data,
        index=0 if exercises_with_data else None,
    )

if selected_exercise:
    col_prog, col_pr = st.columns([2, 1])

    with col_prog:
        ex_data = (
            df_s[(df_s["exercise"] == selected_exercise) & df_s["weight_kg"].notna()]
            .copy()
        )
        # Max weight per session
        session_max = (
            ex_data.groupby("workout_date")
            .agg(
                max_weight=("weight_kg", "max"),
                total_volume=("volume_kg", "sum"),
                total_sets=("weight_kg", "count"),
            )
            .reset_index()
        )

        prog_fig = make_subplots(specs=[[{"secondary_y": True}]])
        prog_fig.add_trace(
            go.Scatter(
                x=session_max["workout_date"],
                y=session_max["max_weight"],
                mode="lines+markers",
                name=f"Max weight ({unit_label})",
                line=dict(color=ACCENT, width=2.5),
                marker=dict(size=6, color=ACCENT),
                hovertemplate="%{x|%b %d, %Y}<br>%{y:.1f} " + unit_label + "<extra></extra>",
            ),
            secondary_y=False,
        )
        prog_fig.add_trace(
            go.Bar(
                x=session_max["workout_date"],
                y=session_max["total_volume"],
                name=f"Session volume ({unit_label})",
                marker=dict(color="#F5A623", opacity=0.4),
                hovertemplate="%{x|%b %d}<br>%{y:,.0f} " + unit_label + "<extra></extra>",
            ),
            secondary_y=True,
        )

        # PR annotations
        ex_prs = df_prs[df_prs["exercise"] == selected_exercise]
        if not ex_prs.empty:
            for _, pr in ex_prs.iterrows():
                prog_fig.add_annotation(
                    x=pr["date"],
                    y=pr["weight_kg"],
                    text="🏆",
                    showarrow=False,
                    yshift=18,
                    font=dict(size=14),
                )

        prog_fig.update_layout(
            title=dict(text=f"{selected_exercise} — Weight Progression", font=dict(size=14, color=TEXT)),
            plot_bgcolor=CARD_BG,
            paper_bgcolor=CARD_BG,
            font=dict(color=TEXT, family="Inter, sans-serif"),
            legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0, font=dict(color="#CBD5E1")),
            height=320,
            margin=dict(l=16, r=16, t=40, b=16),
            xaxis=dict(gridcolor=GRID, zerolinecolor=GRID),
            yaxis=dict(gridcolor=GRID, title=f"Max Weight ({unit_label})"),
            yaxis2=dict(gridcolor="rgba(0,0,0,0)", title=f"Volume ({unit_label})", showgrid=False),
        )
        st.plotly_chart(prog_fig, use_container_width=True)

    with col_pr:
        pr_table = ex_prs.sort_values("date", ascending=False).head(8)
        if not pr_table.empty:
            st.markdown(f"**🏆 PRs for {selected_exercise}**")
            for _, r in pr_table.iterrows():
                st.markdown(
                    f"<div style='background:{CARD_BG};border:1px solid {GRID};border-radius:8px;"
                    f"padding:8px 12px;margin:4px 0'>"
                    f"<span style='color:{ACCENT};font-weight:700'>{r['weight_kg']:.1f} {unit_label}</span>"
                    f" × {int(r['reps']) if pd.notna(r['reps']) else '?'} reps"
                    f"<br><span style='color:#8892A4;font-size:0.78rem'>{pd.Timestamp(r['date']).strftime('%b %d, %Y')}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.info("No PRs recorded for this exercise.")


# ══════════════════════════════════════════════════════════════════════════════
# ROW 5 — Estimated 1 Rep Max (Big 5)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("## 🏆 Estimated 1 Rep Max — The Big 5")

BIG_5 = [
    "Bench Press (Barbell)",
    "Squat (Barbell)",
    "Deadlift (Barbell)",
    "Overhead Press (Barbell)",
    "Pendlay Row (Barbell)",
]

def epley(w, r):
    if r == 1:
        return w
    return w * (1 + r / 30)

def brzycki(w, r):
    if r >= 37:
        return None
    return w * 36 / (37 - r)

def lander(w, r):
    return (100 * w) / (101.3 - 2.67123 * r)

def best_1rm(exercise: str, df: pd.DataFrame):
    """Return the set with the highest estimated 1RM across all formulas."""
    rows = df[(df["exercise"] == exercise) & df["weight_kg"].notna() & df["reps"].notna()].copy()
    rows = rows[rows["reps"] >= 1]
    if rows.empty:
        return None
    rows["epley"] = rows.apply(lambda r: epley(r["weight_kg"], r["reps"]), axis=1)
    rows["brzycki"] = rows.apply(lambda r: brzycki(r["weight_kg"], r["reps"]), axis=1)
    rows["lander"] = rows.apply(lambda r: lander(r["weight_kg"], r["reps"]), axis=1)
    # Pick the row with the highest Epley estimate as the "best set"
    best = rows.loc[rows["epley"].idxmax()]
    return best

orm_records = []
for lift in BIG_5:
    best = best_1rm(lift, df_s)
    if best is not None:
        orm_records.append({
            "exercise": lift,
            "weight": best["weight_kg"] * weight_factor,
            "reps": int(best["reps"]),
            "date": best["workout_date"],
            "epley": epley(best["weight_kg"], best["reps"]) * weight_factor,
            "brzycki": (brzycki(best["weight_kg"], best["reps"]) or 0) * weight_factor,
            "lander": lander(best["weight_kg"], best["reps"]) * weight_factor,
        })

# ── Cards row ──────────────────────────────────────────────────────────────────
short_names = {
    "Bench Press (Barbell)": "Bench",
    "Squat (Barbell)": "Squat",
    "Deadlift (Barbell)": "Deadlift",
    "Overhead Press (Barbell)": "OHP",
    "Pendlay Row (Barbell)": "Pendlay Row",
}

card_cols = st.columns(len(orm_records))
for col, rec in zip(card_cols, orm_records):
    avg_1rm = (rec["epley"] + rec["brzycki"] + rec["lander"]) / 3
    col.markdown(
        f"<div style='background:{CARD_BG};border:1px solid {GRID};border-radius:12px;"
        f"padding:14px 16px;text-align:center'>"
        f"<div style='color:#8892A4;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.07em;margin-bottom:4px'>"
        f"{short_names.get(rec['exercise'], rec['exercise'])}</div>"
        f"<div style='color:{ACCENT};font-size:1.7rem;font-weight:800;line-height:1.1'>{avg_1rm:.1f}</div>"
        f"<div style='color:#8892A4;font-size:0.75rem;margin-top:2px'>{unit_label} avg est.</div>"
        f"<div style='color:#CBD5E1;font-size:0.78rem;margin-top:8px'>Best set: "
        f"<b>{rec['weight']:.1f}{unit_label} × {rec['reps']}</b></div>"
        f"<div style='color:#8892A4;font-size:0.72rem'>{pd.Timestamp(rec['date']).strftime('%b %d, %Y')}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── Grouped bar chart comparing formulas ──────────────────────────────────────
if orm_records:
    lift_labels = [short_names.get(r["exercise"], r["exercise"]) for r in orm_records]
    orm_fig = go.Figure()
    for formula, color in [("epley", ACCENT), ("brzycki", "#F5A623"), ("lander", "#8BE9FD")]:
        orm_fig.add_trace(
            go.Bar(
                name=formula.capitalize(),
                x=lift_labels,
                y=[r[formula] for r in orm_records],
                marker=dict(color=color, opacity=0.85, line=dict(color=CARD_BG, width=1)),
                text=[f"{r[formula]:.1f}" for r in orm_records],
                textposition="outside",
                hovertemplate="%{x}<br>" + formula.capitalize() + ": %{y:.1f} " + unit_label + "<extra></extra>",
            )
        )
    orm_fig.update_layout(
        title=dict(text=f"Estimated 1RM by Formula ({unit_label})", font=dict(size=14, color=TEXT)),
        barmode="group",
        yaxis_title=f"Estimated 1RM ({unit_label})",
        yaxis=dict(range=[0, max(r["epley"] for r in orm_records) * 1.2]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig_defaults(orm_fig, height=320)
    st.plotly_chart(orm_fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# ROW 6 — Workout type breakdown + Sets per session
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("## 🗂️ Workout Types & Session Stats", )
col_type, col_sets = st.columns([3, 2])

with col_type:
    type_counts = df_w["title"].value_counts().head(10).reset_index()
    type_counts.columns = ["title", "count"]
    # Color each bar from the palette
    bar_colors = (PALETTE * 3)[: len(type_counts)]

    type_fig = go.Figure(
        go.Bar(
            x=type_counts["count"],
            y=type_counts["title"],
            orientation="h",
            marker=dict(color=bar_colors, line=dict(color=CARD_BG, width=1)),
            text=type_counts["count"].apply(lambda v: f"{v}"),
            textposition="auto",
            hovertemplate="%{y}<br>%{x} sessions<extra></extra>",
        )
    )
    type_fig.update_layout(
        title=dict(text="Workout Type Frequency", font=dict(size=14, color=TEXT)),
        xaxis=dict(showgrid=False, showticklabels=False, range=[0, type_counts["count"].max() * 1.25]),
        yaxis=dict(autorange="reversed", showgrid=False, tickfont=dict(size=11)),
    )
    fig_defaults(type_fig, height=340)
    st.plotly_chart(type_fig, use_container_width=True)

with col_sets:
    sets_fig = go.Figure(
        go.Histogram(
            x=df_w["total_sets"].dropna(),
            nbinsx=15,
            marker=dict(
                color="#8BE9FD",
                opacity=0.85,
                line=dict(color=CARD_BG, width=1),
            ),
            hovertemplate="%{x} sets<br>%{y} sessions<extra></extra>",
        )
    )
    avg_sets = df_w["total_sets"].mean()
    sets_fig.add_vline(
        x=avg_sets,
        line_dash="dash",
        line_color="#F5A623",
        annotation_text=f"avg {avg_sets:.0f} sets",
        annotation_font_color="#F5A623",
        annotation_position="top right",
    )
    sets_fig.update_layout(
        title=dict(text="Sets per Session", font=dict(size=14, color=TEXT)),
        xaxis_title="Number of Sets",
        yaxis_title="Sessions",
    )
    fig_defaults(sets_fig, height=340)
    st.plotly_chart(sets_fig, use_container_width=True)

# Full-width: exercises per session trend
ex_over_time = df_w.sort_values("date")[["date", "n_exercises", "total_sets"]].copy()
rolling_ex = ex_over_time["n_exercises"].rolling(8, min_periods=1).mean()

intensity_fig = go.Figure()
intensity_fig.add_trace(
    go.Bar(
        x=ex_over_time["date"],
        y=ex_over_time["n_exercises"],
        name="Exercises",
        marker=dict(color=ACCENT, opacity=0.4),
        hovertemplate="%{x|%b %d, %Y}<br>%{y} exercises<extra></extra>",
    )
)
intensity_fig.add_trace(
    go.Scatter(
        x=ex_over_time["date"],
        y=rolling_ex,
        name="8-session avg",
        line=dict(color="#50FA7B", width=2.5),
        hovertemplate="%{x|%b %d}<br>avg %{y:.1f} exercises<extra></extra>",
    )
)
intensity_fig.update_layout(
    title=dict(text="Exercises per Session Over Time", font=dict(size=14, color=TEXT)),
    yaxis_title="# Exercises",
    showlegend=True,
)
fig_defaults(intensity_fig, height=260)
st.plotly_chart(intensity_fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# ROW 6 — Monthly progress heatmap + RPE / Muscle balance
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("## 📊 Monthly Progress & Balance")
col_monthly, col_balance = st.columns([2, 1])

with col_monthly:
    monthly = df_w.copy()
    monthly["month_label"] = monthly["date"].dt.strftime("%b %Y")
    monthly["month_dt"] = monthly["date"].dt.to_period("M").dt.to_timestamp()
    monthly_stats = (
        monthly.groupby("month_dt")
        .agg(
            workouts=("id", "count"),
            volume=("volume_kg", "sum"),
            avg_duration=("duration_min", "mean"),
        )
        .reset_index()
    )
    monthly_stats["month_label"] = monthly_stats["month_dt"].dt.strftime("%b %Y")

    month_fig = make_subplots(specs=[[{"secondary_y": True}]])
    month_fig.add_trace(
        go.Bar(
            x=monthly_stats["month_label"],
            y=monthly_stats["volume"] / 1000,
            name=f"Volume (t {unit_label})",
            marker_color=ACCENT,
            opacity=0.8,
            hovertemplate="%{x}<br>%{y:.1f}t<extra></extra>",
        ),
        secondary_y=False,
    )
    month_fig.add_trace(
        go.Scatter(
            x=monthly_stats["month_label"],
            y=monthly_stats["workouts"],
            name="Sessions",
            line=dict(color="#50FA7B", width=2.5),
            marker=dict(size=8, color="#50FA7B"),
            hovertemplate="%{x}<br>%{y} sessions<extra></extra>",
            mode="lines+markers",
        ),
        secondary_y=True,
    )
    month_fig.update_layout(
        title=dict(text="Monthly Volume & Session Count", font=dict(size=14, color=TEXT)),
        plot_bgcolor=CARD_BG,
        paper_bgcolor=CARD_BG,
        font=dict(color=TEXT, family="Inter, sans-serif"),
        legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0, font=dict(color="#CBD5E1")),
        height=320,
        margin=dict(l=16, r=16, t=40, b=16),
        xaxis=dict(gridcolor=GRID),
        yaxis=dict(gridcolor=GRID, title=f"Volume (t {unit_label})"),
        yaxis2=dict(gridcolor="rgba(0,0,0,0)", title="Sessions", showgrid=False),
    )
    st.plotly_chart(month_fig, use_container_width=True)

with col_balance:
    # Push vs Pull vs Legs balance
    push_muscles = {"chest", "triceps", "shoulders"}
    pull_muscles = {"upper_back", "lats", "biceps"}
    leg_muscles = {"quadriceps", "hamstrings", "glutes", "calves"}

    def classify(m):
        if m in push_muscles:
            return "Push"
        elif m in pull_muscles:
            return "Pull"
        elif m in leg_muscles:
            return "Legs"
        else:
            return "Other"

    df_s_bal = df_s[df_s["volume_kg"].notna()].copy()
    df_s_bal["category"] = df_s_bal["primary_muscle"].apply(classify)
    balance = df_s_bal.groupby("category")["volume_kg"].sum()

    balance_fig = go.Figure(
        go.Pie(
            labels=balance.index,
            values=balance.values,
            hole=0.5,
            textinfo="label+percent",
            hovertemplate="%{label}<br>%{value:,.0f} " + unit_label + " (%{percent})<extra></extra>",
            marker=dict(
                colors=[ACCENT, "#8BE9FD", "#50FA7B", "#6272A4"],
                line=dict(color=CARD_BG, width=2),
            ),
        )
    )
    balance_fig.update_layout(
        title=dict(text="Push / Pull / Legs Balance", font=dict(size=14, color=TEXT)),
        showlegend=False,
    )
    fig_defaults(balance_fig, height=320)
    st.plotly_chart(balance_fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#8892A4;font-size:0.8rem'>"
    "Built with Streamlit & Plotly · Data from <a href='https://hevy.com' style='color:#E84545'>Hevy App</a>"
    "</div>",
    unsafe_allow_html=True,
)
