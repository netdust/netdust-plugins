"""test_revert_run.py — bin/revert-run runs ONE test with the branch's changed non-test files swapped
back to the base in the working tree only (the index never leaves HEAD), restores the tree on every
exit and verifies it, marks a swap in progress in .git/revert-run.swapped so a killed run is found,
and writes a classified log the checker reads. Every case builds its own scratch git repo under a
temp dir — never a real checkout."""
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "bin" / "revert-run"
SENTINEL = ".git/revert-run.swapped"
TEST_PATH, TITLE = "tests/e2e/x.spec.ts", "credits heading @e2e"
STEM = "tests__e2e__x.spec.ts--credits-heading-e2e"
# The same title test_shakeout_check.py derives: the stem is one rule in two languages.
ODD_TITLE, ODD_STEM = "Crédits: 2 × 3 @e2e", "tests__e2e__x.spec.ts--cr-dits-2-3-e2e"
PW_FAIL = ("  1) [chromium] › tests/e2e/x.spec.ts:12:5 › credits heading @e2e\n\n"
           "    Error: expect(locator).toBeVisible() failed\n\n"
           "    Locator:  getByRole('heading', { name: 'Credits' })\n"
           "    Expected: visible\n    Received: <element(s) not found>\n    Timeout:  5000ms\n")
PW_TIMEOUT = ("    TimeoutError: locator.click: Timeout 5000ms exceeded.\n"
              "    Call log:\n      - waiting for getByRole('button', { name: 'Save' })\n")
PHPUNIT_FAIL = "1) RowsTest::testCount\nFailed asserting that 2 matches expected 3.\n"
SWAPPED = ("src/a.txt", "src/new.txt", "src/old.txt", "src/r1.txt", "src/r2.txt", "src/-x y.txt", "src/link.txt",
           "src/a[1].txt", "old/deep/x.txt")


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=T", *args],
                          capture_output=True, text=True, check=True).stdout


def _write(repo: Path, rel: str, text: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def _repo(root: Path) -> Path:
    """main: seven files; feature: one changed, one added, one deleted, one renamed, one with a leading
    dash changed, one file turned symlink, one with glob characters in its name changed, one deleted
    with its whole directory, plus a test and a spec added (never swapped)."""
    repo = root / "proj"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main", ".")
    for rel, text in (("src/a.txt", "base a\n"), ("src/old.txt", "old\n"), ("src/r1.txt", "r\n"),
                      ("src/-x y.txt", "base dash\n"), ("src/link.txt", "plain file\n"), ("README", "readme\n"),
                      ("src/a[1].txt", "base glob\n"), ("old/deep/x.txt", "gone\n")):
        _write(repo, rel, text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    _git(repo, "checkout", "-qb", "feature/feat")
    _write(repo, "src/a.txt", "feature a\n")
    _write(repo, "src/new.txt", "new\n")
    (repo / "src/old.txt").unlink()
    (repo / "src/r1.txt").rename(repo / "src/r2.txt")
    _write(repo, "src/-x y.txt", "feature dash\n")
    (repo / "src/link.txt").unlink()
    (repo / "src/link.txt").symlink_to("a.txt")
    _write(repo, "src/a[1].txt", "feature glob\n")
    (repo / "old/deep/x.txt").unlink()
    (repo / "old/deep").rmdir()
    (repo / "old").rmdir()
    _write(repo, "tests/t.sh", "echo t\n")
    _write(repo, "specs/feat/plan.md", "plan\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "feature")
    return repo


def _snapshot(repo: Path) -> dict:
    out = {}
    for rel in SWAPPED + ("tests/t.sh", "specs/feat/plan.md", "README"):
        p = repo / rel
        if p.is_symlink():
            out[rel] = ("link", os.readlink(p))
        elif p.is_file():
            out[rel] = ("file", p.read_bytes())
        else:
            out[rel] = ("absent", None)
    return out


def _run(repo: Path, cmd: str, *, title=TITLE, path=TEST_PATH, feature="feat", timeout=60):
    if not SCRIPT.exists():
        return 127, "", f"no script at {SCRIPT}", ""
    proc = subprocess.run([str(SCRIPT), feature, path, title, "--", "bash", "-c", cmd],
                          cwd=repo, capture_output=True, text=True, timeout=timeout)
    logs = sorted((repo / "specs" / feature / "shakeout").glob("*.revert.txt")) \
        if (repo / "specs" / feature / "shakeout").is_dir() else []
    log = logs[0].read_text() if logs else ""
    return proc.returncode, proc.stdout, proc.stderr, log


def _recording_cmd(rec: Path, tail: str) -> str:
    """A test command that records the tree it sees, then runs `tail` (its exit is the command's)."""
    return (f"git status --porcelain > '{rec}/status'; ls src > '{rec}/ls'; cat src/a.txt > '{rec}/a'; "
            f"cat 'src/-x y.txt' > '{rec}/dash'; (test -L src/link.txt && echo link || cat src/link.txt) > '{rec}/link'; "
            f"cat 'src/a[1].txt' > '{rec}/glob'; ls tests specs/feat > '{rec}/kept' 2>&1; {tail}")


def _start(repo: Path, rec: Path, cmd: str) -> subprocess.Popen:
    """revert-run in its own session running `cmd`, returned once the command has touched rec/started."""
    proc = subprocess.Popen([str(SCRIPT), "feat", TEST_PATH, TITLE, "--", "bash", "-c", cmd],
                            cwd=repo, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    deadline = time.time() + 10
    while not (rec / "started").exists() and time.time() < deadline and proc.poll() is None:
        time.sleep(0.05)
    return proc


def _recovery(err: str) -> str:
    """The `recover:` line revert-run prints when the base's files are left in the tree."""
    return next((ln.split("recover: ", 1)[1] for ln in err.splitlines() if "recover: " in ln), "")


def _index_is_head(repo: Path) -> bool:
    return _git(repo, "diff", "--cached", "--name-only").strip() == ""


def _case(name: str, fn) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="revert-run-") as tmp:
        root = Path(tmp)
        repo = _repo(root)
        rec = root / "rec"
        rec.mkdir()
        try:
            ok, why = fn(repo, rec)
        except Exception as e:  # a crashed case is a failed case, with its reason
            ok, why = False, f"{e.__class__.__name__}: {e}"
    return ok, f"{name}{'' if ok else ' — ' + why}"


def _clean(repo: Path) -> bool:
    """The tree equals HEAD; the log the script writes is the one new file allowed."""
    return _git(repo, "status", "--porcelain", "--", ".", ":(exclude)specs/feat/shakeout").strip() == ""


# ── cases ──────────────────────────────────────────────────────────────────────

def _assertion_failed(repo, rec):
    (rec / "out.txt").write_text(PW_FAIL)
    rc, _, err, log = _run(repo, f"cat '{rec}/out.txt'; exit 1")
    path = repo / "specs/feat/shakeout" / f"{STEM}.revert.txt"
    return (rc == 0 and path.is_file() and log.startswith("revert-run: assertion-failed\n")
            and "Expected: visible" in log and "exit: 1" in log and _clean(repo),
            f"rc {rc}, log at {path.name if path.is_file() else 'nowhere'}, head {log[:40]!r}, err {err[-200:]!r}")


def _phpunit(repo, rec):
    (rec / "out.txt").write_text(PHPUNIT_FAIL)
    rc, _, err, log = _run(repo, f"cat '{rec}/out.txt'; exit 1")
    return rc == 0 and log.startswith("revert-run: assertion-failed\n") and _clean(repo), f"rc {rc}, head {log[:40]!r}, err {err[-200:]!r}"


def _timeout(repo, rec):
    (rec / "out.txt").write_text(PW_TIMEOUT)
    rc, _, err, log = _run(repo, f"cat '{rec}/out.txt'; exit 1")
    return rc == 0 and log.startswith("revert-run: error\n") and "locator.click" in log and _clean(repo), \
        f"rc {rc}, head {log[:40]!r}, err {err[-200:]!r}"


def _passed(repo, rec):
    rc, _, err, log = _run(repo, "echo '1 passed'; exit 0")
    return rc == 0 and log.startswith("revert-run: passed\n") and "exit: 0" in log and _clean(repo), \
        f"rc {rc}, head {log[:40]!r}, err {err[-200:]!r}"


def _round_trip(repo, rec):
    before = _snapshot(repo)
    rc, _, err, log = _run(repo, _recording_cmd(rec, "exit 0"))
    seen = (rec / "ls").read_text().split() if (rec / "ls").is_file() else []
    during_ok = (seen and "old.txt" in seen and "r1.txt" in seen and "new.txt" not in seen and "r2.txt" not in seen
                 and (rec / "a").read_text() == "base a\n" and (rec / "dash").read_text() == "base dash\n")
    after_ok = _snapshot(repo) == before and _clean(repo)
    return rc == 0 and during_ok and after_ok, \
        f"rc {rc}, during ls={seen}, after clean={_clean(repo)}, same={_snapshot(repo) == before}, err {err[-200:]!r}"


def _refuses_modified(repo, rec):
    (repo / "src/a.txt").write_text("edited, not committed\n")
    rc, out, err, log = _run(repo, _recording_cmd(rec, "exit 1"))
    nothing_ran = not (rec / "status").exists()
    return (rc == 2 and "src/a.txt" in err + out and log == "" and nothing_ran
            and (repo / "src/a.txt").read_text() == "edited, not committed\n"
            and (repo / "src/new.txt").is_file() and not (repo / "src/old.txt").exists(),
            f"rc {rc}, ran={not nothing_ran}, log={bool(log)}, err {err[-200:]!r}")


def _refuses_untracked_at_deleted(repo, rec):
    (repo / "src/old.txt").write_text("someone's scratch\n")
    rc, out, err, log = _run(repo, _recording_cmd(rec, "exit 1"))
    return (rc == 2 and "src/old.txt" in err + out and log == "" and not (rec / "status").exists()
            and (repo / "src/old.txt").read_text() == "someone's scratch\n",
            f"rc {rc}, err {err[-200:]!r}")


def _typechange(repo, rec):
    rc, _, err, log = _run(repo, _recording_cmd(rec, "exit 0"))
    during = (rec / "link").read_text() if (rec / "link").is_file() else ""
    after_link = (repo / "src/link.txt").is_symlink() and os.readlink(repo / "src/link.txt") == "a.txt"
    return rc == 0 and during == "plain file\n" and after_link and _clean(repo), \
        f"rc {rc}, during {during!r}, symlink after={after_link}, err {err[-200:]!r}"


def _interrupt(repo, rec):
    if not SCRIPT.exists():
        return False, f"no script at {SCRIPT}"
    before = _snapshot(repo)
    cmd = f"touch '{rec}/started'; sleep 30"
    proc = subprocess.Popen([str(SCRIPT), "feat", TEST_PATH, TITLE, "--", "bash", "-c", cmd],
                            cwd=repo, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    deadline = time.time() + 10
    while not (rec / "started").exists() and time.time() < deadline and proc.poll() is None:
        time.sleep(0.05)
    swapped = (repo / "src/old.txt").exists() and not (repo / "src/new.txt").exists()
    os.killpg(proc.pid, signal.SIGINT)
    try:
        err = proc.communicate(timeout=15)[1]
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        return False, "revert-run did not exit after SIGINT"
    restored = _snapshot(repo) == before and _clean(repo)
    # a second restore is a no-op: a later run on the clean tree ends clean too
    rc2, _, err2, _ = _run(repo, "exit 0")
    return swapped and restored and rc2 == 0 and _clean(repo), \
        f"swapped during={swapped}, restored={restored}, rc after={rc2}, err {err[-200:]!r} {err2[-100:]!r}"


def _never_swaps_tests(repo, rec):
    rc, _, err, log = _run(repo, _recording_cmd(rec, "exit 0"))
    kept = (rec / "kept").read_text() if (rec / "kept").is_file() else ""
    swapped_lines = [ln for ln in log.splitlines() if ln.startswith("swapped:")]
    return (rc == 0 and "t.sh" in kept and "plan.md" in kept
            and not any("tests/" in ln or "specs/" in ln for ln in swapped_lines) and swapped_lines,
            f"rc {rc}, kept {kept!r}, swapped {swapped_lines}, err {err[-200:]!r}")


def _excerpt(repo, rec):
    lines = [f"line {i}" for i in range(1, 251)] + PW_FAIL.splitlines() + [f"line {i}" for i in range(251, 501)]
    (rec / "out.txt").write_text("\n".join(lines) + "\n")
    rc, _, err, log = _run(repo, f"cat '{rec}/out.txt'; exit 1")
    body = log.split("\n--- ", 1)[1] if "\n--- " in log else ""
    out_lines = [ln for ln in body.splitlines()[1:] if ln.strip()]
    return (rc == 0 and log.startswith("revert-run: assertion-failed\n") and "Error: expect(" in body
            and len(out_lines) <= 20 and "line 1\n" not in log and "line 500" not in log,
            f"rc {rc}, excerpt lines {len(out_lines)}, has marker={'Error: expect(' in body}, err {err[-200:]!r}")


def _stem(repo, rec):
    (rec / "out.txt").write_text(PW_FAIL)
    rc, _, err, _ = _run(repo, f"cat '{rec}/out.txt'; exit 1", title=ODD_TITLE)
    path = repo / "specs/feat/shakeout" / f"{ODD_STEM}.revert.txt"
    return rc == 0 and path.is_file(), f"rc {rc}, logs {[p.name for p in (repo / 'specs/feat/shakeout').glob('*')] if (repo / 'specs/feat/shakeout').is_dir() else []}, err {err[-200:]!r}"


def _not_ignored(repo, rec):
    """Every project ignores *.log (this repo, the devops gitignore template, most sites): the proof must survive git add."""
    (repo / ".gitignore").write_text("*.log\n")
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-qm", "ignore logs")
    (rec / "out.txt").write_text(PW_FAIL)
    rc, _, err, log = _run(repo, f"cat '{rec}/out.txt'; exit 1")
    written = next(iter((repo / "specs/feat/shakeout").glob("*.revert.*")), None)
    ignored = subprocess.run(["git", "-C", str(repo), "check-ignore", "-q", str(written)]).returncode == 0 if written else True
    return rc == 0 and written is not None and not ignored, \
        f"rc {rc}, log {written.name if written else None}, git-ignored={ignored}, err {err[-200:]!r}"


def _killed(repo, rec):
    """SIGKILL mid-run (OOM, power loss): the index is still HEAD's, .git/revert-run.swapped names the
    swap, the next run refuses with a recovery line, and that line restores the tree."""
    if not SCRIPT.exists():
        return False, f"no script at {SCRIPT}"
    proc = _start(repo, rec, f"echo $$ > '{rec}/pid'; touch '{rec}/started'; sleep 30")
    proc.kill()
    groups = [proc.pid]
    if (rec / "pid").is_file() and (rec / "pid").read_text().strip().isdigit():
        groups.append(int((rec / "pid").read_text()))
    for g in groups:
        if g > 1:
            try:
                os.killpg(g, signal.SIGKILL)
            except ProcessLookupError:
                pass
    proc.communicate(timeout=15)
    swapped = (repo / "src/a.txt").read_text() == "base a\n" and (repo / "src/old.txt").exists()
    index_ok, sentinel = _index_is_head(repo), (repo / SENTINEL).is_file()
    rc2, _, err2, log2 = _run(repo, "exit 0")
    refused = rc2 == 2 and log2 == "" and "recover: " in err2 and "src/a.txt" in err2 and "src/old.txt" in err2
    recovered = False
    if refused:
        subprocess.run(["bash", "-c", _recovery(err2)], cwd=repo, capture_output=True)
        recovered = _clean(repo) and not (repo / SENTINEL).exists()
    return swapped and index_ok and sentinel and refused and recovered, \
        f"swapped={swapped}, index untouched={index_ok}, sentinel={sentinel}, next run refused={refused}, recovered={recovered}, err {err2[-300:]!r}"


def _locked_restore(repo, rec):
    """The restore cannot take the index lock (another git holds it): no log, exit 2, the paths and a
    recovery line printed, the sentinel kept — never a silent `assertion-failed` over base code."""
    (rec / "out.txt").write_text(PW_FAIL)
    rc, out, err, log = _run(repo, f"cat '{rec}/out.txt'; touch .git/index.lock; exit 1")
    loud = rc == 2 and log == "" and "recover: " in err and "src/a.txt" in err
    sentinel = (repo / SENTINEL).is_file()
    (repo / ".git/index.lock").unlink(missing_ok=True)
    if loud:
        subprocess.run(["bash", "-c", _recovery(err)], cwd=repo, capture_output=True)
    return loud and sentinel and _clean(repo) and not (repo / SENTINEL).exists(), \
        f"rc {rc}, log written={bool(log)}, sentinel={sentinel}, clean after recovery={_clean(repo)}, err {err[-300:]!r}"


def _refuses_ignored_at_deleted(repo, rec):
    """git status hides ignored files: one at a path the branch deleted would be overwritten, then removed."""
    (repo / ".gitignore").write_text("src/old.txt\n")
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-qm", "ignore")
    (repo / "src/old.txt").write_text("ignored scratch\n")
    rc, out, err, log = _run(repo, _recording_cmd(rec, "exit 1"))
    return (rc == 2 and "src/old.txt" in err and log == "" and not (rec / "status").exists()
            and (repo / "src/old.txt").read_text() == "ignored scratch\n",
            f"rc {rc}, kept={(repo / 'src/old.txt').is_file() and (repo / 'src/old.txt').read_text() == 'ignored scratch' + chr(10)}, err {err[-200:]!r}")


def _refuses_file_to_directory_clash(repo, rec):
    """The base has src/thing as a file, HEAD as a directory: refused, or the base checkout removes the subtree."""
    clash = repo.parent / "clash"
    clash.mkdir()
    _git(clash, "init", "-q", "-b", "main", ".")
    _write(clash, "src/thing", "a file\n")
    _write(clash, "README", "r\n")
    _git(clash, "add", "-A")
    _git(clash, "commit", "-qm", "base")
    _git(clash, "checkout", "-qb", "feature/feat")
    (clash / "src/thing").unlink()
    _write(clash, "src/thing/inner.txt", "inner\n")
    _write(clash, ".gitignore", "*.cache\n")
    _git(clash, "add", "-A")
    _git(clash, "commit", "-qm", "feature")
    _write(clash, "src/thing/build.cache", "ignored\n")
    rc, out, err, log = _run(clash, "exit 1")
    return (rc == 2 and "src/thing" in err and log == "" and (clash / "src/thing/inner.txt").is_file()
            and (clash / "src/thing/build.cache").read_text() == "ignored\n",
            f"rc {rc}, inner kept={(clash / 'src/thing/inner.txt').is_file()}, err {err[-200:]!r}")


def _refuses_bad_feature(repo, rec):
    """<feature> is a directory name under specs/: a slash, `..`, a dash-led word or nothing is refused before any swap."""
    results = {}
    for feature in ("../escape", "a/b", "..", "-x", ""):
        rc, _, err, _ = _run(repo, "exit 1", feature=feature)
        results[feature] = rc == 2 and "revert-run: refused" in err
    return all(results.values()) and not (repo / "escape").exists() and not (repo / "specs/a").exists() \
        and not (repo / "specs/-x").exists() and _clean(repo), f"refused per name {results}"


def _interrupt_kills_the_grandchild(repo, rec):
    """SIGINT to revert-run alone: the command's own children (a browser) die with it, never outliving the restore."""
    if not SCRIPT.exists():
        return False, f"no script at {SCRIPT}"
    proc = _start(repo, rec, f"sleep 30 & echo $! > '{rec}/gpid'; touch '{rec}/started'; wait")
    os.kill(proc.pid, signal.SIGINT)
    try:
        err = proc.communicate(timeout=15)[1]
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        return False, "revert-run did not exit after SIGINT"
    gpid = int((rec / "gpid").read_text()) if (rec / "gpid").is_file() and (rec / "gpid").read_text().strip().isdigit() else 0
    alive, deadline = gpid > 1, time.time() + 3
    while alive and time.time() < deadline:
        try:
            os.kill(gpid, 0)
            time.sleep(0.05)
        except ProcessLookupError:
            alive = False
    if alive:
        try:
            os.kill(gpid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    return gpid > 1 and not alive and _clean(repo), f"grandchild {gpid} alive after exit={alive}, clean={_clean(repo)}, err {err[-200:]!r}"


def _submodule_not_swapped(repo, rec):
    """A gitlink the branch moved is listed as `not swapped:` — its content never was."""
    sub = repo.parent / "withsub"
    sub.mkdir()
    _git(sub, "init", "-q", "-b", "main", ".")
    _write(sub, "src/a.txt", "base\n")
    _git(sub, "add", "-A")
    _git(sub, "commit", "-qm", "base")
    sha = _git(sub, "rev-parse", "HEAD").strip()
    _git(sub, "update-index", "--add", "--cacheinfo", f"160000,{sha},vendor/sub")
    _git(sub, "commit", "-qm", "gitlink")
    _git(sub, "checkout", "-qb", "feature/feat")
    _write(sub, "src/a.txt", "feature\n")
    _git(sub, "add", "src/a.txt")
    _git(sub, "update-index", "--add", "--cacheinfo", f"160000,{'1' * 40},vendor/sub")
    _git(sub, "commit", "-qm", "feature")
    rc, _, err, log = _run(sub, "exit 0")
    lines = log.splitlines()
    # a gitlink with no checkout reads as ` D` in status, so the clean check leaves submodules out
    clean = _git(sub, "status", "--porcelain", "--ignore-submodules=all", "--", ".", ":(exclude)specs/feat/shakeout").strip() == ""
    return (rc == 0 and "not swapped: vendor/sub (submodule)" in lines and "swapped: src/a.txt (M)" in lines
            and not any(ln.startswith("swapped: vendor/sub") for ln in lines) and clean,
            f"rc {rc}, log lines {lines[:8]}, clean={clean}, err {err[-200:]!r}")


def _prunes_empty_dirs(repo, rec):
    """A deleted path's directory, recreated for the base's file, does not survive the restore (WordPress scans plugin dirs)."""
    rc, _, err, log = _run(repo, "exit 0")
    return rc == 0 and not (repo / "old").exists() and _clean(repo), \
        f"rc {rc}, old/ left={(repo / 'old').exists()}, err {err[-200:]!r}"


def _glob_in_a_tracked_path(repo, rec):
    """`src/a[1].txt` is tracked and changed, `src/a1.txt` an untracked sibling: literal pathspecs, no spurious refusal."""
    (repo / "src/a1.txt").write_text("sibling\n")
    rc, _, err, log = _run(repo, _recording_cmd(rec, "exit 0"))
    during = (rec / "glob").read_text() if (rec / "glob").is_file() else ""
    status = _git(repo, "status", "--porcelain", "--", ".", ":(exclude)specs/feat/shakeout").strip()
    return (rc == 0 and during == "base glob\n" and (repo / "src/a1.txt").read_text() == "sibling\n"
            and (repo / "src/a[1].txt").read_text() == "feature glob\n" and status == "?? src/a1.txt",
            f"rc {rc}, during {during!r}, status {status!r}, err {err[-200:]!r}")


def run() -> list[tuple[bool, str]]:
    return [
        _case("test_log_is_not_git_ignored: a repo ignoring *.log still tracks the proof revert-run writes", _not_ignored),
        _case("test_killed_run_leaves_the_index_and_a_sentinel: SIGKILL mid-run, the index is HEAD's, the next run refuses with a recovery line that works", _killed),
        _case("test_failed_restore_is_loud: a held index lock → no log, exit 2, the paths and the recovery line, the sentinel kept", _locked_restore),
        _case("test_refuses_on_an_ignored_file_at_a_deleted_path", _refuses_ignored_at_deleted),
        _case("test_refuses_a_file_to_directory_clash: a base file where HEAD has a directory is never checked out over it", _refuses_file_to_directory_clash),
        _case("test_refuses_a_feature_name_that_leaves_specs", _refuses_bad_feature),
        _case("test_interrupt_kills_the_grandchild: the command runs in its own process group and dies with it", _interrupt_kills_the_grandchild),
        _case("test_submodule_is_listed_not_swapped", _submodule_not_swapped),
        _case("test_restore_prunes_the_directories_it_recreated", _prunes_empty_dirs),
        _case("test_glob_characters_in_a_tracked_path_are_literal", _glob_in_a_tracked_path),
        _case("test_expect_on_a_missing_element_is_assertion_failed: Playwright's toBeVisible text + exit 1 → assertion-failed, log at the derived stem", _assertion_failed),
        _case("test_phpunit_failed_asserting_is_assertion_failed", _phpunit),
        _case("test_click_timeout_is_error: a locator.click timeout with no expect is error", _timeout),
        _case("test_test_that_passes_on_base_is_passed", _passed),
        _case("test_added_deleted_and_renamed_files_round_trip: the base layout during the run, HEAD's after, status clean", _round_trip),
        _case("test_refuses_on_a_modified_tracked_file: exit 2, the file named, nothing swapped, no log", _refuses_modified),
        _case("test_refuses_on_an_untracked_file_at_a_deleted_path", _refuses_untracked_at_deleted),
        _case("test_typechange_round_trips: the base's file during, the symlink after", _typechange),
        _case("test_interrupt_restores_the_tree: SIGINT to the group mid-run, every file equals HEAD, a second restore is harmless", _interrupt),
        _case("test_tests_and_specs_are_never_swapped", _never_swaps_tests),
        _case("test_log_keeps_an_excerpt_not_the_output: 500 lines in, at most 20 around the marker out", _excerpt),
        _case("test_stem_is_shared_with_the_checker: an odd title slugs to the name the checker derives", _stem),
    ]
