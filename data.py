"""Transform raw Hevy API data into analysis-ready DataFrames."""

import pandas as pd
from datetime import datetime, timezone


def build_dataframes(raw: dict) -> dict:
    workouts = raw["workouts"]
    templates = raw["templates"]

    template_map = {t["id"]: t for t in templates}

    # ── Workout-level DataFrame ────────────────────────────────────────────
    rows = []
    for w in workouts:
        start = _parse_dt(w["start_time"])
        end = _parse_dt(w["end_time"])
        duration_min = (end - start).total_seconds() / 60 if start and end else None

        total_vol = 0
        total_sets = 0
        exercise_titles = []
        for ex in w["exercises"]:
            exercise_titles.append(ex["title"])
            for s in ex["sets"]:
                if s.get("weight_kg") and s.get("reps"):
                    total_vol += s["weight_kg"] * s["reps"]
                    total_sets += 1

        rows.append(
            {
                "id": w["id"],
                "title": w["title"],
                "date": start.date() if start else None,
                "start_time": start,
                "end_time": end,
                "duration_min": duration_min,
                "volume_kg": total_vol,
                "total_sets": total_sets,
                "n_exercises": len(w["exercises"]),
                "exercise_list": exercise_titles,
                "weekday": start.strftime("%A") if start else None,
                "week": start.strftime("%Y-W%W") if start else None,
                "month": start.strftime("%Y-%m") if start else None,
                "year_week": start.isocalendar()[:2] if start else None,
            }
        )

    df_workouts = pd.DataFrame(rows)
    df_workouts["date"] = pd.to_datetime(df_workouts["date"])

    # ── Set-level DataFrame ────────────────────────────────────────────────
    set_rows = []
    for w in workouts:
        start = _parse_dt(w["start_time"])
        for ex in w["exercises"]:
            tid = ex.get("exercise_template_id", "")
            tmpl = template_map.get(tid, {})
            for s in ex["sets"]:
                set_rows.append(
                    {
                        "workout_id": w["id"],
                        "workout_date": start.date() if start else None,
                        "exercise": ex["title"],
                        "template_id": tid,
                        "primary_muscle": tmpl.get("primary_muscle_group", "unknown"),
                        "secondary_muscles": tmpl.get("secondary_muscle_groups", []),
                        "equipment": tmpl.get("equipment", "unknown"),
                        "set_type": s.get("type", "normal"),
                        "weight_kg": s.get("weight_kg"),
                        "reps": s.get("reps"),
                        "volume_kg": (
                            s["weight_kg"] * s["reps"]
                            if s.get("weight_kg") and s.get("reps")
                            else None
                        ),
                        "duration_seconds": s.get("duration_seconds"),
                        "rpe": s.get("rpe"),
                    }
                )

    df_sets = pd.DataFrame(set_rows)
    df_sets["workout_date"] = pd.to_datetime(df_sets["workout_date"])

    # ── Personal Records DataFrame ─────────────────────────────────────────
    pr_rows = []
    for exercise, group in df_sets[df_sets["weight_kg"].notna()].groupby("exercise"):
        group_sorted = group.sort_values("workout_date")
        max_so_far = 0.0
        for _, row in group_sorted.iterrows():
            if row["weight_kg"] > max_so_far:
                max_so_far = row["weight_kg"]
                pr_rows.append(
                    {
                        "exercise": exercise,
                        "date": row["workout_date"],
                        "weight_kg": row["weight_kg"],
                        "reps": row["reps"],
                        "primary_muscle": row["primary_muscle"],
                    }
                )
    df_prs = pd.DataFrame(pr_rows)

    return {
        "workouts": df_workouts,
        "sets": df_sets,
        "prs": df_prs,
        "template_map": template_map,
    }


def _parse_dt(s: str):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None
