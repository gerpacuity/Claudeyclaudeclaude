"""Video compositions — arrange elements into full videos."""

import os
import shutil
import subprocess
import tempfile
import threading
from datetime import datetime, timezone

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    current_app, jsonify,
)
from flask_login import login_required, current_user

from .models import db, Element, Composition, CompositionItem
from ..science import RESOLUTION_PRESETS
from ..pipeline import (
    concatenate_clips, mix_audio_tracks, merge_video_audio,
    loop_to_duration, generate_thumbnail as gen_thumb,
)

compositions_bp = Blueprint("compositions", __name__)


@compositions_bp.route("/")
@login_required
def index():
    compositions = (
        Composition.query
        .filter_by(user_id=current_user.id)
        .order_by(Composition.created_at.desc())
        .all()
    )
    return render_template("compositions/index.html", compositions=compositions)


@compositions_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        name = request.form.get("name", "").strip() or "Untitled Video"
        target_duration = request.form.get("target_duration", "36000")
        mood = request.form.get("mood", "relaxed")
        volume = float(request.form.get("volume", "0.3"))
        resolution = request.form.get("resolution", "1080p")
        element_ids = request.form.getlist("element_ids")

        comp = Composition(
            user_id=current_user.id,
            name=name,
            target_duration_sec=int(target_duration),
            mood=mood,
            audio_volume=volume,
            resolution=resolution,
            status="draft",
        )
        db.session.add(comp)
        db.session.flush()

        for pos, eid in enumerate(element_ids):
            item = CompositionItem(
                composition_id=comp.id,
                element_id=int(eid),
                position=pos,
            )
            db.session.add(item)

        db.session.commit()
        flash(f"Composition '{name}' created.", "success")
        return redirect(url_for("compositions.detail", comp_id=comp.id))

    scene_elements = (
        Element.query
        .filter_by(user_id=current_user.id, element_type="scene", status="ready")
        .order_by(Element.created_at.desc())
        .all()
    )
    audio_elements = (
        Element.query
        .filter_by(user_id=current_user.id, element_type="audio", status="ready")
        .order_by(Element.created_at.desc())
        .all()
    )
    return render_template("compositions/create.html",
        scene_elements=scene_elements,
        audio_elements=audio_elements,
        resolutions=list(RESOLUTION_PRESETS.keys()),
    )


@compositions_bp.route("/<int:comp_id>")
@login_required
def detail(comp_id):
    comp = Composition.query.filter_by(id=comp_id, user_id=current_user.id).first_or_404()
    scene_items = [item for item in comp.items if item.element.element_type == "scene"]
    audio_items = [item for item in comp.items if item.element.element_type == "audio"]
    return render_template("compositions/detail.html",
        comp=comp, scene_items=scene_items, audio_items=audio_items)


@compositions_bp.route("/<int:comp_id>/update", methods=["POST"])
@login_required
def update(comp_id):
    comp = Composition.query.filter_by(id=comp_id, user_id=current_user.id).first_or_404()
    element_ids = request.form.getlist("element_ids")

    # Clear existing items and rebuild
    CompositionItem.query.filter_by(composition_id=comp.id).delete()
    for pos, eid in enumerate(element_ids):
        item = CompositionItem(composition_id=comp.id, element_id=int(eid), position=pos)
        db.session.add(item)

    comp.name = request.form.get("name", comp.name)
    comp.target_duration_sec = int(request.form.get("target_duration", comp.target_duration_sec))
    comp.mood = request.form.get("mood", comp.mood)
    comp.audio_volume = float(request.form.get("volume", comp.audio_volume))
    comp.resolution = request.form.get("resolution", comp.resolution)
    comp.status = "draft"
    db.session.commit()

    flash("Composition updated.", "success")
    return redirect(url_for("compositions.detail", comp_id=comp.id))


@compositions_bp.route("/<int:comp_id>/render", methods=["POST"])
@login_required
def render(comp_id):
    comp = Composition.query.filter_by(id=comp_id, user_id=current_user.id).first_or_404()
    if not comp.items:
        flash("Add elements before rendering.", "error")
        return redirect(url_for("compositions.detail", comp_id=comp.id))

    comp.status = "rendering"
    db.session.commit()

    thread = threading.Thread(
        target=_render_composition,
        args=(current_app._get_current_object(), comp.id),
        daemon=True,
    )
    thread.start()
    flash("Rendering started! This may take a while.", "success")
    return redirect(url_for("compositions.detail", comp_id=comp.id))


@compositions_bp.route("/<int:comp_id>/delete", methods=["POST"])
@login_required
def delete(comp_id):
    comp = Composition.query.filter_by(id=comp_id, user_id=current_user.id).first_or_404()
    if comp.file_path and os.path.exists(comp.file_path):
        os.remove(comp.file_path)
    if comp.thumbnail_path and os.path.exists(comp.thumbnail_path):
        os.remove(comp.thumbnail_path)
    db.session.delete(comp)
    db.session.commit()
    flash("Composition deleted.", "success")
    return redirect(url_for("compositions.index"))


@compositions_bp.route("/<int:comp_id>/status")
@login_required
def status(comp_id):
    comp = Composition.query.filter_by(id=comp_id, user_id=current_user.id).first_or_404()
    return jsonify({"status": comp.status})


def _render_composition(app, comp_id):
    """Render a composition by assembling its elements."""
    with app.app_context():
        comp = db.session.get(Composition, comp_id)
        if not comp:
            return

        media_dir = app.config["MEDIA_DIR"]
        work_dir = tempfile.mkdtemp(prefix="dogvid_comp_")

        try:
            scene_items = [i for i in comp.items if i.element.element_type == "scene"]
            audio_items = [i for i in comp.items if i.element.element_type == "audio"]

            scene_files = [i.element.file_path for i in scene_items if i.element.file_exists]
            audio_files = [i.element.file_path for i in audio_items if i.element.file_exists]

            if not scene_files:
                comp.status = "failed"
                db.session.commit()
                return

            # Concatenate scene clips
            segment_video = os.path.join(work_dir, "segment_video.mp4")
            if not concatenate_clips(scene_files, segment_video):
                comp.status = "failed"
                db.session.commit()
                return

            # Mix audio if available
            segment_audio = os.path.join(work_dir, "segment_audio.m4a")
            unique_duration = sum(i.element.duration_sec for i in scene_items)
            has_audio = bool(audio_files) and mix_audio_tracks(
                audio_files, unique_duration, segment_audio
            )

            # Merge video + audio
            segment_merged = os.path.join(work_dir, "segment_merged.mp4")
            if has_audio:
                if not merge_video_audio(segment_video, segment_audio, segment_merged):
                    segment_merged = segment_video
            else:
                segment_merged = segment_video

            # Loop to target duration
            final_path = os.path.join(media_dir, "compositions", f"comp_{comp.id}.mp4")
            if comp.target_duration_sec > unique_duration:
                if not loop_to_duration(
                    segment_merged,
                    segment_audio if has_audio else None,
                    comp.target_duration_sec,
                    final_path,
                ):
                    shutil.copy2(segment_merged, final_path)
            else:
                shutil.copy2(segment_merged, final_path)

            comp.file_path = final_path

            # Thumbnail
            thumb_path = os.path.join(media_dir, "thumbnails", f"comp_{comp.id}.jpg")
            subprocess.run([
                "ffmpeg", "-y", "-i", final_path,
                "-vf", "select=eq(n\\,60),scale=640:-1",
                "-frames:v", "1", thumb_path,
            ], capture_output=True, timeout=30)
            if os.path.exists(thumb_path):
                comp.thumbnail_path = thumb_path

            comp.status = "ready"
            comp.rendered_at = datetime.now(timezone.utc)
            db.session.commit()

        except Exception:
            comp.status = "failed"
            db.session.commit()
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
