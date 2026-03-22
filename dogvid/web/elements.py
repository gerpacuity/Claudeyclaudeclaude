"""Element library — create, browse, preview reusable 60-90s clips."""

import os
import threading

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    current_app, jsonify,
)
from flask_login import login_required, current_user

from .models import db, Element
from ..scenes import SCENE_GENERATORS, SceneConfig
from ..audio import AUDIO_GENERATORS, AudioConfig
from ..science import RESOLUTION_PRESETS, DEFAULT_FPS

elements_bp = Blueprint("elements", __name__)

SCENE_DESCRIPTIONS = {
    "floating_orbs": "Blue/yellow orbs drifting across a dark background",
    "wave_pattern": "Ocean-like sine wave ripples in blue palette",
    "gradient_sweep": "Rotating blue-to-yellow gradient sweep",
    "bouncing_shapes": "Shapes bouncing around, mimicking small animal movement",
    "starfield": "Twinkling stars on deep blue background",
    "lava_lamp": "Slow-moving blue/yellow blobs",
}

AUDIO_DESCRIPTIONS = {
    "calming_drone": "Layered solfeggio frequencies with gentle modulation",
    "nature_ambience": "Synthesized rain, wind, and distant bird tones",
    "heartbeat_rhythm": "Slow heartbeat at ~60 BPM with sub-bass",
    "binaural_relaxation": "Binaural beats creating theta-wave pulsing",
}


@elements_bp.route("/")
@login_required
def index():
    filter_type = request.args.get("type", "all")
    query = Element.query.filter_by(user_id=current_user.id)
    if filter_type in ("scene", "audio"):
        query = query.filter_by(element_type=filter_type)
    elements = query.order_by(Element.created_at.desc()).all()
    return render_template("elements/index.html",
        elements=elements,
        filter_type=filter_type,
        scene_generators=SCENE_GENERATORS,
        audio_generators=AUDIO_GENERATORS,
    )


@elements_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        element_type = request.form.get("element_type")
        generator_type = request.form.get("generator_type")
        duration = int(request.form.get("duration", 60))
        resolution = request.form.get("resolution", "1080p")
        mood = request.form.get("mood", "relaxed")

        duration = max(30, min(90, duration))

        if not name:
            name = f"{generator_type.replace('_', ' ').title()} {duration}s"

        element = Element(
            user_id=current_user.id,
            name=name,
            element_type=element_type,
            generator_type=generator_type,
            duration_sec=duration,
            resolution=resolution,
            params_json='{"mood": "' + mood + '"}',
            status="pending",
        )
        db.session.add(element)
        db.session.commit()

        flash(f"Element '{name}' created. Starting render...", "success")
        _start_render(current_app._get_current_object(), element.id)
        return redirect(url_for("elements.detail", element_id=element.id))

    return render_template("elements/create.html",
        scene_generators=SCENE_GENERATORS,
        scene_descriptions=SCENE_DESCRIPTIONS,
        audio_generators=AUDIO_GENERATORS,
        audio_descriptions=AUDIO_DESCRIPTIONS,
        resolutions=list(RESOLUTION_PRESETS.keys()),
    )


@elements_bp.route("/<int:element_id>")
@login_required
def detail(element_id):
    element = Element.query.filter_by(id=element_id, user_id=current_user.id).first_or_404()
    return render_template("elements/detail.html", element=element)


@elements_bp.route("/<int:element_id>/delete", methods=["POST"])
@login_required
def delete(element_id):
    element = Element.query.filter_by(id=element_id, user_id=current_user.id).first_or_404()
    if element.file_path and os.path.exists(element.file_path):
        os.remove(element.file_path)
    if element.thumbnail_path and os.path.exists(element.thumbnail_path):
        os.remove(element.thumbnail_path)
    db.session.delete(element)
    db.session.commit()
    flash("Element deleted.", "success")
    return redirect(url_for("elements.index"))


@elements_bp.route("/<int:element_id>/rerender", methods=["POST"])
@login_required
def rerender(element_id):
    element = Element.query.filter_by(id=element_id, user_id=current_user.id).first_or_404()
    element.status = "pending"
    db.session.commit()
    _start_render(current_app._get_current_object(), element.id)
    flash("Re-rendering element...", "success")
    return redirect(url_for("elements.detail", element_id=element.id))


@elements_bp.route("/<int:element_id>/status")
@login_required
def status(element_id):
    element = Element.query.filter_by(id=element_id, user_id=current_user.id).first_or_404()
    return jsonify({"status": element.status, "file_exists": element.file_exists})


def _start_render(app, element_id):
    """Kick off element rendering in a background thread."""
    thread = threading.Thread(target=_render_element, args=(app, element_id), daemon=True)
    thread.start()


def _render_element(app, element_id):
    """Render a single element (scene or audio clip)."""
    import subprocess

    with app.app_context():
        element = db.session.get(Element, element_id)
        if not element:
            return

        element.status = "rendering"
        db.session.commit()

        media_dir = app.config["MEDIA_DIR"]
        params = element.params

        try:
            if element.element_type == "scene":
                res = RESOLUTION_PRESETS.get(element.resolution, (1920, 1080))
                cfg = SceneConfig(
                    scene_type=element.generator_type,
                    duration_sec=element.duration_sec,
                    width=res[0],
                    height=res[1],
                    fps=DEFAULT_FPS,
                )
                generator = SCENE_GENERATORS[element.generator_type]
                cmd = generator(cfg)
                out_path = os.path.join(media_dir, "elements", "scenes", f"element_{element.id}.mp4")
                full_cmd = cmd + [out_path]

                result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=600)
                if result.returncode != 0:
                    element.status = "failed"
                    db.session.commit()
                    return

                element.file_path = out_path

                # Generate thumbnail
                thumb_path = os.path.join(media_dir, "thumbnails", f"element_{element.id}.jpg")
                subprocess.run([
                    "ffmpeg", "-y", "-i", out_path,
                    "-vf", "select=eq(n\\,30),scale=320:-1",
                    "-frames:v", "1", thumb_path,
                ], capture_output=True, timeout=30)
                if os.path.exists(thumb_path):
                    element.thumbnail_path = thumb_path

            elif element.element_type == "audio":
                mood = params.get("mood", "relaxed")
                cfg = AudioConfig(
                    duration_sec=element.duration_sec,
                    mood=mood,
                    volume=0.3,
                )
                generator = AUDIO_GENERATORS[element.generator_type]
                cmd = generator(cfg)
                out_path = os.path.join(media_dir, "elements", "audio", f"element_{element.id}.m4a")
                full_cmd = cmd + [out_path]

                result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=600)
                if result.returncode != 0:
                    element.status = "failed"
                    db.session.commit()
                    return

                element.file_path = out_path

            element.status = "ready"
            db.session.commit()

        except Exception:
            element.status = "failed"
            db.session.commit()
