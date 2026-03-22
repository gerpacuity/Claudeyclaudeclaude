"""Google OAuth authentication."""

import os
import json

import requests
from flask import Blueprint, redirect, url_for, session, request, flash, current_app
from flask_login import login_user, logout_user, login_required

from .models import db, User

auth_bp = Blueprint("auth", __name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@auth_bp.route("/login")
def login():
    from flask import render_template
    if not current_app.config["GOOGLE_CLIENT_ID"]:
        flash("Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET env vars.", "error")
        return render_template("login.html")
    return render_template("login.html")


@auth_bp.route("/login/google")
def login_google():
    client_id = current_app.config["GOOGLE_CLIENT_ID"]
    if not client_id:
        flash("Google OAuth not configured.", "error")
        return redirect(url_for("auth.login"))

    redirect_uri = url_for("auth.google_callback", _external=True)
    scope = "openid email profile"
    state = os.urandom(16).hex()
    session["oauth_state"] = state

    auth_url = (
        f"{GOOGLE_AUTH_URL}?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope={scope}&"
        f"state={state}&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    return redirect(auth_url)


@auth_bp.route("/login/google/callback")
def google_callback():
    if request.args.get("state") != session.pop("oauth_state", None):
        flash("Invalid OAuth state.", "error")
        return redirect(url_for("auth.login"))

    code = request.args.get("code")
    if not code:
        flash("Login cancelled.", "error")
        return redirect(url_for("auth.login"))

    # Exchange code for token
    token_data = requests.post(GOOGLE_TOKEN_URL, data={
        "code": code,
        "client_id": current_app.config["GOOGLE_CLIENT_ID"],
        "client_secret": current_app.config["GOOGLE_CLIENT_SECRET"],
        "redirect_uri": url_for("auth.google_callback", _external=True),
        "grant_type": "authorization_code",
    }).json()

    access_token = token_data.get("access_token")
    if not access_token:
        flash("Failed to get access token.", "error")
        return redirect(url_for("auth.login"))

    # Get user info
    userinfo = requests.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    ).json()

    google_id = userinfo["id"]
    user = User.query.filter_by(google_id=google_id).first()

    if not user:
        user = User(
            google_id=google_id,
            email=userinfo.get("email", ""),
            name=userinfo.get("name", "User"),
            avatar_url=userinfo.get("picture"),
        )
        db.session.add(user)
        db.session.commit()

    login_user(user)
    return redirect(url_for("views.dashboard"))


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    if current_app.config.get("DEV_MODE"):
        return redirect(url_for("views.dashboard"))
    return redirect(url_for("auth.login"))
