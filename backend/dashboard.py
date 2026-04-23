from flask import Blueprint, render_template, redirect, url_for, session
import database

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect(url_for("login.login"))

    

    return render_template(
        "dashboard.html",
        user=session["user"],
        #overdue=overdue,
        #overdue_count=len(overdue)
    )