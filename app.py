from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Use a secret key for session management

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client['todo_db']
users_collection = db['users']
tasks_collection = db['tasks']

# Helper function to get user tasks
def get_user_tasks(user_id):
    return list(tasks_collection.find({"user_id": user_id}))

# Routes
@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("task_dashboard"))

# Sign Up Route
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password)

        # Check if the username already exists
        if users_collection.find_one({"username": username}):
            flash("User already exists!")
            return redirect(url_for("signup"))
        
        # Create a new user with hashed password
        users_collection.insert_one({"username": username, "password": hashed_password})
        flash("Account created successfully!")
        return redirect(url_for("login"))
    
    return render_template("signup.html")

# Login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Check if the user exists in the database
        user = users_collection.find_one({"username": username})

        if not user:
            flash("User not found!")
            return redirect(url_for("login"))

        # Check if the 'password' key exists
        if "password" not in user:
            flash("Error: No password found for this user.")
            return redirect(url_for("login"))

        # Check if the password is correct
        if not check_password_hash(user["password"], password):
            flash("Incorrect password!")
            return redirect(url_for("login"))

        # If login is successful, set up the session
        session["user_id"] = str(user["_id"])
        session["username"] = username
        return redirect(url_for("task_dashboard"))
    
    return render_template("login.html")

# Task Dashboard Route
@app.route("/tasks")
def task_dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    tasks = get_user_tasks(session["user_id"])
    return render_template("task_dashboard.html", tasks=tasks, username=session["username"])

# Task Management Routes
@app.route("/tasks/add", methods=["POST"])
def add_task():
    if "user_id" not in session:
        return redirect(url_for("login"))
    title = request.form["title"]
    task_data = {
        "user_id": session["user_id"],
        "title": title,
        "completed": False
    }
    tasks_collection.insert_one(task_data)
    return redirect(url_for("task_dashboard"))


@app.route("/tasks/<task_id>", methods=["GET", "POST", "DELETE"])
def task_detail(task_id):
    task = tasks_collection.find_one({"_id": task_id})
    if request.method == "POST":
        tasks_collection.update_one({"_id": task_id}, {"$set": {"completed": True}})
        return redirect(url_for("congratulations", task_id=task_id))
    elif request.method == "DELETE":
        tasks_collection.delete_one({"_id": task_id})
        return redirect(url_for("task_dashboard"))
    return render_template("task_detail.html", task=task)

@app.route("/tasks/complete/<task_id>", methods=["POST"])
def mark_task_completed(task_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    tasks_collection.update_one({"_id": task_id}, {"$set": {"completed": True}})
    return redirect(url_for("task_dashboard"))

@app.route("/tasks/completed/<task_id>")
def congratulations(task_id):
    task = tasks_collection.find_one({"_id": task_id})
    return render_template("congrats.html", task=task)

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    user = users_collection.find_one({"_id": session["user_id"]})

    if request.method == "POST":
        new_username = request.form["username"]
        new_password = request.form["password"]
        hashed_password = generate_password_hash(new_password)

        # Update username and password in the database
        users_collection.update_one({"_id": session["user_id"]}, {
            "$set": {"username": new_username, "password": hashed_password}
        })
        
        session["username"] = new_username  # Update session data
        flash("Settings updated successfully!")
        return redirect(url_for("task_dashboard"))

    return render_template("settings.html", user=user)

# Logout Route
@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("username", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
