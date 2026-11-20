"""Persistent app knowledge and transactional review history."""

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
from uuid import uuid4


class ReviewError(ValueError):
    pass


class StaleReport(ReviewError):
    def __init__(self, latest):
        super().__init__("Only the latest finalized report can apply AI proposals.")
        self.latest = latest


class KnowledgeStore:
    def __init__(self, installation):
        self.path = Path(installation) / "data" / "knowledge" / "knowledge.sqlite3"

    @contextmanager
    def connect(self, write=False):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS entries (
                    id TEXT PRIMARY KEY, app TEXT NOT NULL, name TEXT NOT NULL,
                    description TEXT NOT NULL, steps TEXT NOT NULL, revision TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS reports (
                    id TEXT PRIMARY KEY, path TEXT NOT NULL, finished TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS reviews (
                    report TEXT NOT NULL, request TEXT NOT NULL, generation INTEGER NOT NULL,
                    decision TEXT NOT NULL, draft TEXT NOT NULL, PRIMARY KEY(report, request, generation));
            """)
            if write:
                connection.execute("BEGIN IMMEDIATE")
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _entry(row):
        return dict(row, steps=json.loads(row["steps"])) if row else None

    def entries(self, app=None, query=""):
        with self.connect() as db:
            rows = db.execute("SELECT * FROM entries ORDER BY app, name").fetchall()
        return [self._entry(row) for row in rows
                if (app is None or row["app"].casefold() == app.strip().casefold())
                and query.casefold() in " ".join((row["name"], row["description"],
                                                row["app"] if app is None else "")).casefold()]

    def lookup(self, app, query="", entry_id=""):
        entries = self.entries(app, query)
        if entry_id:
            return next((row for row in entries if row["id"] == entry_id), None)
        return [{key: row[key] for key in ("id", "name", "description")} for row in entries[:20]]

    @staticmethod
    def _save(db, draft, entry_id):
        current = KnowledgeStore._entry(db.execute("SELECT * FROM entries WHERE id=?", (entry_id,)).fetchone())
        expected = draft.get("revision", "")
        if (current["revision"] if current else "") != expected:
            raise ReviewError("The entry changed. Review the current version before saving.")
        if draft["operation"] == "delete":
            if current is None:
                raise ReviewError("The entry was already removed.")
            db.execute("DELETE FROM entries WHERE id=?", (entry_id,))
            return ""
        if not all(draft.get(key, "").strip() for key in ("app", "name", "description")) or not draft.get("steps"):
            raise ReviewError("Application, name, description and at least one step are required.")
        revision = uuid4().hex
        db.execute("INSERT OR REPLACE INTO entries VALUES (?, ?, ?, ?, ?, ?)",
                   (entry_id, draft["app"].strip(), draft["name"].strip(), draft["description"].strip(),
                    json.dumps(draft["steps"], ensure_ascii=False), revision))
        return revision

    def edit(self, draft):
        with self.connect(write=True) as db:
            return self._save(db, draft, draft.get("entryId") or uuid4().hex)

    def register(self, report, path, finished):
        with self.connect(write=True) as db:
            db.execute("INSERT OR IGNORE INTO reports VALUES (?, ?, ?)", (report, str(path), finished))

    @staticmethod
    def _latest(db):
        row = db.execute("SELECT id FROM reports ORDER BY finished DESC, rowid DESC LIMIT 1").fetchone()
        return row["id"] if row else ""

    def report(self, report):
        with self.connect() as db:
            row = db.execute("SELECT path FROM reports WHERE id=?", (report,)).fetchone()
            return (Path(row["path"]) if row else None), self._latest(db)

    def history(self, report, request):
        with self.connect() as db:
            return self._history(db, report, request)

    @staticmethod
    def _history(db, report, request):
        return [dict(row, draft=json.loads(row["draft"])) for row in db.execute(
            "SELECT generation, decision, draft FROM reviews WHERE report=? AND request=? ORDER BY generation",
            (report, request))]

    def review(self, report, proposal, generation, decision, draft=None):
        with self.connect(write=True) as db:
            latest = self._latest(db)
            if report != latest:
                raise StaleReport(latest)
            request = proposal["id"]
            history = self._history(db, report, request)
            if generation < len(history):
                return history[generation]["decision"]
            if generation != len(history):
                raise ReviewError("Reload the request before making a decision.")
            previous = history[-1] if history else None
            if previous and previous["decision"] != "reopened" and decision != "reopened":
                raise ReviewError("Reopen the request before making another decision.")
            if decision == "reopened" and (not previous or previous["decision"] == "reopened"):
                raise ReviewError("Only a decided request can be reopened.")
            saved = dict(draft or (previous["draft"] if previous else proposal))
            if decision == "accepted":
                saved["entryId"] = saved.get("entryId") or uuid4().hex
                saved["revision"] = self._save(db, saved, saved["entryId"])
            if decision not in ("accepted", "rejected", "reopened"):
                raise ReviewError("Unknown review decision.")
            db.execute("INSERT INTO reviews VALUES (?, ?, ?, ?, ?)",
                       (report, request, generation, decision, json.dumps(saved, ensure_ascii=False)))
            return decision
