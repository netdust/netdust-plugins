"""
test_stop_hook_root.py — the Stop hook writes memory/ at the PROJECT ROOT, however
deep the shell's cwd is, and never below a vendor segment.

Found 2026-09-02: seventeen stray memory/.stop-hook-state.json under themes/, plugins/,
vendor/ and packages/ across ~/Sites — every one a session that had `cd`'d before it
stopped. The hook now walks up from cwd to the nearest CLAUDE.md / site.yml / .git,
stopping at $HOME. Runs the real hook via subprocess with a fake $HOME. No mocks.
"""
import json
import shutil
import tempfile
from pathlib import Path

from hook_test_utils import msg as _msg, write_transcript as _write, run_stop_hook as _run


def _home() -> Path:
    return Path(tempfile.mkdtemp(prefix="netdust-home-"))


def _transcript(home: Path) -> Path:
    t = home / "t.jsonl"
    _write(t, [_msg("user", "go", "u1"), _msg("assistant", "DECISION: keep it\n", "a1")])
    return t


def test_deep_cwd_lands_at_root() -> tuple[bool, str]:
    home = _home()
    root = home / "Sites" / "proj"; (root / "a" / "b" / "c").mkdir(parents=True)
    (root / "site.yml").write_text("site: {}\n")
    r = _run(root / "a" / "b" / "c", _transcript(home), {"HOME": str(home)})
    ok = (root / "memory" / ".stop-hook-state.json").exists() and not (root / "a" / "b" / "c" / "memory").exists()
    shutil.rmtree(home, ignore_errors=True)
    return ok, f"cwd three levels down → sidecar at <root>/memory/, none at cwd (rc={r.returncode})"


def test_git_under_vendor_is_not_a_root() -> tuple[bool, str]:
    home = _home()
    root = home / "Sites" / "proj"; (root / "vendor" / "x" / ".git").mkdir(parents=True)
    (root / "CLAUDE.md").write_text("# proj\n")
    _run(root / "vendor" / "x", _transcript(home), {"HOME": str(home)})
    ok = (root / "memory" / ".stop-hook-state.json").exists() and not (root / "vendor" / "x" / "memory").exists()
    shutil.rmtree(home, ignore_errors=True)
    return ok, "a .git inside vendor/x is skipped; the sidecar lands at the project root"


def test_no_root_writes_nothing() -> tuple[bool, str]:
    home = _home()
    cwd = home / "scratch" / "vendor" / "deep"; cwd.mkdir(parents=True)
    r = _run(cwd, _transcript(home), {"HOME": str(home)})
    written = list(home.rglob(".stop-hook-state.json"))
    ok = r.returncode == 0 and not written
    shutil.rmtree(home, ignore_errors=True)
    return ok, f"below vendor/ with no marker up to $HOME → exit 0, nothing written ({len(written)} sidecars found)"


def test_bare_dir_is_still_a_project() -> tuple[bool, str]:
    home = _home()
    cwd = home / "fresh"; cwd.mkdir()
    _run(cwd, _transcript(home), {"HOME": str(home)})
    ok = (cwd / "memory" / ".stop-hook-state.json").exists()
    shutil.rmtree(home, ignore_errors=True)
    return ok, "a marker-less cwd outside any vendor segment keeps today's behaviour (memory/ at cwd)"


def run() -> list[tuple[bool, str]]:
    return [test_deep_cwd_lands_at_root(), test_git_under_vendor_is_not_a_root(), test_no_root_writes_nothing(), test_bare_dir_is_still_a_project()]


if __name__ == "__main__":
    for ok, d in run():
        print(("pass" if ok else "FAIL"), d)
