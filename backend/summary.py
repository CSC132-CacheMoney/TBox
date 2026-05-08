# summary.py — per-user checkout summary page

from flask import Blueprint, render_template, redirect, url_for, session
from datetime import datetime
import database

summary_bp = Blueprint("summary", __name__)


def _fmt_dur(seconds):
    """Convert a duration in seconds to a compact 'Xh Ym' string."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}h {m}m" if h else f"{m}m"


def _enrich_current(row, limit_hours):
    """Attach duration, progress-bar percentage, and overdue flag to an
    active checkout row."""
    diff    = datetime.now() - datetime.fromisoformat(row["checked_out_at"])
    total_h = diff.total_seconds() / 3600
    return {
        **row,
        "duration": _fmt_dur(diff.total_seconds()),
        # Cap at 100 so the bar never overflows the container
        "bar_pct":  min(int(total_h / limit_hours * 100), 100),
        "overdue":  total_h > limit_hours,
    }


def _enrich_history(row):
    """Attach duration and active flag to a checkout history row.
    Active rows (not yet returned) calculate duration from now."""
    if row["returned_at"]:
        diff = (datetime.fromisoformat(row["returned_at"])
                - datetime.fromisoformat(row["checked_out_at"]))
        return {**row, "duration": _fmt_dur(diff.total_seconds()), "active": False}
    diff = datetime.now() - datetime.fromisoformat(row["checked_out_at"])
    return {**row, "duration": _fmt_dur(diff.total_seconds()), "active": True}


@summary_bp.route("/summary")
def summary():
    """Per-user summary page showing stats, current checkouts, history, and
    most-used tools.  Always shows data for the logged-in user."""
    if "user" not in session:
        return redirect(url_for("login.login"))

    username    = session["user"]
    data        = database.get_user_summary(username)
    stats       = data["stats"]
    limit_hours = int(database.get_config("checkout_limit_hours") or 24)

    # Format average checkout duration; falls back to '—' if no history
    avg_h   = stats.get("avg_hours")
    avg_str = _fmt_dur(avg_h * 3600) if avg_h else "—"

    current   = [_enrich_current(r, limit_hours) for r in data["current"]]
    history   = [_enrich_history(r) for r in data["history"]]

    # Normalise top-tools usage counts to percentages relative to the top entry
    top_max   = data["top_tools"][0]["uses"] if data["top_tools"] else 1
    top_tools = [
        {**r, "pct": int(r["uses"] / top_max * 100)}
        for r in data["top_tools"]
    ]

    return render_template(
        "summary.html",
        stats=stats,
        avg_str=avg_str,
        current=current,
        history=history,
        top_tools=top_tools,
    )
