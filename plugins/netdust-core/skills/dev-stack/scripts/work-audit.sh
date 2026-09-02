#!/usr/bin/env bash
# work-audit.sh — find work that exists only on this machine.
#
# WHY: on 2026-09-02 one session found three separate strandings — 17 commits on a
# branch that was never pushed, four authored specs (~150 KB) staged once and never
# committed, and a lessons.md commit sitting unpushed in a clone. None were in a
# repo with a Makefile, so no `make` verb could have caught them. Nothing ever asked
# "is this work anywhere but here?"
#
# Usage:
#   work-audit.sh                 # the repo you are standing in
#   work-audit.sh PATH...         # those repos
#   work-audit.sh --fleet         # every git repo one level under the FLEET dirs
#
# Exit 0 = nothing at risk. 1 = work exists only here. 2 = not a git repo.
#
# Reports only. Every fix is printed as a command for you to run — deleting a branch
# or pushing someone's commit is a decision, not a side effect of an audit.
set -uo pipefail

FLEET_DIRS=("$HOME/Sites" "$HOME/Projects")

MAX_FILES=6   # a wall of paths is not a report; the count is the signal

findings=0
note() { printf '    %s\n' "$1"; findings=$((findings + 1)); }
fix()  { printf '      fix: %s\n' "$1"; }

# "a.md b.md c.md …" capped at MAX_FILES, with the remainder as a count.
summarize() {
  local list="$1" n shown
  n="$(printf '%s\n' "$list" | grep -c .)"
  shown="$(printf '%s\n' "$list" | head -"$MAX_FILES" | tr '\n' ' ')"
  if [ "$n" -gt "$MAX_FILES" ]; then
    printf '%s(+%d more)' "$shown" "$((n - MAX_FILES))"
  else
    printf '%s' "$shown"
  fi
}

audit_repo() {
  local dir="$1" name
  name="$(basename "$dir")"
  git -C "$dir" rev-parse --is-inside-work-tree >/dev/null 2>&1 || return 2

  local out=""
  # Collect into a buffer so a clean repo prints nothing at all.
  local before=$findings
  printf -v out '%s' ""

  local head remote_head upstream
  head="$(git -C "$dir" rev-parse --abbrev-ref HEAD 2>/dev/null)"

  echo "  $name  ($dir, on $head)"

  # 1. Uncommitted work — tracked edits and untracked files alike. The staged-only
  #    case is called out separately: `git add` writes a blob that gc can reap, so
  #    the working file is the only durable copy and it LOOKS tracked.
  local staged unstaged untracked
  staged="$(git -C "$dir" diff --cached --name-only 2>/dev/null)"
  unstaged="$(git -C "$dir" diff --name-only 2>/dev/null)"
  untracked="$(git -C "$dir" ls-files --others --exclude-standard 2>/dev/null)"

  if [ -n "$staged" ]; then
    note "staged, never committed: $(summarize "$staged")"
    fix "git -C $dir commit"
  fi
  [ -n "$unstaged" ] && note "modified, uncommitted: $(summarize "$unstaged")"
  if [ -n "$untracked" ]; then
    note "untracked: $(summarize "$untracked")"
    fix "git -C $dir add -A && git -C $dir commit"
  fi

  # 2. Commits the remote has never seen, on any local branch.
  local b up ahead
  while IFS= read -r b; do
    [ -n "$b" ] || continue
    up="$(git -C "$dir" rev-parse --abbrev-ref "$b@{u}" 2>/dev/null)"
    if [ -z "$up" ]; then
      # No upstream at all. Only interesting if it carries commits the default
      # branch does not already contain — a merged leftover is noise, not risk.
      if ! contained_in_remote "$dir" "$b"; then
        note "branch '$b' has NO upstream and is not contained in the remote"
        fix "git -C $dir push -u origin $b"
      fi
      continue
    fi
    ahead="$(git -C "$dir" rev-list --count "$up..$b" 2>/dev/null)"
    if [ "${ahead:-0}" -gt 0 ]; then
      note "branch '$b' is $ahead commit(s) ahead of $up — unpushed"
      fix "git -C $dir push ${up%%/*} $b"
    fi
  done < <(git -C "$dir" for-each-ref --format='%(refname:short)' refs/heads 2>/dev/null)

  # 3. Remote branches already merged into the default branch — dead weight that
  #    hides the branches that still mean something.
  local def merged
  def="$(default_branch "$dir")"
  if [ -n "$def" ]; then
    while IFS= read -r merged; do
      [ -n "$merged" ] || continue
      note "remote branch '$merged' is fully merged into $def"
      fix "git -C $dir push origin --delete ${merged#origin/}"
    done < <(git -C "$dir" for-each-ref --format='%(refname:short)' refs/remotes/origin 2>/dev/null \
              | grep -v -E "^(origin|origin/HEAD|${def})$" \
              | while IFS= read -r r; do
                  git -C "$dir" merge-base --is-ancestor "$r" "$def" 2>/dev/null && echo "$r"
                done)
  fi

  [ "$findings" -eq "$before" ] && echo "    clean"
  return 0
}

default_branch() {
  local dir="$1" d
  d="$(git -C "$dir" symbolic-ref --quiet refs/remotes/origin/HEAD 2>/dev/null)"
  if [ -n "$d" ]; then printf '%s' "${d#refs/remotes/}"; return; fi
  for c in origin/main origin/master; do
    git -C "$dir" rev-parse --verify --quiet "$c" >/dev/null 2>&1 && { printf '%s' "$c"; return; }
  done
}

contained_in_remote() {  # $1 = dir, $2 = branch — true when some remote ref holds it
  local dir="$1" b="$2" r
  while IFS= read -r r; do
    git -C "$dir" merge-base --is-ancestor "$b" "$r" 2>/dev/null && return 0
  done < <(git -C "$dir" for-each-ref --format='%(refname:short)' refs/remotes 2>/dev/null)
  return 1
}

TARGETS=()
case "${1:-}" in
  --fleet)
    for root in "${FLEET_DIRS[@]}"; do
      [ -d "$root" ] || continue
      while IFS= read -r g; do TARGETS+=("$(dirname "$g")"); done \
        < <(find "$root" -mindepth 2 -maxdepth 2 -name .git -print 2>/dev/null | sort)
    done
    ;;
  "") TARGETS=("$PWD") ;;
  *)  TARGETS=("$@") ;;
esac

echo "work-audit: ${#TARGETS[@]} repo(s)"
for t in "${TARGETS[@]}"; do
  audit_repo "$t" || { echo "  $(basename "$t"): not a git repo"; exit 2; }
done

echo
if [ "$findings" -gt 0 ]; then
  echo "$findings finding(s): work that exists only on this machine, or refs that hide the ones that matter." >&2
  exit 1
fi
echo "clean — nothing stranded."
exit 0
