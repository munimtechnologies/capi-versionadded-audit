# Grading: do the C API docs' `versionadded` notes match the exported symbols? (run 1)

MV2, Munim, Inc. (mv2@munimtech.com). Graded 2026-11-02 against PREREG.md (filed 2026-11-01,
before any data was read). Made with AI agents working in MV2's name. Code Apache-2.0; text and
results CC BY 4.0.

## Data the run used

- python/cpython `main` at commit `aa4f541a9742fa1de1008d13cbf23b2eb3799e3a` (tarball SHA-256
  `365e96ba...24b64`, fetched 2026-11-01T16:30Z): 80 `Doc/c-api` rst files, 592 `versionadded`
  markers, 543 attached to a C directive, 387 names probed.
- Interpreters (python-build-standalone via uv 0.13.6, Linux x86-64): 3.8.20, 3.9.25, 3.10.22,
  3.11.18, 3.12.16, 3.13.18, 3.14.10, 3.15.2. No 3.7 build, so 3.8 markers are untested.
- Gate P0 **held**: `Py_Initialize` and `PyLong_FromLong` found everywhere; `PyType_GetName`
  (3.11), `Py_NewRef` (3.10) and `PyLong_AsInt` (3.13) first appear where expected.
- Files: `results/run1-summary.json`, `results/rows.csv`, `results/rows.json`,
  `results/flagged.csv`.

## Verdicts

| | Prediction | Result | Verdict |
|---|---|---|---|
| P1 | at least 93% of tested primary rows are `ok` | 221 of 227 (97.4%) | **HELD** |
| P2 | more `earlier` rows than `later` rows | 2 earlier, 4 later, 0 gap | **FAILED** |
| P3 | hand review confirms at least 2 genuine doc errors | 0 under the two "doc error" labels | **FAILED** |

## Hand review of all 6 flagged rows

| Rows | Entry | Docs say | Probe | Label | Evidence (read first-hand) |
|---|---|---|---|---|---|
| 1 | `PyVectorcall_Function` | 3.9 | exported from 3.11 | inline or macro | v3.9.0 `Include/cpython/abstract.h`: `static inline vectorcallfunc PyVectorcall_Function(PyObject *callable)` |
| 1 | `PyObject_CallOneArg` | 3.9 | exported from 3.11 | inline or macro | same header: `static inline PyObject * PyObject_CallOneArg(PyObject *func, PyObject *arg)` |
| 1 | `Py_IS_TYPE` | 3.9 | exported from 3.15 | inline or macro | v3.9.0 `Include/object.h`: `#define Py_IS_TYPE(ob, type) _Py_IS_TYPE(...)` over a static inline |
| 1 | `Py_SET_SIZE` | 3.9 | exported from 3.15 | inline or macro | same file: `#define Py_SET_SIZE(ob, size) _Py_SET_SIZE(...)` |
| 2 | `PyUnstable_ThreadState_SetStackProtection`, `..._ResetStackProtection` | 3.15 | exported in 3.14.10 | backport | absent from v3.14.0 `Include/cpython/pystate.h`; declared on the 3.14 branch; added in 3.14.1 (gh-139653, backport PR #141661, 3.14.1 changelog) |

Total: 6 rows; 4 inline or macro, 2 backport, 0 doc errors under the pre-registered labels. The
four "later" rows are correct for source compatibility: the names worked in 3.9 as macros or
static inline functions, and were exported as symbols later.

## Not a P3 error, but a real problem: the 3.14 docs lost "Added in version 3.14.1"

The two backport rows count as "backport" under PREREG.md, because neither function existed at
v3.14.0. They still led to a real documentation regression, found while reading them:

- At tags v3.14.1, v3.14.2 and v3.14.3, `Doc/c-api/init.rst` says `.. versionadded:: 3.14.1`
  for both functions, followed by a warning: the function "was added in a bugfix release, and
  extensions that use it will be incompatible with Python 3.14.0", and packages should declare
  `Requires-Python: != 3.14.0.*`.
- At tag v3.14.4 the page was split up ("[3.14] gh-141811: Split up `init.rst` into multiple
  pages (GH-144844) (GH-145061)", 2026-02-23). Since then, the 3.14 branch's
  `Doc/c-api/threads.rst` says `.. versionadded:: 3.15` for both, and the file has no
  "3.14.0" or "Requires-Python" text at all.
- The live page docs.python.org/3.14/c-api/threads.html (3.14.10, read 2026-11-02) shows
  "Added in version 3.15." for both functions, and no compatibility warning.

So a reader of the 3.14 docs is told these functions are not in 3.14, and is no longer told
that using them breaks 3.14.0. Third-party projects already call them on 3.14.1+ (for example
RustCall.jl, which looks the symbol up at run time because 3.14.0 lacks it). On `main` and 3.15,
"3.15" follows the convention that each branch's docs state that branch's version (see
python/cpython #159013). On the 3.14 branch it is wrong. Searches of python/cpython issues and
PRs for `SetStackProtection` (2026-11-02) found the feature and backport PRs and two crash
reports, but nothing about this note. Details are in FIXLIST.md.

This case prompted a new pre-registered study across all of 3.12-3.15:
munimtechnologies/branch-version-notes-audit.

## What this means

The C API's "Added in version" notes agree with the exported symbols even more closely than
the library docs do (97.4% against 94.3%). Every disagreement had a clean explanation, so P3's
two-error bar failed. P2 failed because macros and inline functions that were exported only
later (4 rows) outnumbered names exported before their documented version (2 rows). The one
real problem lives on a maintenance branch's copy of the docs, which this audit (on `main`)
was not built to judge.

## Limits

Linux builds only. A symbol that is private but exported, or exported only on Windows or macOS,
is not separated by the probe. `main` docs only. The rows that rest on CPython's release history
(3.14.1 changelog, PR #141661) were cross-checked against the 3.14 branch and tag headers.
