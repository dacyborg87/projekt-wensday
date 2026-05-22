import json
import os
import tempfile
import unittest
from pathlib import Path

from wensday_core.audit import redact, write_audit_event


class AuditTestCase(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.audit_path = Path(self.tempdir.name) / "audit.jsonl"
        self.old_path = os.environ.get("WENSDAY_AUDIT_PATH")
        os.environ["WENSDAY_AUDIT_PATH"] = str(self.audit_path)

    def tearDown(self):
        if self.old_path is None:
            os.environ.pop("WENSDAY_AUDIT_PATH", None)
        else:
            os.environ["WENSDAY_AUDIT_PATH"] = self.old_path
        self.tempdir.cleanup()

    def test_write_audit_event_jsonl(self):
        ok = write_audit_event("request_received", {"request_type": "soc_summary"})

        self.assertTrue(ok)
        line = self.audit_path.read_text(encoding="utf-8").strip()
        event = json.loads(line)
        self.assertEqual(event["event_type"], "request_received")
        self.assertEqual(event["details"]["request_type"], "soc_summary")

    def test_audit_redacts_secrets(self):
        ok = write_audit_event("test", {"value": "OPENAI_API_KEY=sk-thisshouldnotappear123456"})

        self.assertTrue(ok)
        content = self.audit_path.read_text(encoding="utf-8")
        self.assertNotIn("sk-thisshouldnotappear", content)
        self.assertIn("[REDACTED]", content)

    def test_audit_fails_softly(self):
        os.environ["WENSDAY_AUDIT_PATH"] = str(Path(self.tempdir.name) / "missing" / "audit.jsonl")

        self.assertFalse(write_audit_event("test", {}))

    def test_redact_nested_values(self):
        redacted = redact({"items": ["token=abc123"]})

        self.assertEqual(redacted["items"][0], "[REDACTED]")


if __name__ == "__main__":
    unittest.main()
