# dashboard.py — dashboard page and live-update endpoints

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
    """Attach a human-readable duration and progress-bar percentage to the
    longest-running checkout row returned by database.get_longest_checkout()."""
    if not row:
        return None
    diff        = datetime.now() - datetime.fromisoformat(row["checked_out_at"])
    total_hours = diff.total_seconds() / 3600
    hours       = int(total_hours)
    mins        = int((diff.total_seconds() % 3600) // 60)
    limit       = int(database.get_config("checkout_limit_hours") or 24)
    return {
        **row,
        "duration": f"{hours}h {mins}m" if hours else f"{mins}m",
        "hours":    hours,
        # Cap at 100 so the progress bar never overflows
        "bar_pct":  min(int(total_hours / limit * 100), 100),
    }


@dashboard_bp.route("/dashboard")
def dashboard():
    """Main dashboard — requires an active session."""
    if "user" not in session:
        return redirect(url_for("login.login"))

    stats    = database.get_dashboard_stats()
    longest  = _enrich_longest(database.get_longest_checkout())
    weekly   = database.get_weekly_checkouts()
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
    """JSON endpoint polled by the dashboard to refresh stat cards without a
    full page reload."""
    if "user" not in session:
        abort(401)
    return jsonify({
        "stats":   database.get_dashboard_stats(),
        "longest": _enrich_longest(database.get_longest_checkout()),
        "weekly":  database.get_weekly_checkouts(),
    })


@dashboard_bp.route("/dashboard/events")
def dashboard_events():
    """Server-Sent Events stream that pushes new activity entries to the
    dashboard live log every 4 seconds.  The stop Event lets the generator
    exit immediately on client disconnect instead of blocking on sleep()."""
    if "user" not in session:
        abort(401)

    stop = threading.Event()

    def generate():
        last_seen = datetime.now().isoformat()
        # Initial ping confirms the stream is open
        yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        try:
            # stop.wait() blocks for up to 4 s, then returns False so the loop
            # continues; returns True immediately when the client disconnects
            while not stop.wait(timeout=4):
                events = database.get_recent_activity(since=last_seen, limit=15)
                if events:
                    last_seen = events[0]["event_time"]
                    # Send oldest-first so the UI appends in the right order
                    for e in reversed(events):
                        yield f"data: {json.dumps(e)}\n\n"
                else:
                    # Keep the connection alive even when there is no new data
                    yield ": keepalive\n\n"
        finally:
            # Ensure the event is set so the thread is not left hanging
            stop.set()

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
