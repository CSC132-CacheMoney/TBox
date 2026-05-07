import json
import threading
import time
from datetime import datetime
from flask import (Blueprint, Response, abort, jsonify,
                   redirect, render_template, session,
                   stream_with_context, url_for)
import database

dashboard_bp = Blueprint("dashboard", __name__)


def _enrich_longest(row):
    if not row:
        return None
    diff = datetime.now() - datetime.fromisoformat(row["checked_out_at"])
    total_hours = diff.total_seconds() / 3600
    hours = int(total_hours)
    mins = int((diff.total_seconds() % 3600) // 60)
    limit = int(database.get_config("checkout_limit_hours") or 24)
    return {
        **row,
        "duration": f"{hours}h {mins}m" if hours else f"{mins}m",
        "hours": hours,
        "bar_pct": min(int(total_hours / limit * 100), 100),
    }


@dashboard_bp.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login.login"))

    stats = database.get_dashboard_stats()
    longest = _enrich_longest(database.get_longest_checkout())
    weekly = database.get_weekly_checkouts()
    activity = database.get_recent_activity(limit=20)

    return render_template(
        "dashboard.html",
        user=session["user"],
        stats=stats,
        longest=longest,
        weekly=weekly,
        activity=activity,
    )


@dashboard_bp.route("/dashboard/stats")
def dashboard_stats():
    if "user" not in session:
        abort(401)
    return jsonify({
        "stats": database.get_dashboard_stats(),
        "longest": _enrich_longest(database.get_longest_checkout()),
        "weekly": database.get_weekly_checkouts(),
    })


@dashboard_bp.route("/dashboard/events")
def dashboard_events():
    if "user" not in session:
        abort(401)

    stop = threading.Event()

    def generate():
        last_seen = datetime.now().isoformat()
        yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        try:
            while not stop.wait(timeout=4):
                events = database.get_recent_activity(since=last_seen, limit=15)
                if events:
                    last_seen = events[0]["event_time"]
                    for e in reversed(events):
                        yield f"data: {json.dumps(e)}\n\n"
                else:
                    yield ": keepalive\n\n"
        finally:
            stop.set()

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
