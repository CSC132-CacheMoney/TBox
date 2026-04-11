from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import TBox.backend.pico_Reader as reader
import database
 
register_bp = Blueprint("register", __name__)
 
 
@register_bp.route("/register", methods=["GET", "POST"])
def register_tool():
    """
    Register Tool screen (s10070).
    - GET:  Show the registration form (tool name, condition, category).
    - POST: Validate inputs and add the new tool to the database.
            RFID tag is optional here — it can be assigned later via scanner.
    """
    if "user" not in session:
        return redirect(url_for("login.login"))
 
    if request.method == "POST":
        tool_name = request.form.get("tool_name", "").strip().lower().capitalize()
        condition = request.form.get("condition", "Good")
        category  = request.form.get("category",  "Hand Tool")
        rfid_tag  = reader.write_rfid_tag(reader.init_rfid())  # Attempt to write a new RFID tag; returns None if failed
 
        # Validate
        if not tool_name:
            flash("Please enter a tool name.", "error")
            return render_template("register.html",
                                   condition=condition,
                                   category=category)
 
        try:
            database.register_tool(
                name=tool_name,
                rfid_tag=rfid_tag,
                category=category,
                condition=condition
            )
            flash(f"'{tool_name}' registered successfully.", "success")
            return redirect(url_for("inventory.inventory"))
 
        except ValueError as e:
            # Duplicate RFID tag
            flash(str(e), "error")
 
    return render_template("register.html")