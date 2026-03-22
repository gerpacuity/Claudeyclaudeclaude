"""Database models for DogVid web UI."""

import json
import os
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(128), unique=True, nullable=False)
    email = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(256), nullable=False)
    avatar_url = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    elements = db.relationship("Element", backref="owner", lazy="dynamic")
    compositions = db.relationship("Composition", backref="owner", lazy="dynamic")


class Element(db.Model):
    """
    A reusable 60-90 second scene or audio clip.
    This is the atomic unit of content — elements get composed into videos.
    """
    __tablename__ = "elements"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(256), nullable=False)
    element_type = db.Column(db.String(16), nullable=False)  # "scene" or "audio"
    generator_type = db.Column(db.String(64), nullable=False)  # e.g. "floating_orbs"
    duration_sec = db.Column(db.Integer, nullable=False, default=60)
    resolution = db.Column(db.String(16), default="1080p")
    params_json = db.Column(db.Text, default="{}")  # extra generator params
    file_path = db.Column(db.String(512))
    thumbnail_path = db.Column(db.String(512))
    status = db.Column(db.String(16), default="pending")  # pending, rendering, ready, failed
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    @property
    def params(self):
        return json.loads(self.params_json) if self.params_json else {}

    @params.setter
    def params(self, value):
        self.params_json = json.dumps(value)

    @property
    def file_exists(self):
        return self.file_path and os.path.exists(self.file_path)

    @property
    def duration_display(self):
        return f"{self.duration_sec}s"


class Composition(db.Model):
    """A video built from a sequence of reusable elements."""
    __tablename__ = "compositions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(256), nullable=False)
    target_duration_sec = db.Column(db.Integer, default=36000)  # 10h
    mood = db.Column(db.String(32), default="relaxed")
    audio_volume = db.Column(db.Float, default=0.3)
    resolution = db.Column(db.String(16), default="1080p")
    status = db.Column(db.String(16), default="draft")  # draft, rendering, ready, failed
    file_path = db.Column(db.String(512))
    thumbnail_path = db.Column(db.String(512))
    youtube_id = db.Column(db.String(32))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    rendered_at = db.Column(db.DateTime)

    items = db.relationship(
        "CompositionItem", backref="composition",
        order_by="CompositionItem.position", cascade="all, delete-orphan",
    )

    @property
    def unique_duration_sec(self):
        """Total duration of the unique segment before looping."""
        return sum(item.element.duration_sec for item in self.items if item.element)

    @property
    def target_duration_display(self):
        hours = self.target_duration_sec // 3600
        mins = (self.target_duration_sec % 3600) // 60
        if hours:
            return f"{hours}h" if not mins else f"{hours}h {mins}m"
        return f"{mins}m"


class CompositionItem(db.Model):
    """Links an element to a composition at a specific position."""
    __tablename__ = "composition_items"

    id = db.Column(db.Integer, primary_key=True)
    composition_id = db.Column(db.Integer, db.ForeignKey("compositions.id"), nullable=False)
    element_id = db.Column(db.Integer, db.ForeignKey("elements.id"), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)

    element = db.relationship("Element")
