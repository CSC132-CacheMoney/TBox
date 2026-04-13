from flask import Blueprint, render_template, request, redirect, url_for, session
import database
 
login_bp = Blueprint("login", __name__)
 
 
@login_bp.route("/", methods=["GET", "POST"])
def login():
    """
    Login screen.
        - GET:  Show the login form.
        - POST: Validate the name (2-10 chars), save to session, log the user,
    then redirect to the dashboard.
    """
    # Already logged in — skip straight to dashboard
    if "user" in session:
        return redirect(url_for("dashboard.dashboard"))
 
    error = None
 
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower().capitalize()
 
        # Validate: 2–10 characters (matches design's TextBox validation)
        if len(username) < 2 or len(username) > 10:
            error = "Name must be between 2 and 10 characters."
        else:
            session["user"] = username
            database.log_user(username)
            return redirect(url_for("dashboard.dashboard"))
 
    return render_template("login.html", error=error)
 
 
@login_bp.route("/logout")
def logout():
    """
    Logout — triggered by the mdi-exit-to-app icon on the dashboard.
    Clears the session and returns to the login screen.
    """
    session.clear()
    return redirect(url_for("login.login"))