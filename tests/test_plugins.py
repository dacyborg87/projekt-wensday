import unittest

from wensday_core.orchestrator import WensdayRequest
from wensday_core.plugins import PluginRegistry, PluginResult


class ReadOnlyPlugin:
    name = "test_plugin"
    request_types = {"soc_summary"}
    read_only = True

    def can_handle(self, request):
        return True

    def run(self, request):
        return PluginResult(handled=True, answer="plugin handled", evidence=["sample"])


class WritePlugin:
    name = "write_plugin"
    request_types = {"soc_summary"}
    read_only = False

    def can_handle(self, request):
        return True

    def run(self, request):
        return PluginResult(handled=True, answer="should not run")


class PluginsTestCase(unittest.TestCase):
    def test_read_only_plugin_can_register_and_route(self):
        registry = PluginRegistry()
        registry.register(ReadOnlyPlugin())

        result = registry.route(WensdayRequest("summarize alerts", request_type="soc_summary"))

        self.assertTrue(result.handled)
        self.assertEqual(result.answer, "plugin handled")
        self.assertEqual(result.plugin_name, "test_plugin")

    def test_write_plugin_rejected(self):
        registry = PluginRegistry()

        with self.assertRaises(ValueError):
            registry.register(WritePlugin())

    def test_unknown_request_not_handled(self):
        registry = PluginRegistry()
        registry.register(ReadOnlyPlugin())

        result = registry.route(WensdayRequest("hello", request_type="general_chat"))

        self.assertFalse(result.handled)


if __name__ == "__main__":
    unittest.main()
