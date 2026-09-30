"""Permanent storage for live citizen requests in Google Cloud Firestore (Firebase).

The app ranks projects from a local SQLite working copy, which is fast but is wiped when a free
server restarts. So every live request is also written to Firestore, and on start-up all live
requests are loaded back from Firestore into SQLite. Nothing submitted by a citizen is lost.

Credentials (a Firebase service-account key), in this order:
  FIREBASE_CREDENTIALS   the key file's JSON text (used on the hosting server)
  firebase-key.json      the key file in the project folder (used on a laptop; never committed)
Without either, the app runs on SQLite alone.
"""
import json
import os
from pathlib import Path

COLLECTION = os.environ.get("FIRESTORE_COLLECTION", "requests")
KEY_FILE = Path(__file__).resolve().parent.parent / "firebase-key.json"

_db = None


def init():
    global _db
    info = None
    if os.environ.get("FIREBASE_CREDENTIALS"):
        info = json.loads(os.environ["FIREBASE_CREDENTIALS"])
    elif KEY_FILE.exists():
        info = json.loads(KEY_FILE.read_text(encoding="utf-8"))
    if not info:
        print("Firestore not configured: live requests are kept in SQLite only")
        return
    try:
        from google.cloud import firestore
        from google.oauth2 import service_account

        creds = service_account.Credentials.from_service_account_info(info)
        _db = firestore.Client(project=info["project_id"], credentials=creds)
        print(f"Firestore connected: project {info['project_id']}, collection '{COLLECTION}'")
    except Exception as e:
        print("Firestore unavailable, using SQLite only:", e)
        _db = None


def enabled() -> bool:
    return _db is not None


def save(rec: dict):
    """Write one live request. A Firestore error never stops the citizen's submission."""
    if not _db:
        return
    try:
        _db.collection(COLLECTION).document(rec["id"]).set(rec, timeout=15)
    except Exception as e:
        print("Firestore save failed (kept in SQLite):", e)


def load_all() -> list[dict]:
    if not _db:
        return []
    try:
        return [doc.to_dict() for doc in _db.collection(COLLECTION).stream(timeout=60)]
    except Exception as e:
        print("Firestore load failed:", e)
        return []
