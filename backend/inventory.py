# inventory.py — tool inventory list and checkout submission

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import threading
import database
from alerts import SMTPServer
import pico_Reader

inventory_bp = Blueprint("inventory", __name__)
Notify = SMTPServer()   # used to send checkout alert emails in a background thread


@inventory_bp.route("/inventory")
def inventory():
    """Display all non-retired tools as selectable pill buttons.
    Supports an optional ?filter= query param: all | available | checked-out | retired."""
    if "user" not in session:
        return redirect(url_for("login.login"))

    filter_by = request.args.get("filter", "all")
    all_tools = [dict(row) for row in database.get_all_tools()]

    # Apply status filter; default hides retired tools
    if filter_by == "available":
        tools = [t for t in all_tools if t["status"] == "Available"]
    elif filter_by == "checked-out":
        tools = [t for t in all_tools if t["status"] == "Checked Out"]
    elif filter_by == "retired":
        tools = [t for t in all_tools if t["status"] == "Retired"]
    else:
        tools = [t for t in all_tools if t["status"] != "Retired"]

    return render_template(
        "inventory.html",
        tools=tools,
        filter_by=filter_by,
        user=session["user"]
    )


@inventory_bp.route("/inventory/checkout", methods=["POST"])
def checkout():
    """Process checkout of one or more tools.
    Expects a comma-separated list of tool IDs in the 'tool_ids' form field."""
    if "user" not in session:
        return redirect(url_for("login.login"))

    raw      = request.form.get("tool_ids", "")
    tool_ids = [int(i) for i in raw.split(",") if i.strip().isdigit()]

    succeeded, failed = [], []
    for tool_id in tool_ids:
        try:
            database.checkout_tool(tool_id, session["user"])
            tool  = dict(database.get_tool_by_id(tool_id))
            label = database.display_name(tool)
            succeeded.append(label)
            # Send alert in a daemon thread so it doesn't block the redirect
            threading.Thread(target=Notify.send_checked_out, args=(label,), daemon=True).start()
        except ValueError as e:
            failed.append(str(e))

    if succeeded:
        flash(f"{len(succeeded)} tool(s) checked out to {session['user']}.", "success")
    for msg in failed:
        flash(msg, "error")

    return redirect(url_for("inventory.inventory"))
