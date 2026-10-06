#!/usr/bin/env python3
import os
import sys
import signal
import unittest
from unittest.mock import MagicMock, patch

import gowatch


class TestGoWatchSmartDetection(unittest.TestCase):
    def test_custom_command_override(self):
        handler = gowatch.GoFileHandler.__new__(gowatch.GoFileHandler)
        handler.custom_command = ["go", "build", "-o", "bin/app"]
        handler.watch_dir = "/tmp/test"
        handler.check_mode = False
        handler.clear_screen_on_reload = True
        handler.lock = gowatch.threading.Lock()
        handler.process = None

        with patch.object(handler, '_stop_process_locked'), \
             patch('subprocess.Popen') as mock_popen, \
             patch('gowatch.clear_screen'):
            mock_proc = MagicMock()
            mock_proc.wait.return_value = 0
            mock_popen.return_value = mock_proc

            handler.run_trigger("foo_test.go")
            kwargs = {}
            if os.name != "nt" and hasattr(os, "setsid"):
                kwargs["preexec_fn"] = os.setsid
            mock_popen.assert_called_with(["go", "build", "-o", "bin/app"], shell=False, **kwargs)

    def test_smart_detection_test_file(self):
        handler = gowatch.GoFileHandler.__new__(gowatch.GoFileHandler)
        handler.custom_command = None
        handler.watch_dir = "/tmp/test"
        handler.check_mode = False
        handler.clear_screen_on_reload = True
        handler.lock = gowatch.threading.Lock()
        handler.process = None

        with patch.object(handler, '_stop_process_locked'), \
             patch('subprocess.Popen') as mock_popen, \
             patch('gowatch.clear_screen'):
            mock_proc = MagicMock()
            mock_proc.wait.return_value = 0
            mock_popen.return_value = mock_proc

            handler.run_trigger("/tmp/test/service_test.go")
            kwargs = {}
            if os.name != "nt" and hasattr(os, "setsid"):
                kwargs["preexec_fn"] = os.setsid
            mock_popen.assert_called_with(["go", "test", "-v", "./..."], shell=False, **kwargs)

    def test_smart_detection_normal_go_file(self):
        handler = gowatch.GoFileHandler.__new__(gowatch.GoFileHandler)
        handler.custom_command = None
        handler.watch_dir = "/tmp/test"
        handler.check_mode = False
        handler.clear_screen_on_reload = True
        handler.lock = gowatch.threading.Lock()
        handler.process = None

        with patch.object(handler, '_stop_process_locked'), \
             patch('subprocess.Popen') as mock_popen, \
             patch('gowatch.clear_screen'):
            mock_proc = MagicMock()
            mock_proc.wait.return_value = 0
            mock_popen.return_value = mock_proc

            handler.run_trigger("/tmp/test/main.go")
            kwargs = {}
            if os.name != "nt" and hasattr(os, "setsid"):
                kwargs["preexec_fn"] = os.setsid
            mock_popen.assert_called_with(["go", "run", "."], shell=False, **kwargs)

    def test_smart_detection_initial_startup(self):
        handler = gowatch.GoFileHandler.__new__(gowatch.GoFileHandler)
        handler.custom_command = None
        handler.watch_dir = "/tmp/test"
        handler.check_mode = False
        handler.clear_screen_on_reload = True
        handler.lock = gowatch.threading.Lock()
        handler.process = None

        with patch.object(handler, '_stop_process_locked'), \
             patch('subprocess.Popen') as mock_popen, \
             patch('gowatch.clear_screen'):
            mock_proc = MagicMock()
            mock_proc.wait.return_value = 0
            mock_popen.return_value = mock_proc

            handler.run_trigger(changed_file=None)
            kwargs = {}
            if os.name != "nt" and hasattr(os, "setsid"):
                kwargs["preexec_fn"] = os.setsid
            mock_popen.assert_called_with(["go", "run", "."], shell=False, **kwargs)

    def test_check_mode(self):
        handler = gowatch.GoFileHandler.__new__(gowatch.GoFileHandler)
        handler.custom_command = None
        handler.watch_dir = "/tmp/test"
        handler.check_mode = True
        handler.clear_screen_on_reload = True
        handler.lock = gowatch.threading.Lock()
        handler.process = None

        with patch.object(handler, '_stop_process_locked'), \
             patch('subprocess.Popen') as mock_popen, \
             patch('gowatch.clear_screen'):
            mock_proc = MagicMock()
            mock_proc.wait.return_value = 0
            mock_popen.return_value = mock_proc

            handler.run_trigger("/tmp/test/main.go")
            kwargs = {}
            if os.name != "nt" and hasattr(os, "setsid"):
                kwargs["preexec_fn"] = os.setsid
            mock_popen.assert_called_with(["go", "build", "-o", "/dev/null", "."], shell=False, **kwargs)

    def test_no_clear_option(self):
        handler = gowatch.GoFileHandler.__new__(gowatch.GoFileHandler)
        handler.custom_command = None
        handler.watch_dir = "/tmp/test"
        handler.check_mode = False
        handler.clear_screen_on_reload = False
        handler.lock = gowatch.threading.Lock()
        handler.process = None

        with patch.object(handler, '_stop_process_locked'), \
             patch('subprocess.Popen') as mock_popen, \
             patch('gowatch.clear_screen') as mock_clear:
            mock_proc = MagicMock()
            mock_proc.wait.return_value = 0
            mock_popen.return_value = mock_proc

            handler.run_trigger("/tmp/test/main.go")
            mock_clear.assert_not_called()

    def test_is_ignored_filtering(self):
        handler = gowatch.GoFileHandler.__new__(gowatch.GoFileHandler)
        handler.watch_dir = "/tmp/test"

        # Ignored directory events / paths
        self.assertTrue(handler._is_ignored("/tmp/test/.git/HEAD"))
        self.assertTrue(handler._is_ignored("/tmp/test/venv/lib/foo.go"))
        self.assertTrue(handler._is_ignored("/tmp/test/.venv/lib/foo.go"))
        self.assertTrue(handler._is_ignored("/tmp/test/__pycache__/foo.pyc"))
        self.assertTrue(handler._is_ignored("/tmp/test/bin/app"))
        self.assertTrue(handler._is_ignored("/tmp/test/.idea/workspace.xml"))
        self.assertTrue(handler._is_ignored("/tmp/test/.vscode/settings.json"))
        self.assertTrue(handler._is_ignored("/tmp/test/node_modules/pkg/index.go"))
        self.assertTrue(handler._is_ignored("/tmp/test/.hidden/file.go"))

        # Ignored temp files
        self.assertTrue(handler._is_ignored("/tmp/test/main.go~"))
        self.assertTrue(handler._is_ignored("/tmp/test/main.go.tmp"))
        self.assertTrue(handler._is_ignored("/tmp/test/main.go.swp"))
        self.assertTrue(handler._is_ignored("/tmp/test/main.tmp.123"))
        self.assertTrue(handler._is_ignored("/tmp/test/.main.go.swp"))

        # Valid files
        self.assertFalse(handler._is_ignored("/tmp/test/main.go"))
        self.assertFalse(handler._is_ignored("/tmp/test/pkg/utils.go"))
        self.assertFalse(handler._is_ignored("/tmp/test/pkg/utils_test.go"))

    def test_process_group_termination(self):
        handler = gowatch.GoFileHandler.__new__(gowatch.GoFileHandler)
        handler.lock = gowatch.threading.Lock()
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.pid = 12345
        handler.process = mock_proc

        with patch('os.getpgid', return_value=12345) as mock_getpgid, \
             patch('os.killpg') as mock_killpg:
            handler._stop_process_locked()
            mock_getpgid.assert_called_with(12345)
            mock_killpg.assert_called_with(12345, signal.SIGTERM)
            mock_proc.wait.assert_called()

    def test_restore_terminal(self):
        with patch('sys.stdout.write') as mock_write, \
             patch('sys.stdout.flush') as mock_flush:
            gowatch.restore_terminal()
            mock_write.assert_called_with("\033[0m\033[?25h")
            mock_flush.assert_called()


if __name__ == "__main__":
    unittest.main()

