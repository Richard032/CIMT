"""Persistent app knowledge and transactional review history."""

from contextlib import contextmanager
from hashlib import sha256
import json
import re
from pathlib import Path
import sqlite3
from uuid import uuid4


DEFAULT_GROUP = "General"
PLATFORMS = ("android", "ios", "windows", "maccatalyst")


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
                    description TEXT NOT NULL, steps TEXT NOT NULL, revision TEXT NOT NULL,
                    platform TEXT NOT NULL DEFAULT '', aliases TEXT NOT NULL DEFAULT '[]', groups TEXT NOT NULL DEFAULT '["General"]');
                CREATE TABLE IF NOT EXISTS reports (
                    id TEXT PRIMARY KEY, path TEXT NOT NULL, finished TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS reviews (
                    report TEXT NOT NULL, request TEXT NOT NULL, generation INTEGER NOT NULL,
                    decision TEXT NOT NULL, draft TEXT NOT NULL, PRIMARY KEY(report, request, generation));
            """)
            self._migrate_entries(connection)
            if write:
                connection.execute("BEGIN IMMEDIATE")
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _migrate_entries(db):
        def columns():
            return {row["name"] for row in db.execute("PRAGMA table_info(entries)")}

        if {"platform", "aliases", "groups"} <= columns():
            return
        with db:
            db.execute("BEGIN IMMEDIATE")
            existing = columns()
            if "platform" not in existing:
                db.execute("ALTER TABLE entries ADD COLUMN platform TEXT NOT NULL DEFAULT ''")
            if "aliases" not in existing:
                db.execute("ALTER TABLE entries ADD COLUMN aliases TEXT NOT NULL DEFAULT '[]'")
            if "groups" not in existing:
                db.execute("""ALTER TABLE entries ADD COLUMN groups TEXT NOT NULL DEFAULT '["General"]'""")

    @staticmethod
    def _entry(row):
        if row is None:
            return None
        entry = dict(row, steps=json.loads(row["steps"]), aliases=json.loads(row["aliases"]))
        entry["groups"] = json.loads(row["groups"])
        return entry

    def entries(self, app=None, query="", *, platform=None):
        with self.connect() as db:
            rows = db.execute("SELECT * FROM entries ORDER BY app, name, id").fetchall()
        entries = [self._entry(row) for row in rows
                   if (app is None or row["app"].casefold() == app.strip().casefold())
                   and (platform is None or row["platform"] in ("", platform))]
        words = re.findall(r"\w+", query.casefold())
        filler = {"a", "an", "can", "do", "how", "i", "in", "the", "to"}
        terms = [word for word in words if word not in filler] or words

        def score(entry):
            names = " ".join([entry["name"], *entry["aliases"]]).casefold()
            searchable = " ".join((names, entry["description"], entry["id"], entry["app"], *entry["groups"])).casefold()
            return sum(term in names for term in terms) if all(term in searchable for term in terms) else -1

        ranked = [(score(entry), entry) for entry in entries]
        ranked.sort(key=lambda item: (-item[0], not bool(item[1]["platform"])))
        return [entry for match, entry in ranked if match >= 0]

    @staticmethod
    def _group(app, name):
        key = app.strip().casefold() + "\0" + name.strip().casefold()
        return {"id": sha256(key.encode()).hexdigest()[:16], "name": name}

    def group_index(self, app, platform, query="", offset=0):
        groups = {}
        for entry in self.entries(app, query, platform=platform):
            for name in entry["groups"]:
                identity = self._group(app, name)
                group = groups.setdefault(identity["id"], dict(identity, count=0, knowledgeIds=[]))
                group["count"] += 1
                if len(group["knowledgeIds"]) < 5:
                    group["knowledgeIds"].append(entry["id"])
        return self._page("groups", sorted(groups.values(), key=lambda group: group["name"].casefold()), offset, 12)

    def browse(self, app, *, platform, group="", query="", entry_id="", offset=0):
        if entry_id:
            entry = self.lookup(app, entry_id=entry_id, platform=platform)
            return dict(entry, groups=[self._group(app, name) for name in entry["groups"]]) if entry else None
        if not group and not query.strip():
            return self.group_index(app, platform, offset=offset)
        entries = self.entries(app, query, platform=platform)
        if not group:
            return self._page("procedures", [self._describe(row) for row in entries], offset, 20)
        descriptions = []
        selected = None
        for row in entries:
            for name in row["groups"]:
                identity = self._group(app, name)
                if group == identity["id"] or group.strip().casefold() == name.casefold():
                    selected = identity
                    descriptions.append(self._describe(row))
                    break
        return dict(self._page("procedures", descriptions, offset, 20), group=selected)

    def _describe(self, row):
        return {**{key: row[key] for key in ("id", "name", "aliases", "description")},
                "groups": [self._group(row["app"], name) for name in row["groups"]]}

    @staticmethod
    def _page(key, rows, offset, size):
        end = offset + size
        return {key: rows[offset:end], "nextOffset": end if end < len(rows) else None}

    def lookup(self, app, query="", entry_id="", *, platform=None):
        entries = self.entries(app, query if not entry_id else "", platform=platform)
        if entry_id:
            return next((row for row in entries if row["id"] == entry_id), None)
        return [{key: row[key] for key in ("id", "name", "aliases", "description")} for row in entries[:20]]

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
        platform = draft.get("platform", current["platform"] if current else "")
        if platform not in ("", *PLATFORMS):
            raise ReviewError("Choose a supported platform or All platforms.")
        groups = draft.get("groups", current["groups"] if current else [DEFAULT_GROUP])
        if not isinstance(groups, list) or not groups or any(not isinstance(name, str) or not name.strip() for name in groups):
            raise ReviewError("At least one knowledge group is required.")
        groups = {name.strip().casefold(): name.strip() for name in groups}
        aliases = draft.get("aliases", current["aliases"] if current else [])
        if not isinstance(aliases, list) or any(not isinstance(alias, str) for alias in aliases):
            raise ReviewError("Alternate names must be text.")
        name = draft["name"].strip()
        if current and current["name"].casefold() != name.casefold():
            aliases = [*aliases, current["name"]]
        aliases = {alias.strip().casefold(): alias.strip() for alias in aliases
                   if alias.strip() and alias.strip().casefold() != name.casefold()}
        revision = uuid4().hex
        db.execute("""INSERT OR REPLACE INTO entries
                      (id, app, name, description, steps, revision, platform, aliases, groups)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                   (entry_id, draft["app"].strip(), name, draft["description"].strip(),
                    json.dumps(draft["steps"], ensure_ascii=False), revision, platform,
                    json.dumps(list(aliases.values()), ensure_ascii=False), json.dumps(list(groups.values()), ensure_ascii=False)))
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
