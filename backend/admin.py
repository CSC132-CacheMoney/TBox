import os
import json
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
import database

admin_bp = Blueprint("admin", __name__)

SETTINGS_PATH = Path(__file__).resolve().parent.parent / "config" / "settings.json"


def _load_settings():
    with open(SETTINGS_PATH) as f:
        return json.load(f)


def _save_settings(data):
    with open(SETTINGS_PATH, "w") as f:
        json.dump(data, f, indent=2)


def _is_admin():
    if session.get("is_admin"):
        return True
    if "user" in session and database.is_user_admin(session["user"]):
        session["is_admin"] = True
        return True
    return False


@admin_bp.route("/admin/auth", methods=["POST"])
def admin_auth():
    if "user" not in session:
        return jsonify({"success": False, "error": "Not logged in"}), 401
    password = request.form.get("password", "")
    admin_password = os.getenv("ADMIN_PASSWORD", "")
    if not admin_password:
        return jsonify({"success": False, "error": "No ADMIN_PASSWORD configured in .env"})
    if password == admin_password:
        session["is_admin"] = True
        database.set_admin(session["user"], True)
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Incorrect password"})


@admin_bp.route("/admin")
def admin_panel():
    if "user" not in session:
        return redirect(url_for("login.login"))
    if not _is_admin():
        return redirect(url_for("dashboard.dashboard"))

    checked_out = database.get_checked_out_tools()
    settings = _load_settings()
    return render_template("admin.html", checked_out=checked_out, settings=settings)


@admin_bp.route("/admin/settings", methods=["POST"])
def admin_save_settings():
    if "user" not in session or not _is_admin():
        return redirect(url_for("admin.admin_panel"))

    try:
        new_settings = {
            "rfid": {
                "port": request.form.get("rfid_port", "").strip()
            },
            "alerts": {
                "checkout_limit_hours": int(request.form.get("checkout_limit_hours", 24)),
                "email_host": request.form.get("email_host", "").strip(),
                "email_port": int(request.form.get("email_port", 587)),
                "alert_method": request.form.get("alert_method", "console"),
                "email_from": request.form.get("email_from", "").strip(),
                "email_to": request.form.get("email_to", "").strip(),
            },
            "database": {
                "path": request.form.get("db_path", "data/tools.db").strip()
            }
        }
        _save_settings(new_settings)
        flash("Settings saved successfully.", "success")
    except (ValueError, OSError) as e:
        flash(f"Failed to save settings: {e}", "error")

    return redirect(url_for("admin.admin_panel") + "#settings")


@admin_bp.route("/admin/return/<int:tool_id>", methods=["POST"])
def admin_return_tool(tool_id):
    if "user" not in session or not _is_admin():
        return redirect(url_for("admin.admin_panel"))

    tool = database.get_tool_by_id(tool_id)
    if tool:
        database.return_tool(tool_id)
        flash(f"'{database.display_name(dict(tool))}' marked as returned.", "success")
    else:
        flash("Tool not found.", "error")

    return redirect(url_for("admin.admin_panel") + "#checkouts")


@admin_bp.route("/admin/reset", methods=["POST"])
def admin_reset_db():
    if "user" not in session or not _is_admin():
        return redirect(url_for("admin.admin_panel"))

    database.reset_database()
    session.clear()
    flash("Database has been reset. All tools and records have been cleared.", "success")
    return redirect(url_for("login.login"))
