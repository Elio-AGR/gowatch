#!/usr/bin/env python3
"""
gowatch - Go Hot-Reloading CLI Tool
Monitors Go source code changes and triggers reload commands with smart detection & clean terminal UI.
"""

import sys
import os
import time
import signal
import subprocess
import threading
import argparse
import atexit
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ANSI Color Codes
CYAN = "\033[36m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Directories to ignore
IGNORED_DIRS = {
    ".git",
    "venv",
    ".venv",
    "__pycache__",
    "bin",
    ".idea",
    ".vscode",
    "node_modules",
}


def clear_screen():
    """Clears the terminal screen."""
    os.system("clear" if os.name != "nt" else "cls")
    sys.stdout.write("\033[H")
    sys.stdout.flush()


def restore_terminal():
    """Restores ANSI styles and ensures cursor is visible on exit."""
    sys.stdout.write("\033[0m\033[?25h")
    sys.stdout.flush()


atexit.register(restore_terminal)


class GoFileHandler(FileSystemEventHandler):
    def __init__(
        self,
        debounce_interval=0.3,
        custom_command=None,
        watch_dir=".",
        check_mode=False,
        clear_screen_on_reload=True,
    ):
        super().__init__()
        self.debounce_interval = debounce_interval
        self.custom_command = custom_command
        self.watch_dir = os.path.abspath(watch_dir)
        self.check_mode = check_mode
        self.clear_screen_on_reload = clear_screen_on_reload
        self.timer = None
        self.lock = threading.Lock()
        self.process = None

        # Trigger initial run on startup
        self.run_trigger(changed_file=None)

    def _is_ignored(self, filepath):
        if not filepath:
            return True

        try:
            rel_path = os.path.relpath(filepath, self.watch_dir)
        except ValueError:
            rel_path = filepath

        parts = rel_path.split(os.sep)

        # Check directory components
        for part in parts[:-1]:
            if part.startswith(".") or part in IGNORED_DIRS:
                return True

        filename = parts[-1]
        # Check filename for ignored directories or hidden files/folders
        if filename.startswith(".") or filename in IGNORED_DIRS:
            return True

        # Check temporary editor files (~, .tmp, .swp, .tmp.*)
        if (
            filename.endswith("~")
            or filename.endswith(".tmp")
            or filename.endswith(".swp")
            or ".tmp." in filename
        ):
            return True

        return False

    def on_any_event(self, event):
        # Ignore directory events
        if getattr(event, 'is_directory', False):
            return

        # Ignore non-modification events like opened/closed if present in watchdog
        if getattr(event, 'event_type', '') in ('opened', 'closed'):
            return

        src_path = getattr(event, 'src_path', '')
        dest_path = getattr(event, 'dest_path', '')

        if src_path and self._is_ignored(src_path):
            return
        if dest_path and self._is_ignored(dest_path):
            return

        # Filter: only files ending with .go
        if (src_path and src_path.endswith('.go')) or (dest_path and dest_path.endswith('.go')):
            changed_file = dest_path if (dest_path and dest_path.endswith('.go')) else src_path
            self._schedule_debounce(changed_file)

    def _schedule_debounce(self, filepath):
        with self.lock:
            if self.timer is not None:
                self.timer.cancel()
            self.timer = threading.Timer(
                self.debounce_interval, self._on_debounced_change, args=[filepath]
            )
            self.timer.start()

    def _on_debounced_change(self, filepath):
        self.run_trigger(filepath)

    def run_trigger(self, changed_file=None):
        with self.lock:
            # 1. Clear terminal screen if configured
            if getattr(self, 'clear_screen_on_reload', True):
                clear_screen()

            # 2. Header / Status with Timestamp (Cyan)
            timestamp = time.strftime("%H:%M:%S")
            rel_watch = os.path.relpath(self.watch_dir)
            display_dir = "./..." if rel_watch == "." else f"{rel_watch}/..."
            print(f"{BOLD}{CYAN}[{timestamp}] [gowatch] Watching {display_dir}{RESET}", flush=True)

            # 3. File Changed log (Yellow)
            if changed_file:
                rel_path = os.path.relpath(changed_file, self.watch_dir)
                print(f"{BOLD}{YELLOW}[gowatch] File changed: {rel_path}{RESET}", flush=True)

            # 4. Smart Command Detection or Custom Command / Check Mode
            if getattr(self, 'check_mode', False):
                cmd = ["go", "build", "-o", "/dev/null", "."]
            elif self.custom_command:
                cmd = self.custom_command
            else:
                if changed_file and changed_file.endswith("_test.go"):
                    cmd = ["go", "test", "-v", "./..."]
                else:
                    cmd = ["go", "run", "."]

            cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
            print(f"{CYAN}[gowatch] Executing: {cmd_str}{RESET}\n", flush=True)

            # 5. Stop existing process if running
            self._stop_process_locked()

            # 6. Start new process in its own Process Group & monitor thread
            start_time = time.perf_counter()
            try:
                kwargs = {}
                if os.name != "nt" and hasattr(os, "setsid"):
                    kwargs["preexec_fn"] = os.setsid

                proc = subprocess.Popen(cmd, shell=isinstance(cmd, str), **kwargs)
                self.process = proc

                t = threading.Thread(
                    target=self._monitor_process,
                    args=(proc, start_time),
                    daemon=True
                )
                t.start()
            except Exception as e:
                print(f"{BOLD}{RED}[gowatch] Error starting process: {e}{RESET}", file=sys.stderr, flush=True)
                self.process = None

    def _stop_process_locked(self):
        if self.process and self.process.poll() is None:
            proc = self.process
            self.process = None  # Disassociate so monitor thread ignores exit status
            pid = proc.pid

            killed_pgroup = False
            if hasattr(os, "killpg") and hasattr(os, "getpgid"):
                try:
                    pgid = os.getpgid(pid)
                    os.killpg(pgid, signal.SIGTERM)
                    killed_pgroup = True
                except (ProcessLookupError, OSError):
                    pass

            if not killed_pgroup:
                try:
                    proc.terminate()
                except (ProcessLookupError, OSError):
                    pass

            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                if hasattr(os, "killpg") and hasattr(os, "getpgid"):
                    try:
                        pgid = os.getpgid(pid)
                        os.killpg(pgid, signal.SIGKILL)
                    except (ProcessLookupError, OSError):
                        pass
                try:
                    proc.kill()
                except (ProcessLookupError, OSError):
                    pass
                try:
                    proc.wait(timeout=1.0)
                except Exception:
                    pass

    def _monitor_process(self, proc, start_time):
        try:
            retcode = proc.wait()
        except Exception:
            return

        with self.lock:
            if self.process != proc:
                return  # Process was superseded by another trigger or stopped

        elapsed = time.perf_counter() - start_time
        if elapsed < 1.0:
            duration_str = f"{int(elapsed * 1000)}ms"
        else:
            duration_str = f"{elapsed:.2f}s"

        if retcode == 0:
            print(f"\n{BOLD}{GREEN}[gowatch] Command succeeded (exit code 0) - Finished in {duration_str}{RESET}", flush=True)
        else:
            print(f"\n{BOLD}{RED}[gowatch] Command failed (exit code {retcode}) - Finished in {duration_str}{RESET}", flush=True)

    def shutdown(self):
        with self.lock:
            if self.timer is not None:
                self.timer.cancel()
            self._stop_process_locked()


def main():
    parser = argparse.ArgumentParser(
        description="gowatch - Hot-reloading CLI for Go projects"
    )
    parser.add_argument(
        "-d", "--dir", default=".", help="Directory to watch (default: current working directory)"
    )
    parser.add_argument(
        "-b", "--debounce", type=float, default=0.3, help="Debounce timeout in seconds (default: 0.3)"
    )
    parser.add_argument(
        "-c", "--check", action="store_true", help="Execute 'go build -o /dev/null .' on change (TUI mode / dry check)"
    )
    parser.add_argument(
        "--no-clear", action="store_true", help="Do not clear terminal screen automatically"
    )
    parser.add_argument(
        "cmd", nargs="*", help="Optional custom command to execute on change (e.g. go build .)"
    )

    args = parser.parse_args()
    watch_directory = os.path.abspath(args.dir)
    custom_command = args.cmd if args.cmd else None

    event_handler = GoFileHandler(
        debounce_interval=args.debounce,
        custom_command=custom_command,
        watch_dir=watch_directory,
        check_mode=args.check,
        clear_screen_on_reload=not args.no_clear,
    )
    observer = Observer()
    observer.schedule(event_handler, path=watch_directory, recursive=True)

    def signal_handler(sig, frame):
        print(f"\n{CYAN}[gowatch] Shutting down watcher...{RESET}", flush=True)
        event_handler.shutdown()
        if observer.is_alive():
            observer.stop()
            observer.join(timeout=1.0)
        restore_terminal()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    observer.start()

    try:
        while observer.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        signal_handler(None, None)
    finally:
        restore_terminal()


if __name__ == "__main__":
    main()

