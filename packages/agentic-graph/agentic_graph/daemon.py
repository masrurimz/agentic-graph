import argparse
import sys
import time
from pathlib import Path
from queue import Queue
from threading import Thread, Timer

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from agentic_graph.client import sync


class ChangeHandler(FileSystemEventHandler):
    IGNORED = {
        ".git",
        ".venv",
        ".cognee_data",
        ".cognee_system",
        ".enola",
        "__pycache__",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
    }
    IGNORED_SUFFIXES = (".pyc", ".pyo", ".so", ".dylib", ".dll")
    SOURCE_SUFFIXES = (
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".md",
        ".mdx",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".sql",
        ".rs",
        ".go",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
    )

    def __init__(self, repo_path: str, debounce_seconds: float = 2.0, queue: Queue | None = None):
        self.repo_path = repo_path
        self.debounce = debounce_seconds
        self._queue = queue or Queue()
        self._timer: Timer | None = None
        self._last_event = 0.0

    def _should_ignore(self, path: str) -> bool:
        p = Path(path)
        if any(part in self.IGNORED for part in p.parts):
            return True
        if p.is_dir():
            return True
        if p.name.startswith("."):
            return True
        if p.suffix in self.IGNORED_SUFFIXES:
            return True
        if not p.suffix:
            return True
        if p.suffix not in self.SOURCE_SUFFIXES:
            return True
        return False

    def on_any_event(self, event):
        if self._should_ignore(event.src_path):
            return
        now = time.time()
        if now - self._last_event < 0.05:
            return
        self._last_event = now

        if self._timer is not None:
            self._timer.cancel()

        def _run_sync():
            print(f"syncing after change: {event.src_path} ({event.event_type})", flush=True)
            self._queue.put((self.repo_path, False))

        self._timer = Timer(self.debounce, _run_sync)
        self._timer.daemon = True
        self._timer.start()


def _sync_worker(queue: Queue) -> None:
    while True:
        item = queue.get()
        if item is None:
            break
        repo_path, force = item
        try:
            sync(repo_path, force=force)
            print("sync ok" + (" (force)" if force else ""), flush=True)
        except Exception as exc:
            print(f"sync failed: {exc}", file=sys.stderr, flush=True)
        finally:
            queue.task_done()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("repo_path", default=".", nargs="?")
    parser.add_argument("--debounce", type=float, default=2.0)
    args = parser.parse_args()

    queue: Queue = Queue()
    worker = Thread(target=_sync_worker, args=(queue,), daemon=True)
    worker.start()

    # Prime the graph with a full re-index before watching.
    queue.put((args.repo_path, True))

    handler = ChangeHandler(args.repo_path, args.debounce, queue=queue)
    observer = Observer()
    observer.schedule(handler, args.repo_path, recursive=True)
    observer.start()
    print(f"watching {args.repo_path}", flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    queue.put(None)
    worker.join(timeout=5)


if __name__ == "__main__":
    main()
