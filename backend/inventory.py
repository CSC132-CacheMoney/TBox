from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import threading
import database
from alerts import SMTPServer
import pico_Reader

inventory_bp = Blueprint("inventory", __name__)
Notify = SMTPServer()



@inventory_bp.route("/inventory")
def inventory():
    """
    Inventory screen (s10069).

    Displays all non-retired tools as clickable pill buttons.

    Supports optional ?filter= query param: all | available | checked-out
    """
    if "user" not in session:
        return redirect(url_for("login.login"))

    filter_by = request.args.get("filter", "all")

    all_tools = [dict(row) for row in database.get_all_tools()]

    if filter_by == "available":
        tools = [t for t in all_tools if t["status"] == "Available"]
    elif filter_by == "checked-out":
        tools = [t for t in all_tools if t["status"] == "Checked Out"]
    elif filter_by == "retired":
        tools = [t for t in all_tools if t["status"] == "Retired"]
    else:
        # Default: show everything except retired
        tools = [t for t in all_tools if t["status"] != "Retired"]

    return render_template(
        "inventory.html",
        tools=tools,
        filter_by=filter_by,
        user=session["user"]
    )


@inventory_bp.route("/inventory/checkout", methods=["POST"])
def checkout():
    """
    Handle checkout of one or more tools.
    Expects a JSON body or form field 'tool_ids' (comma-separated).
    Called when the user selects tools in the inventory and confirms checkout.
    """
    if "user" not in session:
        return redirect(url_for("login.login"))

    raw = request.form.get("tool_ids", "")
    tool_ids = [int(i) for i in raw.split(",") if i.strip().isdigit()]

    succeeded, failed = [], []
    for tool_id in tool_ids:
        try:
            database.checkout_tool(tool_id, session["user"])
            name = database.get_tool_by_id(tool_id)["name"]
            succeeded.append(name)
            threading.Thread(target=Notify.send_checked_out, args=(name,), daemon=True).start()
        except ValueError as e:
            failed.append(str(e))

    if succeeded:
        flash(f"{len(succeeded)} tool(s) checked out to {session['user']}.", "success")
    for msg in failed:
        flash(msg, "error")
    
    return redirect(url_for("inventory.inventory"))


