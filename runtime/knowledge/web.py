"""Local browser interface for approved knowledge and report proposals."""

import argparse
from hashlib import sha256
from html import escape
from http.client import HTTPConnection, HTTPException
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from secrets import compare_digest, token_urlsafe
import subprocess
import sys
import time
from urllib.parse import parse_qs, quote, unquote, urlsplit

from .store import KnowledgeStore, ReviewError, StaleReport


PORT = 8765
ORIGIN = f"http://127.0.0.1:{PORT}"


def esc(value):
    return escape(str(value), quote=True)


def field(name, value):
    return f'<input type="hidden" name="{name}" value="{esc(value)}">'


def report_url(report):
    return "/reports/" + quote(report, safe="") + "/index.html#knowledge"


REPORT_ASSETS = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                 ".json": "application/json", ".txt": "text/plain", ".log": "text/plain", ".md": "text/plain"}


def load_proposals(path):
    file = path / "knowledge-proposals.json"
    return json.loads(file.read_text(encoding="utf-8")) if file.is_file() else {"requests": []}


class KnowledgePage:
    def __init__(self, store, token):
        self.store = store
        self.token = token

    def form(self, route, fields, body):
        hidden = "".join(field(key, value) for key, value in dict(fields, token=self.token).items())
        return f'<form method="post" action="{route}">{hidden}{body}</form>'

    @staticmethod
    def editor_fields(draft, *, app=False, current=False, review=False):
        application = esc(draft.get("app", ""))
        app_field = (f'<label>Application <input name="app" value="{application}" required></label><br>'
                     if app else f"<p>Application {application}</p>")
        output = (app_field + f'<label>Name <input name="name" value="{esc(draft.get("name", ""))}"></label><br>'
                  f'<label>Description <textarea name="description">{esc(draft.get("description", ""))}</textarea></label><br>'
                  f'<label>Steps, one per line <textarea name="steps" rows="6">'
                  f'{esc(chr(10).join(draft.get("steps", [])))}</textarea></label><br>')
        if review:
            choices = ("delete", "update") if current else ("add",)
            options = "".join(f'<option{" selected" if operation == draft["operation"] else ""}>{operation}</option>'
                              for operation in choices)
            if draft["operation"] not in choices:
                options = '<option value="" selected>Choose a new operation</option>' + options
            output += f'<label>Operation <select name="operation">{options}</select></label><br>'
        return output

    @staticmethod
    def steps(entry):
        return "<ol>" + "".join(f"<li>{esc(step)}</li>" for step in entry["steps"]) + "</ol>"

    def database(self, query):
        items = []
        for row in self.store.entries(query=query):
            fields = dict(entryId=row["id"], revision=row["revision"])
            buttons = ('<button name="action" value="save">Save</button> '
                       '<label><input type="checkbox" name="confirm"> Confirm deletion</label> '
                       '<button name="action" value="delete">Delete</button>')
            edit = self.form("/edit", fields, self.editor_fields(row, app=True) + buttons)
            items.append(f'<details><summary>{esc(row["app"])} · {esc(row["name"])}</summary>'
                         f'<p>{esc(row["description"])}</p>{self.steps(row)}{edit}</details>')
        add = self.form("/edit", {}, self.editor_fields({}, app=True) + '<button name="action" value="save">Add</button>')
        return ('<h1>Knowledge database</h1><form><label>Search app or knowledge name '
                f'<input name="q" value="{esc(query)}"></label> <button>Search</button></form>'
                + "".join(items) + "<h2>Add knowledge</h2>" + add)

    def proposals(self, report):
        path, latest = self.store.report(report)
        if path is None:
            raise ReviewError("The report is not registered with this installation.")
        data = load_proposals(path)
        rows = "".join(self.request_row(report, item, latest == report) for item in data["requests"])
        table = ('<table><thead><tr><th>Operation</th><th>What I learned</th><th>Name</th><th>Steps</th>'
                 '<th>Decision and actions</th></tr></thead><tbody>' + rows + '</tbody></table>' if rows else "")
        notice = (f'<p>This report is read-only. <a href="{report_url(latest)}">Open the latest report</a>.</p>'
                  if report != latest else "")
        return f'{notice}<p>{esc(data.get("message") or "No knowledge requests are available.")}</p>{table}'

    def request_row(self, report, item, editable):
        history = self.store.history(report, item["id"])
        previous = history[-1] if history else None
        status = previous["decision"] if previous and previous["decision"] != "reopened" else "pending"
        draft = previous["draft"] if previous else item
        current = self.store.lookup(draft["app"], entry_id=draft["entryId"]) if draft.get("entryId") else None
        if status == "pending" and current and draft["operation"] == "add":
            # A reopened addition already has an entry. Editing it is an update.
            draft = dict(draft, operation="update")
        actions = ""
        if editable:
            fields = dict(report=report, request=item["id"], generation=len(history),
                          revision=current["revision"] if current else "")
            if status == "pending":
                if draft.get("revision", "") != fields["revision"]:
                    actions = "<p>The entry changed. Review the current state before applying the proposal.</p>"
                actions += self.form("/review", fields, self.editor_fields(draft, current=current is not None, review=True)
                     + '<button name="action" value="accepted">Accept</button> '
                       '<button name="action" value="rejected">Do not accept</button>')
            else:
                actions = self.form("/review", fields, '<button name="action" value="reopened">Reopen</button>')
        revisions = " → ".join(row["decision"] for row in history)
        original = item.get("previous")
        before = ("<strong>At proposal time</strong>" + self.steps(original) if original else "")
        context = ("<strong>Current entry</strong><p>" + esc(current["name"]) + "</p>" + self.steps(current)
                   if current else "<p>No current entry.</p>")
        return (f'<tr><td>{esc(draft["operation"])}</td><td>{esc(draft["description"])}</td>'
                f'<td>{esc(draft["name"])}</td><td>{self.steps(draft)}{before}{context}</td>'
                f'<td>{esc(status.title())}<p>{esc(revisions)}</p>{actions}</td></tr>')

    @staticmethod
    def draft(values):
        return dict(name=values.get("name", ""), description=values.get("description", ""),
                    steps=[line.strip() for line in values.get("steps", "").splitlines() if line.strip()])

    def change(self, route, values):
        action = values.get("action")
        if route == "/edit":
            if action not in ("delete", "save") or action == "delete" and "confirm" not in values:
                raise ReviewError("Confirm deletion before deleting an entry.")
            self.store.edit(dict(self.draft(values), app=values.get("app", ""),
                                 operation="delete" if action == "delete" else "update",
                                 entryId=values.get("entryId", ""), revision=values.get("revision", "")))
            return "/"
        if route != "/review":
            raise ReviewError("Unknown action.")
        report = values.get("report", "")
        path, latest = self.store.report(report)
        if report != latest:
            raise StaleReport(latest)
        if path is None:
            raise ReviewError("The report is not registered.")
        item = next((row for row in load_proposals(path)["requests"] if row["id"] == values.get("request")), None)
        if item is None:
            raise ReviewError("Unknown proposal.")
        history = self.store.history(report, item["id"])
        base = history[-1]["draft"] if history else item
        draft = None
        if action != "reopened":
            operation = values.get("operation", "")
            if (not operation and history and history[-1]["decision"] == "reopened"
                    and base["operation"] == "add" and base.get("entryId") and values.get("revision")):
                # Older report forms did not select Update for a reopened addition.
                operation = "update"
            if action == "accepted" and operation not in ("add", "update", "delete"):
                raise ReviewError("Choose Add, Update, or Delete before accepting this request.")
            if action == "accepted" and operation in ("update", "delete") and not base.get("entryId"):
                raise ReviewError("Select an existing entry before updating or deleting it.")
            draft = dict(base)
            draft.update(self.draft(values), operation=operation or base["operation"], revision=values.get("revision", ""))
        generation = values.get("generation", "")
        if not generation.isascii() or not generation.isdecimal() or len(generation) > 12:
            raise ReviewError("Invalid request revision.")
        self.store.review(report, item, int(generation), action, draft)
        return report_url(report)


def installation_id(installation):
    return sha256(str(Path(installation).resolve()).encode()).hexdigest()


def server_ready(identity):
    connection = HTTPConnection("127.0.0.1", PORT, timeout=0.5)
    try:
        connection.request("GET", "/health")
        response = connection.getresponse()
        return response.status == 200 and response.read(65).decode("ascii") == identity
    except (OSError, HTTPException, UnicodeError):
        return False
    finally:
        connection.close()


def ensure_server(installation):
    identity = installation_id(installation)
    if server_ready(identity):
        return
    directory = KnowledgeStore(installation).path.parent
    with (directory / "web.log").open("ab") as log:
        worker = subprocess.Popen([sys.executable, "-m", "knowledge.web", str(installation)],
                                  stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                  start_new_session=True)
    for _ in range(25):
        if server_ready(identity):
            return
        if worker.poll() is not None:
            break
        time.sleep(0.1)
    if worker.poll() is None:
        worker.terminate()
    raise OSError(f"CIMT could not start the local report viewer at {ORIGIN}. Check {directory / 'web.log'}.")


def serve(installation):
    store = KnowledgeStore(installation)
    template = (store.path.parent / "editor.html").read_text(encoding="utf-8")
    page = KnowledgePage(store, token_urlsafe())
    identity = installation_id(installation)

    class Handler(BaseHTTPRequestHandler):
        def html(self, content, status=200):
            self.respond(template.replace("{{content}}", content).encode("utf-8"), "text/html; charset=utf-8", status)

        def respond(self, data, content_type, status=200, *, report=False):
            policy = "default-src 'none'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
            if report:
                policy += "; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' data:"
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", policy)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def redirect(self, path):
            self.send_response(303)
            self.send_header("Location", path)
            self.end_headers()

        def do_GET(self):
            if self.headers.get("Host") != f"127.0.0.1:{PORT}":
                self.html("<p>Invalid host.</p>", 403)
                return
            url = urlsplit(self.path)
            query = parse_qs(url.query)
            try:
                if url.path == "/health":
                    self.respond(identity.encode("ascii"), "text/plain")
                elif url.path == "/":
                    self.html(page.database(query.get("q", [""])[0]))
                elif url.path == "/latest":
                    _, latest = store.report("")
                    if latest:
                        self.redirect(report_url(latest))
                    else:
                        self.html("<p>No finalized reports are available.</p>")
                elif url.path.startswith("/reports/"):
                    self.report(url.path)
                elif url.path == "/review":
                    self.redirect(report_url(query.get("report", [""])[0]))
                else:
                    self.html("<p>Page not found.</p>", 404)
            except (ReviewError, OSError, ValueError) as error:
                self.html(f"<p>{esc(error)}</p>", 400)

        def report(self, route):
            report, separator, relative = route.removeprefix("/reports/").partition("/")
            folder, _ = store.report(unquote(report))
            if folder is None or not separator:
                self.html("<p>Report not found in this installation.</p>", 404)
                return
            target = (folder / unquote(relative)).resolve()
            if not target.is_relative_to(folder.resolve()) or not target.is_file():
                self.html("<p>Report file not found.</p>", 404)
                return
            if relative == "index.html":
                body = target.read_text(encoding="utf-8")
                before, start, remainder = body.partition("<!--knowledge-review-start-->")
                _, end, after = remainder.partition("<!--knowledge-review-end-->")
                if start and end:
                    body = before + page.proposals(unquote(report)) + after
                self.respond(body.encode("utf-8"), "text/html; charset=utf-8", report=True)
            elif content_type := REPORT_ASSETS.get(target.suffix):
                self.respond(target.read_bytes(), content_type)
            else:
                self.html("<p>Report file is available in the local report folder.</p>", 404)

        def do_POST(self):
            if (self.headers.get("Host") != f"127.0.0.1:{PORT}" or self.headers.get("Origin") != ORIGIN
                    or self.headers.get_content_type() != "application/x-www-form-urlencoded"):
                self.html("<p>Open the editor locally before submitting changes.</p>", 403)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 1024 * 1024:
                    raise ReviewError("Invalid request size.")
                values = {key: value[0] for key, value in
                          parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True).items()}
                if not compare_digest(values.get("token", "").encode(), page.token.encode()):
                    self.html("<p>Reload the editor before submitting changes.</p>", 403)
                    return
                self.redirect(page.change(self.path, values))
            except StaleReport as error:
                self.html(f'<p>{esc(error)} <a href="{report_url(error.latest)}">Open the latest report</a>.</p>', 409)
            except (ReviewError, ValueError, OSError) as error:
                self.html(f"<p>{esc(error)}</p>", 400)
            except Exception:
                self.html("<p>The change could not be saved. The request remains pending.</p>", 500)

    with ThreadingHTTPServer(("127.0.0.1", PORT), Handler) as server:
        print(f"CIMT knowledge editor: {ORIGIN}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("installation")
    parser.add_argument("--register", nargs=3, metavar=("REPORT", "PATH", "FINISHED"))
    parser.add_argument("--report-url", metavar="REPORT")
    parser.add_argument("--editor-url", action="store_true")
    options = parser.parse_args()
    try:
        if options.register:
            KnowledgeStore(options.installation).register(*options.register)
        if options.report_url or options.editor_url:
            if options.report_url and KnowledgeStore(options.installation).report(options.report_url)[0] is None:
                parser.exit(3, "The report is not registered with this CIMT installation.\n")
            ensure_server(options.installation)
            print(ORIGIN + (report_url(options.report_url) if options.report_url else "/"))
        elif not options.register:
            serve(options.installation)
    except OSError as error:
        parser.exit(3, f"{error}\n")


if __name__ == "__main__":
    main()
