"""Unit tests for the helper functions in utils.py."""

import json
import tempfile
import unittest
from pathlib import Path

from agent import Agent
from utils import load_config, load_memory, save_json, validate_input


class TestLoadConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.dir_path = Path(self.temp_dir.name)

    def test_loads_valid_config(self):
        config_path = self.dir_path / "config.json"
        config_path.write_text(
            json.dumps({"agent_name": "Loaded Agent"}), encoding="utf-8"
        )
        config = load_config(config_path)
        self.assertEqual(config["agent_name"], "Loaded Agent")

    def test_missing_file_raises_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            load_config(self.dir_path / "missing.json")

    def test_invalid_json_raises_value_error(self):
        config_path = self.dir_path / "broken.json"
        config_path.write_text("{not valid json", encoding="utf-8")
        with self.assertRaises(ValueError):
            load_config(config_path)

    def test_non_object_json_raises_value_error(self):
        config_path = self.dir_path / "list.json"
        config_path.write_text("[1, 2, 3]", encoding="utf-8")
        with self.assertRaises(ValueError):
            load_config(config_path)


class TestJsonPersistence(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.dir_path = Path(self.temp_dir.name)

    def test_save_and_load_round_trip(self):
        target = self.dir_path / "nested" / "memory.json"
        save_json(target, {"memory_1": "A fact"})
        self.assertEqual(load_memory(target), {"memory_1": "A fact"})

    def test_load_memory_missing_file_returns_empty_dict(self):
        self.assertEqual(load_memory(self.dir_path / "missing.json"), {})

    def test_load_memory_corrupt_file_returns_empty_dict(self):
        target = self.dir_path / "corrupt.json"
        target.write_text("{broken", encoding="utf-8")
        self.assertEqual(load_memory(target), {})

    def test_load_memory_non_object_returns_empty_dict(self):
        target = self.dir_path / "list.json"
        target.write_text("[1, 2]", encoding="utf-8")
        self.assertEqual(load_memory(target), {})


class TestAgentPersistence(unittest.TestCase):
    """Memory saved through the Agent survives a restart."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.memory_path = str(Path(self.temp_dir.name) / "memory.json")

    def test_memory_survives_a_new_agent_instance(self):
        config = {"memory_file": self.memory_path}
        first_agent = Agent(config)
        first_agent.process_input("/remember The metro opens at 5am")

        second_agent = Agent(config)
        self.assertIn(
            "The metro opens at 5am", second_agent.memory.values()
        )

    def test_forget_all_clears_the_saved_file(self):
        config = {"memory_file": self.memory_path}
        agent = Agent(config)
        agent.process_input("/remember Temporary fact")
        agent.process_input("/forget all")
        self.assertEqual(load_memory(self.memory_path), {})


class TestValidateInput(unittest.TestCase):
    def test_accepts_normal_text(self):
        self.assertTrue(validate_input("hello"))

    def test_rejects_empty_and_whitespace_strings(self):
        self.assertFalse(validate_input(""))
        self.assertFalse(validate_input("   "))

    def test_rejects_non_string_values(self):
        self.assertFalse(validate_input(None))
        self.assertFalse(validate_input(42))


if __name__ == "__main__":
    unittest.main()
