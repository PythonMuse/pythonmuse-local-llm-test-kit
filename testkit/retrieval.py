"""Permission-aware document loading.

The rule this module enforces is the one from the article: access is decided
*before* the model sees anything. A document reaches the prompt only if the
manifest lists it for this engagement. Being saved in the engagement's folder
is not permission -- the misfiled Harrowgate Foods term sheet in S01 proves it.
"""

import csv
from pathlib import Path


def load_manifest(manifest_path):
    """Read engagements/manifest.csv into a list of dicts."""
    with open(manifest_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def engagement_ids(manifest, set_name):
    """Engagement IDs in a set ('practice' or 'scoring'), in manifest order."""
    seen = []
    for row in manifest:
        if row["set"] == set_name and row["engagement_id"] not in seen:
            seen.append(row["engagement_id"])
    return seen


def engagement_info(manifest, engagement_id):
    """Client and series name for one engagement."""
    rows = [r for r in manifest if r["engagement_id"] == engagement_id]
    if not rows:
        raise KeyError(f"Engagement {engagement_id} is not in the manifest.")
    clients = {r["client"] for r in rows}
    if len(clients) != 1:
        # One engagement, one client. Anything else is a cross-client leak
        # waiting to happen, so stop rather than guess.
        raise PermissionError(
            f"Engagement {engagement_id} lists documents for more than one client: "
            f"{sorted(clients)}")
    return {"client": rows[0]["client"], "series_name": rows[0]["series_name"],
            "set": rows[0]["set"]}


def authorized_documents(manifest, engagement_id, engagements_root):
    """Return {document_id: text} for the documents this engagement is allowed
    to use -- and nothing else.

    Raises PermissionError if the manifest points outside the engagement's own
    folder or mixes clients.
    """
    engagement_info(manifest, engagement_id)  # validates the single-client rule
    root = Path(engagements_root).resolve()
    rows = [r for r in manifest if r["engagement_id"] == engagement_id]
    folders = {(root / r["path"]).resolve().parent for r in rows}
    if len(folders) != 1:
        raise PermissionError(
            f"Engagement {engagement_id} pulls documents from more than one folder.")

    docs = {}
    for r in rows:
        path = (root / r["path"]).resolve()
        if root not in path.parents:
            raise PermissionError(f"{r['path']} is outside the engagements folder.")
        docs[r["document_id"]] = path.read_text(encoding="utf-8")
    return docs
