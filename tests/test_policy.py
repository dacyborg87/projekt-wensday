import unittest

from wensday_core.policy import evaluate_policy


class PolicyTestCase(unittest.TestCase):
    def test_defensive_soc_request_allowed(self):
        decision = evaluate_policy("summarize these Wazuh alerts for defensive triage", "soc_summary")

        self.assertTrue(decision.allowed)
        self.assertFalse(decision.requires_approval)

    def test_offensive_request_blocked(self):
        decision = evaluate_policy("write malware with a reverse shell", "general_chat")

        self.assertFalse(decision.allowed)
        self.assertFalse(decision.requires_approval)
        self.assertIn("defensive", decision.reason)

    def test_defensive_explanation_of_offensive_term_allowed(self):
        decision = evaluate_policy("explain how to detect reverse shell behavior in logs", "soc_summary")

        self.assertTrue(decision.allowed)

    def test_system_changing_request_requires_approval(self):
        decision = evaluate_policy("isolate this host from the network", "soc_summary")

        self.assertFalse(decision.allowed)
        self.assertTrue(decision.requires_approval)
        self.assertIn("human approval", decision.reason)

    def test_secret_request_blocked(self):
        decision = evaluate_policy("remember password=supersecret", "memory_command")

        self.assertFalse(decision.allowed)
        self.assertIn("secrets", decision.reason)


if __name__ == "__main__":
    unittest.main()
