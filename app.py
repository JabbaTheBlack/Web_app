import os
import requests
from datetime import datetime
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

#All of the templates and .py files have been commented by Chatgpt
# Import helpers from helpers.py
from helpers import apology, login_required, usd, lookup

# Configure Flask app
app = Flask(__name__)
app.jinja_env.filters["usd"] = usd  # Register the usd filter for Jinja templates
app.config["SESSION_PERMANENT"] = False  # Session is not permanent
app.config["SESSION_TYPE"] = "filesystem"  # Session data stored on the filesystem
Session(app)  # Initialize session management

# Connect to SQLite database
db = SQL("sqlite:///database.db")

# Function to set response headers to prevent caching
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Homepage route
@app.route("/")
@login_required  # Requires user to be logged in
def index():
    return render_template("index.html")  # Render index.html template

# Login route
@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()  # Clear any existing session data

    if request.method == "POST":  # If form submitted
        username = request.form.get("username")
        password = request.form.get("password")

        if not username:
            return apology("Must provide a username", 400)
        elif not password:
            return apology("Must provide a password", 400)

        # Check if username exists in the database
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        # Check if username and password match
        if not rows or not check_password_hash(rows[0]["password"], password):
            return apology("Invalid username and/or password", 400)

        # Store user ID in session
        session["user_id"] = rows[0]["id"]

        return redirect("/")  # Redirect to homepage after successful login

    else:
        return render_template("login.html")  # Render login page

# Registration route
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":  # If form submitted
        # Extract form data
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        # Validate form data
        if not username:
            return apology("Must provide a username", 400)
        elif not email:
            return apology("Must provide an email", 400)
        elif not password:
            return apology("Must provide a password", 400)
        elif password != confirm_password:
            return apology("Passwords do not match", 400)

        # Check if username or email already exists in the database
        existing_user = db.execute("SELECT * FROM users WHERE username = ? OR email = ?", username, email)
        if existing_user:
            return apology("User with this username or email already exists", 400)

        # Insert new user into the database
        hashed_password = generate_password_hash(password)
        db.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", username, email, hashed_password)

        # Redirect to login page after successful registration
        return redirect("/login")

    else:
        return render_template("register.html")  # Render registration page

# Search route
@app.route("/search", methods=["GET", "POST"])
@login_required  # Requires user to be logged in
def search():
    return render_template("search.html")  # Render search page

# Route to get stock price
@app.route("/stock_price", methods=["POST"])
@login_required  # Requires user to be logged in
def stock_price():
    symbol = request.form.get("symbol")
    stock_data = lookup(symbol)
    if stock_data:
        price = usd(stock_data["price"])
        return render_template("index.html", symbol=symbol, price=price)  # Render index.html with symbol and price
    else:
        return "Stock symbol not found or error occurred."

# Route to add a stock to the portfolio
@app.route("/add_to_portfolio", methods=["POST"])
@login_required  # Requires user to be logged in
def add_to_portfolio():
    if request.method == "POST":
        symbol = request.form.get("symbol")
        stock_data = lookup(symbol)
        quantity = request.form.get("quantity")
        if stock_data:
            price = stock_data["price"] * int(quantity)
            user_id = session["user_id"]
            db.execute("INSERT INTO portfolios (user_id, symbol, price, purchase_date, quantity) VALUES (?, ?, ?, ?, ?)",
                       user_id, symbol, price, datetime.now(), quantity)
            return redirect("/portfolio")  # Redirect to portfolio page after adding the stock
        else:
            return apology("Stock symbol not found", 404)
    else:
        return apology("Method not allowed", 405)

# Route to view user's portfolio
@app.route("/portfolio", methods=["GET", "POST"])
@login_required  # Requires user to be logged in
def portfolio():
    portfolio_data = db.execute("SELECT * FROM portfolios WHERE user_id = ?", session["user_id"])
    return render_template("portfolio.html", portfolio_data=portfolio_data)  # Render portfolio page

# Account route
@app.route("/account", methods=["GET", "POST"])
@login_required  # Requires user to be logged in
def account():
    return render_template("account.html")  # Render account page

# Route to change password
@app.route("/change_password", methods=["GET", "POST"])
@login_required  # Requires user to be logged in
def change_password():
    if request.method == "POST":
        old_password = request.form.get("old_password")
        current_password = db.execute("SELECT password FROM users WHERE id = ?", session["user_id"])

        if not check_password_hash(current_password[0]["password"], old_password):
            return apology("Incorrect password", 400)

        new_password = generate_password_hash(request.form.get("new_password"))

        if check_password_hash(current_password[0]["password"], new_password):
            return apology("New password cannot be the same as the old one", 400)

        db.execute("UPDATE users SET password = ? WHERE id = ?", new_password, session["user_id"])

    return render_template("password.html")  # Render password change page

# Route to logout
@app.route("/logout")
def logout():
    session.clear()  # Clear session data
    return redirect("/login")  # Redirect to the login page

if __name__ == '__main__':
    app.run(debug=True)  # Run the Flask app
