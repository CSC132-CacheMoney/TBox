from flask import Flask, render_template, request, redirect, url_for, session
import database  # your db module

app = Flask(__name__)
app.secret_key = "your_secret_key"

# LOGIN — matches s10000 (Login screen)
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        # Validation: 2–10 characters (matches your design's validation config)
        if username and 2 <= len(username) <= 10:
            session["user"] = username
            return redirect(url_for("dashboard"))
    return render_template("GUI/templates/login.htm")

# DASHBOARD — matches s10011 (Dashboard screen)
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", user=session["user"])

# INVENTORY — matches s10069 (Inventory_Screen)
@app.route("/inventory")
def inventory():
    if "user" not in session:
        return redirect(url_for("login"))
    tools = database.get_all_tools()
    return render_template("inventory.html", tools=tools)

# REGISTER TOOL — matches s10070 (Register_Tool)
@app.route("/register", methods=["GET", "POST"])
def register_tool():
    if "user" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        tool_name = request.form.get("tool_name")
        rfid_tag  = request.form.get("rfid_tag")
        database.register_tool(tool_name, rfid_tag)
        return redirect(url_for("inventory"))
    return render_template("register.html")

# RETIRE TOOL — matches s10071 (Retire_Tool)
@app.route("/retire", methods=["GET", "POST"])
def retire_tool():
    if "user" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        rfid_tag = request.form.get("rfid_tag")
        database.retire_tool(rfid_tag)
        return redirect(url_for("inventory"))
    return render_template("retire.html")

# LOGOUT — matches the mdi-exit-to-app icon on Dashboard
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)