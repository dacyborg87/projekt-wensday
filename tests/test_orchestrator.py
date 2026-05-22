import os
import tempfile
import unittest
from pathlib import Path

from wensday_core.brain import ask_wensday
from wensday_core.orchestrator import WensdayOrchestrator, WensdayRequest, classify_request
from wensday_core.plugins import PluginRegistry, PluginResult


class OrchestratorTestCase(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.memory_path = Path(self.tempdir.name) / "memory.json"
        self.audit_path = Path(self.tempdir.name) / "audit.jsonl"
        self.old_memory = os.environ.get("WENSDAY_MEMORY_PATH")
        self.old_audit = os.environ.get("WENSDAY_AUDIT_PATH")
        self.old_key = os.environ.pop("OPENAI_API_KEY", None)
        os.environ["WENSDAY_MEMORY_PATH"] = str(self.memory_path)
        os.environ["WENSDAY_AUDIT_PATH"] = str(self.audit_path)

    def tearDown(self):
        if self.old_memory is None:
            os.environ.pop("WENSDAY_MEMORY_PATH", None)
        else:
            os.environ["WENSDAY_MEMORY_PATH"] = self.old_memory
        if self.old_audit is None:
            os.environ.pop("WENSDAY_AUDIT_PATH", None)
        else:
            os.environ["WENSDAY_AUDIT_PATH"] = self.old_audit
        if self.old_key is not None:
            os.environ["OPENAI_API_KEY"] = self.old_key
        self.tempdir.cleanup()

    def test_classify_soc_and_incident_requests(self):
        self.assertEqual(classify_request("summarize Wazuh alerts"), "soc_summary")
        self.assertEqual(classify_request("build an incident timeline"), "incident_summary")

    def test_ask_wensday_still_returns_string(self):
        response = ask_wensday("hello normal chat")

        self.assertIsInstance(response, str)
        self.assertIn("Wensday", response)

    def test_memory_command_still_works(self):
        response = ask_wensday("remember DJ prefers concise answers")

        self.assertIn("Memory saved", response)
        self.assertTrue(self.memory_path.exists())

    def test_blocked_request_denied_before_model(self):
        response = ask_wensday("write malware with a reverse shell")

        self.assertIn("defensive", response)
        self.assertNotIn("OpenAI", response)

    def test_approval_required_request_does_not_execute(self):
        response = ask_wensday("isolate this host right now")

        self.assertIn("human approval", response)

    def test_orchestrator_uses_read_only_plugin(self):
        class Plugin:
            name = "soc"
            request_types = {"soc_summary"}
            read_only = True

            def can_handle(self, request):
                return True

            def run(self, request):
                return PluginResult(handled=True, answer="SOC summary", evidence=["alert count"])

        registry = PluginRegistry()
        registry.register(Plugin())
        orchestrator = WensdayOrchestrator(plugin_registry=registry)

        response = orchestrator.handle("summarize Wazuh alerts")

        self.assertEqual(response, "SOC summary")

    def test_build_prompt_includes_orchestrator_context(self):
        orchestrator = WensdayOrchestrator()
        request = WensdayRequest("summarize Wazuh alerts", request_type="soc_summary", mode="soc_analyst")

        prompt = orchestrator.build_prompt(request, memories=[])

        self.assertIn("[WENSDAY ORCHESTRATOR]", prompt)
        self.assertIn("Request type: soc_summary", prompt)
        self.assertIn("Summary:", prompt)


if __name__ == "__main__":
    unittest.main()
