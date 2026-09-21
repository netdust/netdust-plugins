"""
test_stop_hook_symlink.py — the Stop hook's tag writers never write through a symlink out
of the project root. A cloned repo can ship memory/lessons.md -> ~/.bashrc; a tag the agent
emits must not be appended to the link's target.
"""
import shutil
import tempfile
from pathlib import Path

from hook_test_utils import msg as _msg, write_transcript as _write, run_stop_hook as _run

TAGS = "DECISION: keep it\nLESSON: watch links\nTODO: check links\n"


def _project(home: Path) -> Path:
    root = home / "Sites" / "proj"
    (root / "memory").mkdir(parents=True)
    (root / "tasks").mkdir()
    (root / "site.yml").write_text("site: {}\n")
    return root


def _drive(home: Path, root: Path) -> None:
    t = home / "t.jsonl"
    _write(t, [_msg("user", "go", "u1"), _msg("assistant", TAGS, "a1")])
    _run(root, t, {"HOME": str(home)})


def test_file_symlinks_are_not_followed() -> tuple[bool, str]:
    home = Path(tempfile.mkdtemp(prefix="netdust-home-"))
    root = _project(home)
    outside = {n: home / f"outside-{n}" for n in ("state", "lessons", "todo")}
    for path in outside.values():
        path.write_text("ORIGINAL\n")
    (root / "memory" / "STATE.md").symlink_to(outside["state"])
    (root / "memory" / "lessons.md").symlink_to(outside["lessons"])
    (root / "tasks" / "todo.md").symlink_to(outside["todo"])
    _drive(home, root)
    untouched = all(p.read_text() == "ORIGINAL\n" for p in outside.values())
    shutil.rmtree(home, ignore_errors=True)
    return untouched, "STATE.md / lessons.md / todo.md symlinked out of the root are left untouched"


def test_directory_symlink_is_not_followed() -> tuple[bool, str]:
    home = Path(tempfile.mkdtemp(prefix="netdust-home-"))
    root = _project(home)
    shutil.rmtree(root / "memory")
    elsewhere = home / "elsewhere"
    elsewhere.mkdir()
    (root / "memory").symlink_to(elsewhere)
    _drive(home, root)
    leaked = [p.name for p in elsewhere.iterdir() if p.name in ("STATE.md", "lessons.md")]
    shutil.rmtree(home, ignore_errors=True)
    return not leaked, f"a memory/ directory symlinked out of the root receives no tag capture (leaked {leaked})"


def test_ordinary_capture_still_lands() -> tuple[bool, str]:
    home = Path(tempfile.mkdtemp(prefix="netdust-home-"))
    root = _project(home)
    _drive(home, root)
    landed = ("keep it" in (root / "memory" / "STATE.md").read_text()
              and "watch links" in (root / "memory" / "lessons.md").read_text()
              and "check links" in (root / "tasks" / "todo.md").read_text())
    shutil.rmtree(home, ignore_errors=True)
    return landed, "without symlinks the DECISION / LESSON / TODO tags land in the project as before"


def run() -> list[tuple[bool, str]]:
    return [test_file_symlinks_are_not_followed(), test_directory_symlink_is_not_followed(),
            test_ordinary_capture_still_lands()]


if __name__ == "__main__":
    for ok, d in run():
        print(("pass" if ok else "FAIL"), d)
