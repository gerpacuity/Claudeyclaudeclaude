"""Main views — dashboard and media serving."""

import os
from flask import Blueprint, render_template, send_from_directory, current_app
from flask_login import login_required, current_user

from .models import db, Element, Composition

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
@login_required
def dashboard():
    elements = Element.query.filter_by(user_id=current_user.id).order_by(Element.created_at.desc()).all()
    compositions = Composition.query.filter_by(user_id=current_user.id).order_by(Composition.created_at.desc()).all()

    scene_count = sum(1 for e in elements if e.element_type == "scene")
    audio_count = sum(1 for e in elements if e.element_type == "audio")
    ready_count = sum(1 for e in elements if e.status == "ready")
    rendering_count = sum(1 for e in elements if e.status == "rendering")
    rendering_count += sum(1 for c in compositions if c.status == "rendering")

    return render_template("dashboard.html",
        elements=elements,
        compositions=compositions,
        scene_count=scene_count,
        audio_count=audio_count,
        ready_count=ready_count,
        rendering_count=rendering_count,
    )


@views_bp.route("/media/<path:filename>")
@login_required
def serve_media(filename):
    return send_from_directory(current_app.config["MEDIA_DIR"], filename)
