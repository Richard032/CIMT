"""Verify approval, standalone editing and agent lookup without provider access."""

from contextlib import closing
import json
import sqlite3
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
from knowledge.store import KnowledgeStore, ReviewError, StaleReport
from knowledge.web import KnowledgePage
from redaction import Redactor
from knowledge.proposals import without_screen_observations, write_proposals
from test_runtime_components import api_agent, action


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.root = Path(root.name)
        self.store = KnowledgeStore(self.root)
        self.folder = self.root / "report"
        self.folder.mkdir()
        self.store.register("run", self.folder, "2026-11-20T09:00:00Z")
        self.proposal = dict(id="p", app="ECON-M", name="Open XPA", description="Tap the filename first",
                             steps=["Tap the filename"], operation="add", entryId="", revision="")

    def test_approval_saves_the_reviewed_version_immediately_and_only_once(self):
        self.assertEqual(self.store.lookup("econ-m", "XPA"), [])
        edited = dict(self.proposal, steps=["Tap filename", "Tap Open XPA File"])
        self.store.review("run", self.proposal, 0, "accepted", edited)
        self.store.review("run", self.proposal, 0, "accepted", edited)
        entries = self.store.entries("econ-m")
        self.assertEqual([entry["steps"] for entry in entries], [edited["steps"]])
        self.assertEqual(self.store.entries("Other app"), [])
        self.assertEqual(self.store.history("run", "p")[0]["decision"], "accepted")

    def test_renaming_knowledge_keeps_its_id_and_old_name_searchable(self):
        self.store.edit(self.proposal)
        original, = self.store.entries()
        self.store.edit(dict(self.proposal, name="Import an offline file", aliases=["Load a fixture"],
                             entryId=original["id"], revision=original["revision"]))
        renamed = self.store.lookup("ECON-M", entry_id=original["id"])
        self.assertEqual(renamed["name"], "Import an offline file")
        self.assertEqual(renamed["aliases"], ["Load a fixture", "Open XPA"])
        self.assertEqual(self.store.lookup("econ-m", "open XPA")[0]["id"], original["id"])
        self.assertEqual(self.store.lookup("econ-m", "load fixture")[0]["id"], original["id"])

    def test_index_and_lookup_limit_results_to_shared_and_current_platform_entries(self):
        for app, name, platform in (("ECON-M", "Android picker", "android"),
                                    ("ECON-M", "iOS picker", "ios"),
                                    ("ECON-M", "Open XPA", ""),
                                    ("Other app", "Other instructions", "")):
            self.store.edit(dict(self.proposal, app=app, name=name, platform=platform))
        index = self.store.group_index("econ-m", "ios")
        self.assertEqual([(row["name"], row["count"]) for row in index["groups"]], [("General", 2)])
        page = self.store.browse("econ-m", platform="ios", group="General")
        self.assertEqual([row["name"] for row in page["procedures"]], ["iOS picker", "Open XPA"])
        self.assertEqual(set(page["procedures"][0]), {"id", "name", "aliases", "description"})
        android, = self.store.lookup("ECON-M", "picker", platform="android")
        self.assertIsNone(self.store.lookup("ECON-M", entry_id=android["id"], platform="ios"))

    def test_group_page_exposes_descriptions_before_steps(self):
        for i in range(21):
            self.store.edit(dict(self.proposal, name=f"Procedure {i:02}", groups=["Fixtures", "Setup"]))
        groups = self.store.browse("ECON-M", platform="ios")
        self.assertEqual([(row["name"], row["count"]) for row in groups["groups"]], [("Fixtures", 21), ("Setup", 21)])
        fixture_group = groups["groups"][0]
        self.assertEqual(len(fixture_group["knowledgeIds"]), 5)
        first = self.store.browse("ECON-M", platform="ios", group=fixture_group["id"])
        second = self.store.browse("ECON-M", platform="ios", group=fixture_group["id"], offset=first["nextOffset"])
        self.assertEqual(len(first["procedures"]), 20)
        self.assertIsNone(second["nextOffset"])
        description, = second["procedures"]
        self.assertEqual(description["name"], "Procedure 20")
        self.assertEqual(description["description"], self.proposal["description"])
        self.assertNotIn("steps", description)
        entry = self.store.browse("ECON-M", platform="ios", entry_id=description["id"])
        self.assertEqual(entry["steps"], self.proposal["steps"])
        self.assertEqual(entry["description"], description["description"])
        self.assertEqual(entry["id"], description["id"])
        self.assertEqual([group["name"] for group in entry["groups"]], ["Fixtures", "Setup"])

    def test_existing_entries_gain_default_metadata_without_changing_their_ids(self):
        store = KnowledgeStore(self.root / "legacy")
        store.path.parent.mkdir(parents=True)
        with closing(sqlite3.connect(store.path)) as db, db:
            db.execute("CREATE TABLE entries (id TEXT PRIMARY KEY, app TEXT, name TEXT, "
                       "description TEXT, steps TEXT, revision TEXT)")
            db.execute("INSERT INTO entries VALUES (?, ?, ?, ?, ?, ?)",
                       ("old-id", "ECON-M", "Open XPA", "Offline file", '["Select file"]', "old-revision"))
        group, = store.group_index("ECON-M", "ios")["groups"]
        self.assertEqual((group["name"], group["knowledgeIds"]), ("General", ["old-id"]))
        entry = store.lookup("ECON-M", entry_id="old-id", platform="android")
        self.assertEqual(entry["steps"], ["Select file"])
        self.assertEqual(entry["revision"], "old-revision")
        self.assertEqual(entry["groups"], ["General"])

    def test_old_report_rejects_write_and_identifies_the_latest_report(self):
        self.store.register("new", self.root, "2026-11-20T10:00:00Z")
        with self.assertRaises(StaleReport) as error:
            self.store.review("run", self.proposal, 0, "accepted")
        self.assertEqual(error.exception.latest, "new")
        self.assertEqual(self.store.history("run", "p"), [])
        self.assertEqual(self.store.entries(), [])

    def test_reopening_a_rejected_request_allows_acceptance(self):
        self.store.review("run", self.proposal, 0, "rejected")
        self.store.review("run", self.proposal, 1, "reopened")
        self.assertEqual(self.store.entries(), [])
        self.store.review("run", self.proposal, 2, "accepted")
        self.assertEqual(len(self.store.entries()), 1)

    def test_reopening_an_accepted_request_preserves_prior_knowledge_when_declined(self):
        self.store.review("run", self.proposal, 0, "accepted")
        self.store.review("run", self.proposal, 1, "reopened")
        original, = self.store.entries()
        revised = dict(self.proposal, operation="update", name="Changed", entryId=original["id"],
                       revision=original["revision"])
        self.store.review("run", self.proposal, 2, "rejected", revised)
        self.assertEqual(self.store.entries(), [original])

    def test_reopened_addition_can_be_edited_and_accepted_as_an_update(self):
        (self.folder / "knowledge-proposals.json").write_text(json.dumps({"requests": [self.proposal]}))
        page = KnowledgePage(self.store, "token")
        request = dict(report="run", request="p")
        page.change("/review", dict(request, generation="0", action="accepted", operation="add",
                                    name="Open XPA", description="Open an offline file", steps="Select the file"))
        original, = self.store.entries()
        page.change("/review", dict(request, generation="1", action="reopened"))
        self.assertIn("<option selected>update</option>", page.proposals("run"))

        # A page opened before the fix may submit a blank operation.
        page.change("/review", dict(request, generation="2", action="accepted", operation="",
                                    revision=original["revision"], name="Import XPA",
                                    description="Open an offline file", steps="Tap the filename"))
        edited, = self.store.entries()
        self.assertEqual(edited["id"], original["id"])
        self.assertEqual(edited["name"], "Import XPA")
        self.assertEqual(edited["steps"], ["Tap the filename"])
        history = self.store.history("run", "p")
        self.assertEqual([row["decision"] for row in history], ["accepted", "reopened", "accepted"])
        self.assertEqual(history[-1]["draft"]["operation"], "update")

    def test_manual_edit_conflicts_with_stale_approval_and_preserves_pending_state(self):
        self.store.edit(self.proposal)
        entry, = self.store.entries()
        proposed = dict(self.proposal, operation="update", entryId=entry["id"], revision=entry["revision"])
        self.store.edit(dict(proposed, name="Direct edit"))
        with self.assertRaisesRegex(ReviewError, "entry changed"):
            self.store.review("run", proposed, 0, "accepted")
        self.assertEqual(self.store.history("run", "p"), [])
        self.assertEqual(self.store.entries()[0]["name"], "Direct edit")

    def test_update_and_delete_apply_as_individual_approvals(self):
        self.store.edit(self.proposal)
        entry, = self.store.entries()
        update = dict(self.proposal, name="Revised name", operation="update",
                      entryId=entry["id"], revision=entry["revision"])
        self.store.review("run", update, 0, "accepted")
        revised, = self.store.entries()
        self.assertEqual(revised["name"], "Revised name")
        delete = dict(update, id="delete", operation="delete", revision=revised["revision"])
        self.store.review("run", delete, 0, "accepted")
        self.assertEqual(self.store.entries(), [])

    def test_standalone_editor_creates_previews_and_deletes_without_a_run(self):
        store = KnowledgeStore(self.root / "new-install")
        page = KnowledgePage(store, "token")
        page.change("/edit", dict(action="save", app="App", name="<Example>",
                                  description="Learned procedure", steps="First\nSecond"))
        entry, = store.entries()
        self.assertIn("&lt;Example&gt;", page.database("App"))
        self.assertIn("<li>Second</li>", page.database("Example"))
        page.change("/edit", dict(action="save", app="App", name="Example", entryId=entry["id"],
                                  revision=entry["revision"], description="Learned procedure", steps="Updated"))
        entry, = store.entries()
        page.change("/edit", dict(action="delete", confirm="on", entryId=entry["id"], revision=entry["revision"]))
        self.assertEqual(store.entries(), [])

    def test_latest_report_renders_review_controls_and_older_report_disables_them(self):
        (self.folder / "knowledge-proposals.json").write_text(json.dumps({"requests": [self.proposal]}))
        page = KnowledgePage(self.store, "token")
        latest = page.proposals("run")
        self.assertIn('name="action" value="accepted"', latest)
        self.assertIn('name="action" value="rejected"', latest)
        self.store.register("new", self.root, "2026-11-20T10:00:00Z")
        old = page.proposals("run")
        self.assertIn("This report is read-only.", old)
        self.assertIn("/reports/new/index.html#knowledge", old)
        self.assertNotIn("<form", old)

    def test_proposal_omits_exploration_ui_trees_and_keeps_screen_references(self):
        screen = {"id": "observed", "elements": [{"label": "large full UI tree"}]}
        scenario = {"exploration": {"paths": [{"label": "Open"}], "applicationMap": {
            "states": [{"id": "home", "observations": ["observed"]}],
            "observations": [screen]}}, "steps": [{"resultObservation": "observed"}]}
        evidence = {"devices": [{"scenarios": [scenario]}]}
        result = without_screen_observations(evidence)["devices"][0]["scenarios"][0]
        self.assertNotIn("observations", result["exploration"]["applicationMap"])
        self.assertEqual(result["exploration"]["applicationMap"]["states"],
                         [{"id": "home", "observations": ["observed"]}])
        self.assertEqual(result["steps"], scenario["steps"])
        self.assertEqual(scenario["exploration"]["applicationMap"]["observations"], [screen])

    def test_invalid_proposal_does_not_discard_valid_requests(self):
        class Generator:
            def propose(self, request):
                return [dict(app="ECON-M", operation="update", entryId="missing"),
                        dict(app="ECON-M", operation="add", name="Open XPA",
                             description="Choose a file", steps=["Tap the filename"])]

        write_proposals(self.folder, Generator(), None, self.store, Redactor({}),
                        [{"app-name": "ECON-M"}], {})
        record = json.loads((self.folder / "knowledge-proposals.json").read_text())
        self.assertEqual([row["name"] for row in record["requests"]], ["Open XPA"])
        self.assertIn("Skipped 1 invalid request", record["message"])
        self.assertIn("Request 1: An update or deletion did not identify an approved entry.", record["message"])

    def test_post_run_proposal_redacts_and_waits_for_approval(self):
        class Generator:
            def propose(self, request):
                return [dict(app="ECON-M", operation="add", name="Open XPA", description="Learned private-secret", groups=["Offline files"],
                             steps=["Tap the filename"])]
        write_proposals(self.folder, Generator(), None, self.store, Redactor({"secret": "private-secret"}),
                        [{"app-name": "ECON-M"}], {})
        record = json.loads((self.folder / "knowledge-proposals.json").read_text())
        self.assertEqual(record["requests"][0]["description"], "Learned <redacted>")
        self.assertEqual(record["requests"][0]["groups"], ["Offline files"])
        self.assertEqual(self.store.entries(), [])


def knowledge_call(arguments, call_id):
    return {"status": "completed", "output": [
        {"type": "function_call", "name": "knowledge_lookup", "call_id": call_id,
         "arguments": json.dumps(arguments)}]}


class AgentKnowledgeTests(unittest.TestCase):
    def test_agent_can_search_and_read_approved_steps_before_choosing_a_command(self):
        agent, _, transport = api_agent([
            knowledge_call({"group": "Offline files", "query": "Open XPA"}, "search"), knowledge_call({"entryId": "one"}, "read"),
            action()])
        responses = {"": [{"id": "one", "name": "Open XPA"}],
                     "one": {"steps": ["Tap the filename first"]}}
        reply = agent.choose("Test XPA", "", "", [], b"", [], [], {},
                             knowledge_lookup=lambda **args: responses[args["entry_id"]])
        self.assertEqual(reply["action"], "done")
        instructions = transport.bodies[0]["input"][0]["content"]
        self.assertIn("Approved app knowledge is available", instructions)
        self.assertIn("Consult knowledge when you encounter a new task", instructions)
        self.assertIn("human-reviewed procedure", instructions)
        self.assertIn("quote its name, steps, and UI labels verbatim", instructions)
        self.assertIn("report the specific mismatch", instructions)
        outputs = [item for item in transport.bodies[-1]["input"] if item.get("type") == "function_call_output"]
        self.assertEqual([result["call_id"] for result in outputs], ["search", "read"])
        self.assertIn("Tap the filename first", outputs[-1]["output"])

    def test_initial_index_contains_groups_without_procedure_steps(self):
        agent, _, transport = api_agent([action()])
        index = {"groups": [{"name": "Offline files", "count": 3}], "nextOffset": None}
        agent.choose("Test XPA", "", "", [], b"", [], [], {}, knowledge_index=index,
                     knowledge_lookup=lambda **args: [])
        index_text = transport.bodies[0]["input"][-1]["content"][-1]["text"]
        self.assertIn(json.dumps(index), index_text)
        self.assertNotIn('"steps"', index_text)

    def test_disabled_agent_does_not_advertise_knowledge_lookup(self):
        agent, _, transport = api_agent([action()])
        agent.choose("Test XPA", "", "", [], b"", [], [], {})
        self.assertNotIn("knowledge_lookup", [tool["name"] for tool in transport.bodies[0]["tools"]])
