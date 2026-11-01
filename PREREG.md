# Pre-registration: do the C API docs' `versionadded` notes match the exported symbols?

MV2, Munim, Inc. (mv2@munimtech.com). Filed 2026-11-01, before the data run. Made with AI
agents working in MV2's name. Code Apache-2.0; text and results CC BY 4.0.

## Question

Extension authors read "Added in version 3.Y" on docs.python.org/3/c-api to decide which
functions they can call on the oldest Python they support. Those notes are written by hand. This
audit checks each one that sits directly on a `.. c:function::` or `.. c:var::` entry against the
symbols the interpreters actually export. Is the symbol absent from the latest 3.(Y-1) release
and present in the latest 3.Y release?

It is the C API companion to munimtechnologies/versionadded-runtime-audit. That audit checked
the library docs the same way on 2026-11-01. 574 of 609 markers matched, and hand review of the
35 mismatches found one real error (calendar's weekday constants marked 3.12, though they are
documented in 3.11).

## Prior art (searched 2026-11-01)

- Web and python/cpython issue searches for C API versionadded checks found one-off fixes. These
  are bpo-31338 (missing versionadded notes on Py_MIN and others, 2017) and PR #160471
  (versions for PyExpat_CAPI members), plus related work on `Py_Version` (bpo-43931).
- `Tools/build/stable_abi.py` and `Misc/stable_abi.toml` check the Limited API/stable ABI
  manifest against headers and exports. They do not check the docs' version notes, and they
  cover only the limited API.
- No tool or study was found that compares the C API docs' `versionadded` notes with the symbols
  exported by each release.

## How blind this is

The library-docs audit above was run and graded. The C API docs' version notes have not been
listed or counted. From general knowledge, a few functions began as macros or static inline
functions and were exported later (for example the vectorcall family). That knowledge shaped P2's
odds.

## Data (fixed now)

- python/cpython `main` as a tarball from codeload.github.com (commit id and SHA-256 recorded):
  every `Doc/c-api/**/*.rst`, plus a copy of `Misc/stable_abi.toml` for the hand review.
- CPython 3.8 to 3.15 at the latest micro release that `uv python install` provides
  (python-build-standalone, Linux x86-64). On 2026-11-01 uv had no 3.7 build, so 3.8 markers
  are untested.
- Each name is looked up with `getattr(ctypes.pythonapi, name)` (dlsym in the interpreter's
  global symbol scope) in a fresh `python -I` process. Nothing is called.

## Rules (fixed in capi.py, tested in test_capi.py)

- **Attachment.** A `versionadded` is attached when its indentation equals the body indentation
  of the innermost open C directive. Markers inside notes, list-tables and the like are
  "unattached". Continuation signature lines add their names to the same entry.
- **Names.** For `c:function`, the first identifier followed by `(` that is not a C type word.
  For `c:var`, the name in `(*name)` if there is one, otherwise the last identifier.
- **Primary set.** Kind `function` or `var`, a bare marker (no description text), a plain `3.Y`
  version (not `3.Y.Z` with Z > 0).
- **Categories.** ok (absent in 3.(Y-1), present in 3.Y), earlier (present in 3.(Y-1)), later
  (absent in 3.Y, present in a later release), gap, never_found (never exported: macros and static
  inline functions documented as functions), probe_error, untested. Only ok, earlier, later and
  gap count.
- **Gate (P0).** `Py_Initialize` and `PyLong_FromLong` must be found in every installed
  interpreter. `PyType_GetName` must be absent in 3.10 and present in 3.11, `Py_NewRef` absent
  in 3.9 and present in 3.10, and `PyLong_AsInt` absent in 3.12 and present in 3.13. If the gate
  fails, the probe is not measuring what it should, and P1 to P3 are NOT_TESTABLE.

## Predictions

- **P1.** At least **93%** of tested primary rows are `ok`. The library docs reached 94.3%. I
  expect C API markers to be about as accurate, because new C functions are almost always
  documented when they are added. About 60%.
- **P2.** More `earlier` rows than `later` rows. Functions that existed and were exported before
  their documented version push toward "earlier". Functions that were macros or inline in 3.Y and
  exported only later push toward "later". About 60%.
- **P3.** Hand review confirms **at least 2** genuine documentation errors. About 50%. This is
  the least blind prediction, because the verdict is human judgement under the labels below.

## Hand review for P3 (fixed now)

Every earlier, later and gap row is read in the rst source. It is then checked against
`Include/` (and the source files the symbol is defined in) at v3.(Y-1).0 and v3.Y.0, and against
What's New and `Misc/stable_abi.toml`. Labels:

- **doc error, too late.** The function or variable existed under the same name, was exported
  and was declared in a public (non-`internal`) header in v3.(Y-1).0. Neither the entry nor
  What's New 3.Y says it was made public, documented or added to the limited API in 3.Y.
- **doc error, too early.** Absent from v3.Y.0 entirely (no function, macro or inline of that
  name in any header) and first available in a later .0 release.
- **inline or macro.** Available in 3.Y as a macro or static inline function and exported only
  later. The note is right for source compatibility; not an error.
- **made public or limited later on purpose.** Stated in the docs or What's New.
- **backport**, **platform or build**, **parser or probe artefact.**

Only the two "doc error" labels count toward P3 and go on FIXLIST.md, with the tag-source
evidence. Before anything goes upstream, python/cpython issues and PRs are searched for the name.

## Limits

- Linux builds only; symbols exported only on Windows or macOS are not tested.
- Exported is not the same as public. A private-but-exported symbol with a public name will
  show as "earlier", and the hand review has to separate it out.
- `main` only; names removed from the docs are not seen.
