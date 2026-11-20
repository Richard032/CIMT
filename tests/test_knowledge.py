"""Verify approval, standalone editing and agent lookup without provider access."""

import json
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

    def test_post_run_proposal_redacts_and_waits_for_approval(self):
        class Generator:
            def propose(self, request):
                return [dict(app="ECON-M", operation="add", name="Open XPA", description="Learned private-secret",
                             steps=["Tap the filename"])]
        write_proposals(self.folder, Generator(), None, self.store, Redactor({"secret": "private-secret"}),
                        [{"app-name": "ECON-M"}], {})
        record = json.loads((self.folder / "knowledge-proposals.json").read_text())
        self.assertEqual(record["requests"][0]["description"], "Learned <redacted>")
        self.assertEqual(self.store.entries(), [])


def knowledge_call(arguments, call_id):
    return {"status": "completed", "output": [
        {"type": "function_call", "name": "knowledge_lookup", "call_id": call_id,
         "arguments": json.dumps(arguments)}]}


class AgentKnowledgeTests(unittest.TestCase):
    def test_agent_can_search_and_read_approved_steps_before_choosing_a_command(self):
        agent, _, transport = api_agent([
            knowledge_call({"query": "Open XPA"}, "search"), knowledge_call({"entryId": "one"}, "read"),
            action()])
        responses = {"": [{"id": "one", "name": "Open XPA"}],
                     "one": {"steps": ["Tap the filename first"]}}
        reply = agent.choose("Test XPA", "", "", [], b"", [], [], {},
                             knowledge_lookup=lambda **args: responses[args["entry_id"]])
        self.assertEqual(reply["action"], "done")
        instructions = transport.bodies[0]["input"][0]["content"]
        self.assertIn("Approved app knowledge is available", instructions)
        self.assertIn("human-reviewed procedure", instructions)
        self.assertIn("quote its name, steps, and UI labels verbatim", instructions)
        self.assertIn("report the specific mismatch", instructions)
        outputs = [item for item in transport.bodies[-1]["input"] if item.get("type") == "function_call_output"]
        self.assertEqual([result["call_id"] for result in outputs], ["search", "read"])
        self.assertIn("Tap the filename first", outputs[-1]["output"])

    def test_disabled_agent_does_not_advertise_knowledge_lookup(self):
        agent, _, transport = api_agent([action()])
        agent.choose("Test XPA", "", "", [], b"", [], [], {})
        self.assertNotIn("knowledge_lookup", [tool["name"] for tool in transport.bodies[0]["tools"]])
