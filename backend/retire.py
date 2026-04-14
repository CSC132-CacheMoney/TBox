from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import database

retire_bp = Blueprint("retire", __name__)


@retire_bp.route("/retire", methods=["GET", "POST"])
def retire_tool():
    """
    Retire Tool screen (s10071).
    - GET:  Show the list of active (non-retired) tools to choose from.
    - POST: Mark selected tool(s) as Retired in the database.
            Retired tools stay in the DB for checkout history records.
    """
    if "user" not in session:
        return redirect(url_for("login.login"))

    if request.method == "POST":
        raw = request.form.get("tool_id", "")
        tool_ids = [int(i) for i in raw.split(",") if i.strip().isdigit()]

        if not tool_ids:
            flash("No tools selected.", "error")
            return redirect(url_for("retire.retire_tool"))

        retired_names = []
        for tool_id in tool_ids:
            tool = database.get_tool_by_id(tool_id)
            if tool:
                # Don't retire a tool that's currently checked out
                if tool["status"] == "Checked Out":
                    flash(
                        f"'{tool['name']}' is currently checked out and cannot be retired.",
                        "error"
                    )
                    continue
                database.retire_tool(tool_id)
                retired_names.append(tool["name"])

        if retired_names:
            flash(
                f"{len(retired_names)} tool(s) retired: {', '.join(retired_names)}.",
                "success"
            )

        return redirect(url_for("inventory.inventory"))

    # GET — load all tools that can be retired (not already retired)
    tools = [dict(row) for row in database.get_active_tools()]

    return render_template("retire.html", tools=tools)