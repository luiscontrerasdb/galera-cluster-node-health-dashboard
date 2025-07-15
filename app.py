import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from datetime import datetime
import configparser
from galera_checklib import get_cluster_status, repair_node
from userdb import add_user, check_user, get_user, get_auditlog, create_db, log_action

app = Flask(__name__)
app.secret_key = os.environ.get("GALERA_SECRET_KEY", "supersecretkey123")

def load_server_configs():
    parser = configparser.ConfigParser()
    parser.read("servers.cnf")
    servers = []
    for section in parser.sections():
        cfg = dict(parser.items(section))
        cfg["node_label"] = section.replace("node","N")
        servers.append(cfg)
    return servers

@app.route("/")
def index():
    user = None
    if "user" in session:
        user = get_user(session["user"])
    return render_template("index.html", now=datetime.now(), user=user)

@app.route("/status")
def status():
    configs = load_server_configs()
    return jsonify(get_cluster_status(configs))

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        user = check_user(username, password)
        if user:
            session["user"] = username
            log_action(username, "login", "OK")
            return redirect(url_for("index"))
        else:
            error = "Invalid username or password"
    return render_template("login.html", error=error, now=datetime.now())

@app.route("/logout")
def logout():
    username = session.get("user")
    if username:
        log_action(username, "logout", "OK")
    session.clear()
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    success = None
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password")
        password2 = request.form.get("password2")
        role = request.form.get("role", "user")
        if not (first_name and last_name and email and username and password and password2):
            error = "All fields are required"
        elif password != password2:
            error = "Passwords do not match"
        elif get_user(username):
            error = "Username already exists"
        else:
            add_user(username, password, role, first_name, last_name, email)
            log_action(username, "register", f"role={role}")
            success = "User created! You may login now."
            return render_template("register.html", error=None, success=success, now=datetime.now())
    return render_template("register.html", error=error, success=success, now=datetime.now())

@app.route("/auditlog")
def auditlog_view():
    username = session.get("user")
    if not username:
        return redirect(url_for("login"))
    logs = get_auditlog(100)
    return render_template("auditlog.html", logs=logs, now=datetime.now())

@app.route("/node/<nodeid>/fix", methods=["POST"])
def node_fix(nodeid):
    configs = load_server_configs()
    ok, msg = repair_node(nodeid, configs)
    username = session.get("user", "system")
    log_action(username, "fix_node", f"node={nodeid} result={msg}")
    return jsonify({"ok": ok, "message": msg})


@app.route("/nodeevents")
def nodeevents():
    from galera_checklib import get_node_events 
    events = get_node_events()
    return render_template("nodeevents.html", events=events)


if __name__ == "__main__":
    create_db()
    app.run(host="0.0.0.0", port=2000, debug=True)

