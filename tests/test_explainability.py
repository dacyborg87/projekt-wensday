import os
import tempfile
import unittest
from pathlib import Path

from wensday_core.orchestrator import (
    WensdayOrchestrator,
    WensdayRequest,
    get_latest_explainable_response,
)
from wensday_core.plugins import PluginRegistry, PluginResult


class ExplainabilityTestCase(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.old_memory = os.environ.get("WENSDAY_MEMORY_PATH")
        self.old_audit = os.environ.get("WENSDAY_AUDIT_PATH")
        self.old_key = os.environ.pop("OPENAI_API_KEY", None)
        os.environ["WENSDAY_MEMORY_PATH"] = str(Path(self.tempdir.name) / "memory.json")
        os.environ["WENSDAY_AUDIT_PATH"] = str(Path(self.tempdir.name) / "audit.jsonl")

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

    def test_operational_response_has_explainable_fields(self):
        orchestrator = WensdayOrchestrator()
        request = WensdayRequest("summarize Wazuh alerts", request_type="soc_summary", mode="soc_analyst")

        response = orchestrator.process(request)

        self.assertIsNotNone(response.explainable)
        self.assertTrue(response.explainable.summary)
        self.assertIn("Policy decision", " ".join(response.explainable.reasoning))
        self.assertIn("Allowed defensive/read-only request.", response.explainable.policy_result)
        self.assertTrue(response.explainable.confidence)

    def test_general_chat_fallback_stays_lightweight(self):
        orchestrator = WensdayOrchestrator()
        request = WensdayRequest("hello Wensday", request_type="general_chat", mode="personal")

        response = orchestrator.process(request)

        self.assertIsInstance(response.to_text(), str)
        self.assertIsNone(response.explainable)

    def test_missing_plugin_is_recorded_as_unverified(self):
        orchestrator = WensdayOrchestrator()
        request = WensdayRequest("summarize Wazuh alerts", request_type="soc_summary", mode="soc_analyst")

        response = orchestrator.process(request)

        self.assertIn(
            "No external SOC or threat-intel integration verified this response.",
            response.explainable.unverified_items,
        )

    def test_plugin_response_records_plugin_and_evidence(self):
        class SocPlugin:
            name = "soc_plugin"
            request_types = {"soc_summary"}
            read_only = True
            description = "Test SOC plugin"

            def can_handle(self, request):
                return True

            def run(self, request):
                return PluginResult(
                    handled=True,
                    answer="SOC summary T1055",
                    evidence=["alert_count=3"],
                    confidence="high",
                )

        registry = PluginRegistry()
        registry.register(SocPlugin())
        orchestrator = WensdayOrchestrator(plugin_registry=registry)
        request = WensdayRequest("summarize Wazuh alerts", request_type="soc_summary", mode="soc_analyst")

        response = orchestrator.process(request)

        self.assertEqual(response.confidence, "high")
        self.assertIn("alert_count=3", response.explainable.evidence)
        self.assertIn("soc_plugin", response.explainable.plugins_queried)

    def test_dashboard_latest_explainable_snapshot_is_safe_shape(self):
        orchestrator = WensdayOrchestrator()
        orchestrator.handle("summarize Wazuh alerts")

        latest = get_latest_explainable_response()

        self.assertIsNotNone(latest)
        self.assertIn("summary", latest)
        self.assertIn("confidence", latest)
        self.assertIn("policy_result", latest)
        self.assertEqual(latest["query"], "soc_summary / personal")
        self.assertNotIn("summarize Wazuh alerts", str(latest))

    def test_policy_denial_records_explainability(self):
        orchestrator = WensdayOrchestrator()
        request = WensdayRequest(
            "isolate this host for the incident",
            request_type="incident_summary",
            mode="incident_commander",
        )

        response = orchestrator.process(request)

        self.assertTrue(response.requires_approval)
        self.assertIsNotNone(response.explainable)
        self.assertIn("human approval", response.explainable.policy_result)


if __name__ == "__main__":
    unittest.main()
