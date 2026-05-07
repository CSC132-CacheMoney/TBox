from flask import Blueprint, render_template, redirect, url_for, session
from datetime import datetime
import database

summary_bp = Blueprint("summary", __name__)


def _fmt_dur(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}h {m}m" if h else f"{m}m"


def _enrich_current(row, limit_hours):
    diff = datetime.now() - datetime.fromisoformat(row["checked_out_at"])
    total_h = diff.total_seconds() / 3600
    return {
        **row,
        "duration": _fmt_dur(diff.total_seconds()),
        "bar_pct": min(int(total_h / limit_hours * 100), 100),
        "overdue": total_h > limit_hours,
    }


def _enrich_history(row):
    if row["returned_at"]:
        diff = (datetime.fromisoformat(row["returned_at"])
                - datetime.fromisoformat(row["checked_out_at"]))
        return {**row, "duration": _fmt_dur(diff.total_seconds()), "active": False}
    diff = datetime.now() - datetime.fromisoformat(row["checked_out_at"])
    return {**row, "duration": _fmt_dur(diff.total_seconds()), "active": True}


@summary_bp.route("/summary")
def summary():
    if "user" not in session:
        return redirect(url_for("login.login"))

    username = session["user"]
    data = database.get_user_summary(username)
    stats = data["stats"]
    limit_hours = int(database.get_config("checkout_limit_hours") or 24)

    avg_h = stats.get("avg_hours")
    avg_str = _fmt_dur(avg_h * 3600) if avg_h else "—"

    current = [_enrich_current(r, limit_hours) for r in data["current"]]
    history = [_enrich_history(r) for r in data["history"]]

    top_max = data["top_tools"][0]["uses"] if data["top_tools"] else 1
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
