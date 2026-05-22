import json
import os
import tempfile
import unittest
from pathlib import Path

import wensday_core.memory as memory
from wensday_core.brain import ask_wensday, build_prompt


class MemoryTestCase(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.memory_path = Path(self.tempdir.name) / "memory.json"
        self.old_path = os.environ.get("WENSDAY_MEMORY_PATH")
        os.environ["WENSDAY_MEMORY_PATH"] = str(self.memory_path)

    def tearDown(self):
        if self.old_path is None:
            os.environ.pop("WENSDAY_MEMORY_PATH", None)
        else:
            os.environ["WENSDAY_MEMORY_PATH"] = self.old_path
        self.tempdir.cleanup()

    def test_add_memory_writes_structured_record(self):
        item = memory.add_memory(
            "DJ is stabilizing Wensday memory.",
            category="projects",
            tags=["wensday"],
        )

        self.assertTrue(item["id"].startswith("mem_"))
        self.assertEqual(item["category"], "projects")
        self.assertEqual(item["content"], "DJ is stabilizing Wensday memory.")
        self.assertEqual(item["tags"], ["wensday"])
        self.assertEqual(item["sensitivity"], "normal")
        self.assertEqual(item["source"], "user_explicit")
        self.assertIn("created_at", item)
        self.assertIn("updated_at", item)

    def test_legacy_memory_loads_as_structured(self):
        self.memory_path.write_text(
            json.dumps(
                [
                    {
                        "text": "DJ is learning Wazuh.",
                        "category": "lab",
                        "timestamp": "2026-01-01T00:00:00Z",
                    }
                ]
            ),
            encoding="utf-8",
        )

        recent = memory.get_recent_memories()

        self.assertEqual(recent[0]["content"], "DJ is learning Wazuh.")
        self.assertEqual(recent[0]["category"], "lab")
        self.assertEqual(recent[0]["created_at"], "2026-01-01T00:00:00Z")
        self.assertEqual(recent[0]["source"], "legacy")

    def test_relevant_memories_prioritize_keywords(self):
        memory.add_memory("DJ uses Wazuh in the SOC lab.", category="soc_lab")
        memory.add_memory("DJ likes short explanations.", category="preferences")

        relevant = memory.get_relevant_memories("summarize my wazuh alerts")

        self.assertEqual(relevant[0]["category"], "soc_lab")

    def test_secret_filter_blocks_credentials(self):
        with self.assertRaises(ValueError):
            memory.add_memory("OPENAI_API_KEY=sk-thisshouldnotbesaved1234567890")

    def test_brain_remember_command_saves_memory_without_openai(self):
        response = ask_wensday("remember DJ prefers clear step-by-step explanations")

        self.assertIn("Memory saved", response)
        saved = memory.search_memories("step-by-step")
        self.assertEqual(len(saved), 1)

    def test_brain_does_not_save_normal_chat_when_openai_missing(self):
        old_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            response = ask_wensday("hello normal chat")
        finally:
            if old_key is not None:
                os.environ["OPENAI_API_KEY"] = old_key

        self.assertIn("Wensday", response)
        self.assertFalse(self.memory_path.exists())

    def test_brain_search_and_forget_commands(self):
        ask_wensday("remember DJ is building Projekt Wensday")

        search_response = ask_wensday("search memory Projekt")
        self.assertIn("Projekt Wensday", search_response)

        forget_response = ask_wensday("forget Projekt Wensday")
        self.assertIn("Forgot 1", forget_response)
        self.assertEqual(memory.search_memories("Projekt"), [])

    def test_prompt_uses_relevant_memories(self):
        memory.add_memory("DJ's SOC lab uses Wazuh.", category="soc_lab")

        prompt = build_prompt("What should I check in Wazuh?")

        self.assertIn("Relevant long-term memories", prompt)
        self.assertIn("DJ's SOC lab uses Wazuh.", prompt)


if __name__ == "__main__":
    unittest.main()
