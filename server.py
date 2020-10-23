#!/usr/bin/env python3.8

# MIT License
#
# Copyright (c) 2020 TheCoder777
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


# load system modules
import bcrypt
import io
import os
import re
import sys
import time
import functools

#  flask modules and extensions
from flask import Flask, render_template, request, redirect, send_file, session, url_for
from flask_session import Session

#  WSGI server for better performance
from gevent.pywsgi import WSGIServer

# load internal modules
from defines.colors import RESET, BOLD, ERROR, WARNING, SUCCESS
from defines import paths
from defines import messages
from handlers import pdfhandler, todolisthandler, dbhandler
from models.message import Message


def checkup():
    """
    Global checkup for all files and dirs
    If this doesn't succeed, the server will NOT start!
    """

    start_time = time.time()
    console = BOLD + "[CHECKUP] " + RESET
    print()

    if not os.path.isdir(paths.TMP_PATH):
        print(console + f"Temporary save directory {paths.TMP_PATH} doesn't exist...", end="")
        os.mkdir(paths.TMP_PATH)
        print(SUCCESS + "created!" + RESET)
    else:
        print(console + SUCCESS + "Temporary directory found!" + RESET)

    if not os.path.isdir(paths.COOKIE_PATH):
        print(console + f"Cookie directory {paths.COOKIE_PATH} doesn't exist...", end="")
        os.mkdir(paths.COOKIE_PATH)
        print(SUCCESS + "created!" + RESET)
    else:
        print(console + SUCCESS + "Cookie directory found!" + RESET)

    if not os.path.isdir(paths.USER_PATH):
        print(console + f"User directory {paths.USER_PATH} doesn't exist...", end="")
        os.mkdir(paths.USER_PATH)
        print(SUCCESS + "created!" + RESET)
    else:
        print(console + SUCCESS + "User directory found!" + RESET)

    if not os.path.isdir(paths.DB_PATH):
        print(console + f"DB directory {paths.DB_PATH} doesn't exist...", end="")
        os.mkdir(paths.DB_PATH)
        print(SUCCESS + "created!" + RESET)
    else:
        print(console + SUCCESS + "DB directory found!" + RESET)

    if not os.path.exists(paths.PDF_TEMPLATE_PATH):
        print(console + ERROR + "PDF Template not found! Please add a pdf template!" + RESET)
        sys.exit(1)
    else:
        print(console + SUCCESS + "PDF Template found!" + RESET)

    if not os.path.exists(paths.TODOLIST_TEMPLATE_PATH):
        print(console + ERROR + "Todolist template not found! Please add a todolist template!" + RESET)
        sys.exit(1)
    else:
        print(console + SUCCESS + "Todolist template found!" + RESET)

    # garbadge cleaning (delete all pdf in tmp file)
    filelist = [f for f in os.listdir(paths.TMP_PATH) if f.endswith(".pdf")]
    if filelist:
        print(console + "Cleaning cache...")
        for f in filelist:
            print(WARNING + "\tremoving: " + os.path.join(paths.TMP_PATH, f) + "..." + RESET, end="")
            os.remove(os.path.join(paths.TMP_PATH, f))
            print(SUCCESS + "done!" + RESET)
    else:
        print(console + SUCCESS + "Cache is clean!" + RESET)

    # Calculate time difference (just because we can)
    diff = time.time() - start_time

    print(console + BOLD + SUCCESS + f"Checkup finished succuessfully in {diff:.4f} seconds!\n" + RESET)


def login_required(func):
    """
    Decorator for pages that need a login
    """
    @functools.wraps(func)
    def login_wrapper(*args, **kwargs):
        value = func(*args, **kwargs)
        if not session.get("user"):
            return redirect(url_for("login"))
        return value
    return login_wrapper()


app = Flask(__name__)


def writepdf(data, uinput):
    packet = io.BytesIO()
    packet = pdfhandler.draw(data, uinput, packet)
    packet.seek(0)
    return pdfhandler.compile(packet)


def write_many_pdfs():
    packet = io.BytesIO()
    if not "ContentDB" in globals():
        ContentDB = dbhandler.ContentDB(session["user"].id)
    content = ContentDB.get_content()
    return pdfhandler.create_many(content)


@app.route("/")
def index():
    if not session.get("mode"):
        session["mode"] = "Dark"
    if session.get("user"):
        return redirect("user")
    else:
        return render_template("index.html")


@app.route("/edit")
def edit():
    if session.get("user"):
        data = UserDB.get_user_data(session.get("user"))
    else:
        data = confighandler.parse_config()

    if request.args.get("id"):
        if not "ContentDB" in globals():
            ContentDB = dbhandler.ContentDB(session["user"].id)
        data = ContentDB.get_content_by_id(request.args.get("id"))
        data = list(data)
        data.pop(0)
        return render_template("edit_custom.html", data=data)
    start_date, end_date = pdfhandler.get_date(kw=data["kw"], type="server", nr=data["nr"], year=data["year"])
    data["sign_date"] = pdfhandler.get_a_date(type="html")
    return render_template("edit.html", data=data, start_date=start_date, end_date=end_date)


@app.route("/edit", methods=["POST"])
def get_and_return():
    if request.method == "POST":
        uinput = dict(request.form.copy())
        if request.form.get("submit"):
            uinput = dict(request.form.copy())
            del uinput["submit"]
            if session.get("user"):
                data = UserDB.get_settings_data(session.get("user"))
            else:
                data = confighandler.parse_config()

            pdf = writepdf(data, uinput)
            # confighandler.add_config_nr()  # only for local usage without users
            UserDB.increase_nr(session.get("user"))
            if not "ContentDB" in globals():
                ContentDB = dbhandler.ContentDB(session["user"].id)
            ContentDB.add_record(uinput, data)
            # TODO: set a mimetype
            # TODO: use a fileobject not a path
            # TODO: set attachment_filename to save_kw_xx.pdf (maybe?)
            return send_file(pdf, as_attachment=True)

        elif request.form.get("refresh"):
            del uinput["refresh"]
            udata = UserDB.get_user_data(session.get("user"))
            start_date, end_date = pdfhandler.get_date(kw=udata["kw"], type="server", nr=uinput["nr"],
                                                       year=uinput["year"])
            return render_template("edit.html", data=data, start_date=start_date, end_date=end_date)

        elif request.form.get("save_custom"):
            data = dict(request.form.copy())
            del data["save_custom"]
            if not "ContentDB" in globals():
                ContentDB = dbhandler.ContentDB(session["user"].id)
            ContentDB.update(list(data.values()), request.args.get("id"))
            return redirect("content-overview")

        if request.form.get("refresh_custom"):
            del uinput["refresh_custom"]
            start_date, end_date = pdfhandler.get_date(kw=uinput["kw"], type="server", nr=uinput["nr"],
                                                       year=uinput["year"])
            uinput = list(uinput.values())
            return render_template("edit_custom.html", data=uinput, start_date=start_date, end_date=end_date)

        else:
            data = dict(request.form.copy())
            udata = UserDB.get_user_data(session.get("user"))
            start_date, end_date = pdfhandler.get_date(kw=udata["kw"], type="server", nr=data["nr"], year=data["year"])
            return render_template("edit.html", data=data, start_date=start_date, end_date=end_date)


@app.route("/settings")
def settings():
    if session.get("user"):
        data = UserDB.get_settings_data(session.get("user"))
    else:
        data = confighandler.parse_config()
    return render_template("settings.html", data=data, action="none")


@app.route("/settings", methods=["POST"])
def get_new_config():
    if request.method == "POST":
        data = dict(request.form.copy())
        if session.get("user"):
            if request.form.get("save"):
                del data["save"]
                if UserDB.update_config(session.get("user"), data):
                    new_data = UserDB.get_settings_data(session.get("user"))
                    return render_template("settings.html", data=new_data, action="success")
                else:
                    return render_template("settings.html", data=data, action="fail")
            else:
                return render_template("settings.html", data=data, action="fail")
        else:
            try:
                if data.get("hard_reset"):
                    confighandler.reset_config()
                    new_data = confighandler.parse_config()
                    return render_template("settings.html", data=new_data, action="success_reset")
                elif data.get("save"):
                    confighandler.update_config(data)
                    new_data = confighandler.parse_config()
                    return render_template("settings.html", data=new_data, action="success")
                else:
                    return render_template("settings.html", data=data, action="fail")
            except KeyError:
                return render_template("settings.html", data=data, action="fail")


# Login/Register related functions


def is_email(email):
    # Email regex (x@x.x where x is element from all characters)
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)


def is_password(pw):
    # Password regex
    # - 8 characters (at least 1 Uppercase)
    # - one number
    # - one special character (from !"#$%&'()*+,-./:;<=>?@[\]\^_`{|}~)
    return re.fullmatch(r"^(?=.*[A-Z])(?=.*[a-z])(?=.*?\d)(?=.*?[!\"#$%&\'()*+,-./:;<=>?@[\]\\^_`{|}~]).{8,}$", pw)


def validate_pw(pw, hashandsalt):
    return bcrypt.checkpw(pw.encode(), hashandsalt)


def hashpw(pw):
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt())


def pws_equal(pw1, pw2):
    if pw1 == pw2:
        return True
    else:
        return False


def check_register_credentials(credentials):
    # List for missing credentials (for the msg system)
    msg = Message()

    # validate name/surname (not empty)
    if not len(credentials["name"]) > 0:
        msg.add(messages.MISSING_NAME)
    if not len(credentials["surname"]) > 0:
        msg.add(messages.MISSING_SURNAME)

    # Check if email exists
    if not len(credentials["email"]) > 0:
        msg.add(messages.MISSING_EMAIL)

    # check email with regex
    # TODO: check if the email is already used in db
    elif not is_email(credentials["email"]):
        msg.add(messages.INVALID_EMAIL)

    # check password match
    if not is_password(credentials["password"]):
        msg.add(messages.UNFULFILLED_PASSWORD_REQUIREMENTS)

    # check if passwords are equal
    if not pws_equal(credentials["password"], credentials["password_re"]):
        msg.add(messages.PASSWORD_MISSMATCH)

    return msg


def check_login_credentials(credentials):
    msg = Message()

    if not len(credentials["email"]) > 0:
        msg.add(messages.MISSING_EMAIL)

    elif not is_email(credentials["email"]):
        msg.add(messages.INVALID_EMAIL)

    if not len(credentials["password"]) > 0:
        msg.add(messages.MISSING_PASSWORD)

    return msg


# REGISTER


@app.route("/register")
def register():
    return render_template("security/register.html")


@app.route("/register", methods=["POST"])
def get_user():
    # Check if the register button is pressed (this will be a 'next' button soon)
    if request.form.get("register"):
        # copy the user credentials to a python dict and check them
        credentials = dict(request.form.copy())
        msg = check_register_credentials(credentials)
        if len(msg.messages) == 0:
            # create a password hash
            pwd_and_salt = hashpw(request.form["password"])
            session["user"] = UserDB.new_user(credentials, pwd_and_salt)
            # TODO: move df initalization to /todolist
            global df
            df = todolisthandler.open_todolist(session["user"].id)
            return redirect(url_for("user"))
        else:
            return render_template("security/register.html", data=credentials, msg=msg.get())
    # Check if the "Use as guest" button is pressed
    elif request.form.get("use_as_guest"):
        return redirect(url_for("edit"))


# LOGIN


@app.route("/login")
def login():
    return render_template("security/login.html")


@app.route("/login", methods=["POST"])
def user_login():
    # Check if the Login Button is pressed
    if request.form.get("login"):
        # copy the user credentials to a python dict and check them
        credentials = dict(request.form.copy())
        msg = check_login_credentials(credentials)
        if len(msg.messages) == 0:
            hash_and_salt = UserDB.get_pw(credentials["email"])
            # validate password with hash from db
            if not validate_pw(credentials["password"], hash_and_salt):
                msg.add(messages.INVALID_PASSWORD)
                return render_template("security/login.html", data=credentials, msg=msg.get())
            # Login user
            session["user"] = UserDB.get_user(credentials["email"])
            return redirect(url_for("user"))
        return render_template("security/login.html", data=credentials, msg=msg.get())
    # Check if the "Use as guest" button is pressed
    elif request.form.get("use_as_guest"):
        return redirect(url_for("edit"))
    # Check if the "Forgot password" button is pressed
    elif request.form.get("forgot_password"):
        return redirect(url_for("forgot_password"))


@app.route("/user")
def user():
    if session.get("user"):
        return render_template("user.html")
    else:
        redirect(url_for("index"))


@app.route("/logout")
def logout():
    # Logout user
    del session["user"]
    return redirect(url_for("index"))


@app.route("/forgot-password")
def forgot_password():
    return render_template("security/forgot_password.html")


@app.route("/change-password")
def change_password():
    return render_template("security/change_password.html")


@app.route("/change-mode")
def change_mode():
    if session["mode"] == "Dark":
        session["mode"] = "Light"
        return redirect(request.referrer)
    else:
        session["mode"] = "Dark"
        return redirect(request.referrer)


@app.route("/todolist")
def todolist():
    if session.get("user"):
        df = todolisthandler.open_todolist(session["user"].id)
        return render_template("todolist.html", data=df)
    else:
        return render_template("index.html", notify="login_required")


@app.route("/todolist", methods=["POST"])
def save_todos():
    if session.get("user"):
        if not "df" in globals():
            df = todolisthandler.open_todolist(session["user"].id)
        data = dict(request.form.copy())
        # TODO: move this to todolisthandler
        if data.get("save"):
            del data["save"]

            # reset all
            for i in range(len(df.columns)):
                df[i]["done"] = False
                for j in range(len(df[i]["blocks"])):
                    df[i]["blocks"][j]["done"] = False
                    for k in range(len(df[i]["blocks"][j]["body"])):
                        df[i]["blocks"][j]["body"][k]["done"] = False

            # insert only returned
            for key in data.keys():
                if len(key) == 1:
                    key = int(key)
                    df[key]["done"] = True
                    for j in range(len(df[key]["blocks"])):
                        df[key]["blocks"][j]["done"] = True
                        for k in range(len(df[key]["blocks"][j]["body"])):
                            df[key]["blocks"][j]["body"][k]["done"] = True

                elif len(key) == 3:
                    l1, l2 = key.split(".")
                    l1, l2 = int(l1), int(l2)
                    df[l1]["blocks"][l2]["done"] = True
                    for k in range(len(df[l1]["blocks"][l2]["body"])):
                        df[l1]["blocks"][l2]["body"][k]["done"] = True

                elif len(key) == 5:
                    l1, l2, l3 = key.split(".")
                    l1, l2, l3 = int(l1), int(l2), int(l3)
                    df[l1]["blocks"][l2]["body"][l3]["done"] = True

            todolisthandler.save_todolist(session["user"].id, df)
            df = todolisthandler.open_todolist(session["user"].id)
            return render_template("todolist.html", data=df, notify="success")
        else:
            df = todolisthandler.open_todolist(session["user"].id)
            return render_template("todolist.html", data=df, notify="fail")
    else:
        return render_template("index.html", notify="login_required")


@app.route("/content-overview")
def content_overview():
    if session.get("user"):
        if not session.get("content_mode"):
            session["content_mode"] = "cards"  # set default, read from Userdb later
        if not "ContentDB" in globals():
            ContentDB = dbhandler.ContentDB(session["user"].id)
        content = ContentDB.get_content()
        return render_template("content_overview.html", mode=session.get("content_mode"), content=content)

    else:
        return render_template("index.html", notify="login_required")


@app.route("/content-overview", methods=["POST"])
def export_all():
    if session.get("user"):
        if request.form.get("export"):
            pdf = write_many_pdfs()
            return send_file(pdf, as_attachment=True)
    else:
        return render_template("index.html", notify="login_required")


# TODO: add a @app.errorhandler(404) page

if __name__ == "__main__":
    HOST = 'localhost'
    PORT = 8000
    SESSION_TYPE = "filesystem"
    SESSION_FILE_DIR = paths.COOKIE_PATH
    app.config.from_object(__name__)
    Session(app)
    checkup()
    UserDB = dbhandler.UserDB()
    if len(sys.argv) > 1:
        if sys.argv[1] in ["--debug", "debug", "-d", "d"]:
            app.run(host=HOST, port=PORT, debug=True)  # for debugging
    else:
        print(f"\nRunning on http://{HOST}:{PORT}/\n")
        server = WSGIServer((HOST, PORT), app)
        server.serve_forever()
