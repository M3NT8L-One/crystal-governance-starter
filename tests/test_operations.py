from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import crystal_health_check  # noqa: E402
import crystal_registry_reconcile  # noqa: E402


class HealthCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "crystal-home"
        shutil.copytree(ROOT / "examples/sample-crystal-home", self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_aligned_sample_is_healthy(self) -> None:
        report = crystal_health_check.health_report(self.root, "default")
        self.assertEqual(report["status"], "HEALTHY")
        self.assertTrue(report["ok"])
        self.assertEqual(report["critical_failures"], [])
        self.assertEqual(report["degradations"], [])

    def test_registry_drift_is_degraded(self) -> None:
        shutil.rmtree(self.root / "profiles/default/sessions/session-beta")
        report = crystal_health_check.health_report(self.root, "default")
        self.assertEqual(report["status"], "DEGRADED")
        self.assertTrue(report["ok"])
        self.assertIn("session_registry_alignment", report["degradations"])

    def test_unreadable_registry_is_unhealthy(self) -> None:
        (self.root / "profiles/default/registry.json").write_text("{", encoding="utf-8")
        report = crystal_health_check.health_report(self.root, "default")
        self.assertEqual(report["status"], "UNHEALTHY")
        self.assertFalse(report["ok"])
        self.assertIn("registry_readable", report["critical_failures"])

    def test_recorded_frontdoor_with_cron_source_is_degraded(self) -> None:
        registry_path = self.root / "profiles/default/registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["sessions"]["session-alpha"].update(
            {"actor_kind": "frontdoor", "source": "cron"}
        )
        registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

        report = crystal_health_check.health_report(self.root, "default")

        self.assertEqual(report["status"], "DEGRADED")
        self.assertIn("excluded_actor_registry", report["degradations"])

    def test_subagent_source_is_degraded(self) -> None:
        registry_path = self.root / "profiles/default/registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["sessions"]["session-alpha"].update(
            {"actor_kind": "frontdoor", "platform": "subagent", "source": "subagent"}
        )
        registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

        report = crystal_health_check.health_report(self.root, "default")

        self.assertEqual(report["status"], "DEGRADED")
        self.assertIn("excluded_actor_registry", report["degradations"])

    def test_runtime_actor_kinds_are_degraded(self) -> None:
        for actor_kind in ("auxiliary_model", "cron_job", "kanban_worker", "scratch_agent"):
            with self.subTest(actor_kind=actor_kind):
                registry_path = self.root / "profiles/default/registry.json"
                registry = json.loads(registry_path.read_text(encoding="utf-8"))
                registry["sessions"]["session-alpha"] = {"actor_kind": actor_kind}
                registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

                report = crystal_health_check.health_report(self.root, "default")

                self.assertEqual(report["status"], "DEGRADED")
                self.assertIn("excluded_actor_registry", report["degradations"])

    def test_missing_actor_identity_is_degraded_but_not_excluded(self) -> None:
        registry_path = self.root / "profiles/default/registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["sessions"]["session-alpha"] = {"topic_key": "unknown-source"}
        registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

        report = crystal_health_check.health_report(self.root, "default")

        self.assertEqual(report["status"], "DEGRADED")
        self.assertIn("unclassified_actor_registry", report["degradations"])
        self.assertNotIn("excluded_actor_registry", report["degradations"])

    def test_source_health_reports_dirty_tree_and_missing_remote(self) -> None:
        source = Path(self.temp.name) / "source"
        source.mkdir()
        subprocess.run(["git", "init", "-q", str(source)], check=True)
        subprocess.run(["git", "-C", str(source), "config", "user.email", "demo@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(source), "config", "user.name", "Demo User"], check=True)
        (source / "README.md").write_text("demo\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(source), "add", "README.md"], check=True)
        subprocess.run(["git", "-C", str(source), "commit", "-qm", "initial"], check=True)

        report = crystal_health_check.health_report(self.root, "default", source_root=source)
        self.assertEqual(report["status"], "DEGRADED")
        self.assertIn("source_durability", report["degradations"])

        subprocess.run(
            ["git", "-C", str(source), "remote", "add", "origin", "https://example.invalid/demo.git"],
            check=True,
        )
        clean = crystal_health_check.health_report(self.root, "default", source_root=source)
        self.assertEqual(clean["status"], "HEALTHY")
        self.assertNotIn("origin", json.dumps(clean))

        (source / "README.md").write_text("changed\n", encoding="utf-8")
        dirty = crystal_health_check.health_report(self.root, "default", source_root=source)
        self.assertEqual(dirty["status"], "DEGRADED")
        self.assertIn("live_source_clean", dirty["degradations"])
        self.assertNotIn("README.md", json.dumps(dirty))

    def test_actor_inference_does_not_match_substrings(self) -> None:
        registry_path = self.root / "profiles/default/registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["sessions"]["session-alpha"].update(
            {
                "platform": "preview",
                "source": "code-review",
                "session_type": "internal-tool",
            }
        )
        registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

        report = crystal_health_check.health_report(self.root, "default")

        self.assertEqual(report["status"], "HEALTHY")

    def test_identifier_collision_is_unhealthy(self) -> None:
        registry_path = self.root / "profiles/default/registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["sessions"]["session/alpha"] = dict(registry["sessions"]["session-alpha"])
        registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

        report = crystal_health_check.health_report(self.root, "default")

        self.assertEqual(report["status"], "UNHEALTHY")
        self.assertIn("session_identifier_collisions", report["critical_failures"])

    def test_non_directory_session_root_is_unhealthy_without_path_leak(self) -> None:
        session_root = self.root / "profiles/default/sessions"
        shutil.rmtree(session_root)
        session_root.write_text("not a directory\n", encoding="utf-8")

        report = crystal_health_check.health_report(self.root, "default")

        self.assertEqual(report["status"], "UNHEALTHY")
        self.assertIn("session_directory_readable", report["critical_failures"])
        self.assertNotIn(str(self.root), json.dumps(report))

    def test_other_profile_stale_lock_does_not_affect_default(self) -> None:
        other = self.root / "profiles/other"
        other.mkdir()
        (other / "stale.lock").write_text("locked\n", encoding="utf-8")

        report = crystal_health_check.health_report(
            self.root,
            "default",
            stale_lock_seconds=-1,
        )

        self.assertEqual(report["status"], "HEALTHY")
        self.assertEqual(report["critical_failures"], [])


class RegistryReconcileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "crystal-home"
        shutil.copytree(ROOT / "examples/sample-crystal-home", self.root)
        self.profile = self.root / "profiles/default"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_dry_run_finds_orphan_without_mutation(self) -> None:
        orphan = self.profile / "sessions/orphan-session"
        orphan.mkdir()
        (orphan / "CRYSTAL.md").write_text("# preserved evidence\n", encoding="utf-8")

        result = crystal_registry_reconcile.reconcile_registry(self.root, "default")

        self.assertTrue(result["ok"])
        self.assertTrue(result["dry_run"])
        self.assertFalse(result["applied"])
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["summary"], {"orphan_session_directory": 1})
        self.assertTrue(orphan.exists())
        self.assertFalse((self.profile / "archive").exists())

    def test_non_directory_session_root_refuses_without_path_leak(self) -> None:
        session_root = self.profile / "sessions"
        shutil.rmtree(session_root)
        session_root.write_text("not a directory\n", encoding="utf-8")
        before = (self.profile / "registry.json").read_text(encoding="utf-8")

        result = crystal_registry_reconcile.reconcile_registry(self.root, "default")

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "NotADirectoryError")
        self.assertNotIn(str(self.root), json.dumps(result))
        self.assertEqual((self.profile / "registry.json").read_text(encoding="utf-8"), before)
        self.assertFalse((self.profile / "archive").exists())

    def test_plan_omits_registry_entry_metadata(self) -> None:
        registry_path = self.profile / "registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["sessions"]["session-beta"].update(
            {
                "actor_kind": "background_worker",
                "private_note": "do-not-share-this-metadata",
            }
        )
        registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

        result = crystal_registry_reconcile.reconcile_registry(self.root, "default")

        serialized = json.dumps(result)
        self.assertNotIn("entry", result["candidates"][0])
        self.assertNotIn("do-not-share-this-metadata", serialized)

    def test_false_positive_actor_substrings_are_not_selected(self) -> None:
        registry_path = self.profile / "registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["sessions"]["session-beta"].update(
            {
                "platform": "preview",
                "source": "code-review",
                "session_type": "internal-tool",
            }
        )
        registry["sessions"]["session-hyphen-worker"] = {"actor_kind": "background-worker"}
        worker_dir = self.profile / "sessions/session-hyphen-worker"
        worker_dir.mkdir()
        (worker_dir / "CRYSTAL.md").write_text("# worker\n", encoding="utf-8")
        registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

        result = crystal_registry_reconcile.reconcile_registry(self.root, "default")
        candidates = {item["session_id"]: item for item in result["candidates"]}

        self.assertNotIn("session-beta", candidates)
        self.assertEqual(candidates["session-hyphen-worker"]["reasons"], ["excluded_actor"])

    def test_identifier_collision_refuses_to_plan(self) -> None:
        registry_path = self.profile / "registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["sessions"]["session/alpha"] = dict(registry["sessions"]["session-alpha"])
        registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

        result = crystal_registry_reconcile.reconcile_registry(self.root, "default")

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "session identifier collision")
        self.assertFalse((self.profile / "archive").exists())

    def test_apply_archives_evidence_and_writes_restoration_receipt(self) -> None:
        registry_path = self.profile / "registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["sessions"]["session-beta"]["actor_kind"] = "background_worker"
        registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

        result = crystal_registry_reconcile.reconcile_registry(
            self.root,
            "default",
            dry_run=False,
            timestamp="20300101T010203Z",
        )

        self.assertTrue(result["applied"])
        self.assertFalse((self.profile / "sessions/session-beta").exists())
        archive = self.profile / result["archive"]
        self.assertTrue((archive / "sessions/session-beta/CRYSTAL.md").exists())
        self.assertTrue((archive / "registry.before.json").exists())
        self.assertTrue((archive / "registry.after.json").exists())
        receipt = json.loads((self.profile / result["receipt"]).read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "complete")
        self.assertEqual(receipt["removed_registry_count"], 1)
        self.assertEqual(receipt["moves"][0]["session_id"], "session-beta")
        updated = json.loads(registry_path.read_text(encoding="utf-8"))
        self.assertNotIn("session-beta", updated["sessions"])

    def test_apply_rolls_back_after_mid_move_failure(self) -> None:
        registry_path = self.profile / "registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        for entry in registry["sessions"].values():
            entry["actor_kind"] = "background_worker"
        registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
        before = json.loads(registry_path.read_text(encoding="utf-8"))
        real_move = shutil.move
        call_count = 0

        def fail_second_move(source: str, destination: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise OSError("simulated move failure")
            return real_move(source, destination)

        with mock.patch.object(crystal_registry_reconcile.shutil, "move", side_effect=fail_second_move):
            result = crystal_registry_reconcile.reconcile_registry(
                self.root,
                "default",
                dry_run=False,
                timestamp="20300101T020304Z",
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "rolled_back")
        self.assertNotIn(str(self.root), json.dumps(result))
        self.assertEqual(json.loads(registry_path.read_text(encoding="utf-8")), before)
        self.assertTrue((self.profile / "sessions/session-alpha").exists())
        self.assertTrue((self.profile / "sessions/session-beta").exists())
        receipt = json.loads((self.profile / result["receipt"]).read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "rolled_back")

    def test_existing_archive_refuses_apply_without_mutation(self) -> None:
        registry_path = self.profile / "registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["sessions"]["session-beta"]["actor_kind"] = "background_worker"
        registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
        before = registry_path.read_text(encoding="utf-8")
        archive = self.profile / "archive/registry-reconcile-20300101T030405Z"
        archive.mkdir(parents=True)

        result = crystal_registry_reconcile.reconcile_registry(
            self.root,
            "default",
            dry_run=False,
            timestamp="20300101T030405Z",
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "archive already exists")
        self.assertEqual(registry_path.read_text(encoding="utf-8"), before)
        self.assertTrue((self.profile / "sessions/session-beta").exists())

    def test_misclassified_cron_source_is_selected(self) -> None:
        registry_path = self.profile / "registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["sessions"]["session-beta"].update(
            {"actor_kind": "frontdoor", "source": "cron"}
        )
        registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

        result = crystal_registry_reconcile.reconcile_registry(self.root, "default")

        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["summary"], {"excluded_actor": 1})

    def test_protected_session_is_never_selected(self) -> None:
        registry_path = self.profile / "registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["sessions"]["session-alpha"]["actor_kind"] = "background_worker"
        registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

        result = crystal_registry_reconcile.reconcile_registry(
            self.root,
            "default",
            protect_sessions=["session-alpha"],
        )

        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(result["protected"], ["session-alpha"])
        self.assertTrue((self.profile / "sessions/session-alpha").exists())


class TriageGateTests(unittest.TestCase):
    def test_degraded_health_wakes_even_when_audit_is_clean(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            report_dir = Path(temp)
            (report_dir / "crystal-governance-audit.json").write_text(
                json.dumps({"high_count": 0, "medium_count": 0, "finding_count": 0}),
                encoding="utf-8",
            )
            (report_dir / "crystal-health.json").write_text(
                json.dumps({"status": "DEGRADED", "degradations": ["source_durability"]}),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "crystal_triage_gate.py"),
                    "--report-dir",
                    str(report_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("status=DEGRADED", result.stdout)
            self.assertIn("source_durability", result.stdout)
            self.assertNotIn(str(report_dir), result.stdout)

    def test_wrapper_triages_unhealthy_health_before_exiting(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "state"
            out = Path(temp) / "reports"
            shutil.copytree(ROOT / "examples/sample-crystal-home", root)
            (root / "profiles/default/registry.json").write_text("{", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "run_crystal_checks.py"),
                    "--root",
                    str(root),
                    "--out",
                    str(out),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 1)
            self.assertTrue((out / "crystal-health.json").exists())
            self.assertIn("status=UNHEALTHY", result.stdout)
            self.assertIn("registry_readable", result.stdout)

    def test_non_object_health_report_fails_closed_with_wake(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            report_dir = Path(temp)
            (report_dir / "crystal-governance-audit.json").write_text(
                json.dumps({"high_count": 0, "medium_count": 0, "finding_count": 0}),
                encoding="utf-8",
            )
            (report_dir / "crystal-health.json").write_text("[]\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "crystal_triage_gate.py"),
                    "--report-dir",
                    str(report_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn("health report unreadable", result.stdout)
            self.assertIn("InvalidReportType", result.stdout)
            self.assertNotIn(str(report_dir), result.stdout)

    def test_corrupt_health_report_fails_closed_with_wake(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            report_dir = Path(temp)
            (report_dir / "crystal-governance-audit.json").write_text(
                json.dumps({"high_count": 0, "medium_count": 0, "finding_count": 0}),
                encoding="utf-8",
            )
            (report_dir / "crystal-health.json").write_text("{", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "crystal_triage_gate.py"),
                    "--report-dir",
                    str(report_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn("health report unreadable", result.stdout)
            self.assertIn("JSONDecodeError", result.stdout)
            self.assertNotIn(str(report_dir), result.stdout)

    def test_healthy_state_and_clean_audit_stay_quiet(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            report_dir = Path(temp)
            (report_dir / "crystal-governance-audit.json").write_text(
                json.dumps({"high_count": 0, "medium_count": 0, "finding_count": 0}),
                encoding="utf-8",
            )
            (report_dir / "crystal-health.json").write_text(
                json.dumps({"status": "HEALTHY", "degradations": []}),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "crystal_triage_gate.py"),
                    "--report-dir",
                    str(report_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
