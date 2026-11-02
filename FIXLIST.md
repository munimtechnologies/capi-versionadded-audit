# Fix list: C API version notes (run 1)

MV2, Munim, Inc. Hand-checked 2026-11-02. Made with AI agents working in MV2's name. CC BY 4.0.

None of the 6 flagged rows is a doc error under PREREG.md's labels. One related problem was
found while reading them. It is listed here so a maintainer can check it.

## 1. 3.14 docs: stack-protection functions say "Added in version 3.15" and lost their 3.14.0 warning

- **Where:** branch `3.14`, `Doc/c-api/threads.rst`, entries
  `PyUnstable_ThreadState_SetStackProtection` and `PyUnstable_ThreadState_ResetStackProtection`.
  Live at https://docs.python.org/3.14/c-api/threads.html (3.14.10).
- **Now:** `.. versionadded:: 3.15` on both entries, and no compatibility warning.
- **Was (v3.14.1-v3.14.3, `Doc/c-api/init.rst`):** `.. versionadded:: 3.14.1` with a nested
  warning that extensions using the function will be incompatible with Python 3.14.0, and a
  recommendation to declare `Requires-Python: != 3.14.0.*`.
- **When it changed:** v3.14.4, with the 3.14 backport of the init.rst split (GH-145061,
  2026-02-23). The split's 3.14 copy carries `main`'s "3.15".
- **Evidence:** v3.14.0 `Include/cpython/pystate.h` has no such functions; the 3.14 branch
  header declares both; the 3.14.1 changelog lists gh-139653 "Add
  PyUnstable_ThreadState_SetStackProtection() and PyUnstable_ThreadState_ResetStackProtection()";
  the 3.14.10 interpreter exports both.
- **Suggested fix (3.14 branch only):** restore `.. versionadded:: 3.14.1` and the warning
  text from v3.14.3 `Doc/c-api/init.rst` on both entries. `main` and 3.15 can keep "3.15",
  following the per-branch convention in python/cpython #159013.
- **Duplicate search (2026-11-02):** python/cpython issues and PRs for `SetStackProtection`
  return gh-139653, PRs #139668, #141661 and #141892, and issues #142253, #144165, #157519 and
  #159639. None is about this note.
