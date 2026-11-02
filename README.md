# capi-versionadded-audit

Do the "Added in version X.Y" notes in CPython's C API docs match the symbols the interpreters
export? This is a pre-registered audit by MV2 of Munim, Inc., made with AI agents working in his
name.

It reads every `.. versionadded::` in `Doc/c-api` on `main` and finds the `c:function` or
`c:var` entry each one marks. It then looks the symbol up in CPython 3.8 to 3.15 (with ctypes,
nothing is called) to see whether it first appears in release X.Y. It is the C API companion to
munimtechnologies/versionadded-runtime-audit.

- `PREREG.md`: question, prior art, rules, gate and three predictions, fixed before the data run.
- `capi.py`: finds each marker's symbol, classifies probe results, checks the control gate and
  grades P1 and P2.
- `probe_capi.py`: runs inside each interpreter (3.7 syntax) and reports which symbols exist.
- `job.py`: the data run. It downloads the CPython tarball, installs each interpreter with
  `uv python install`, probes and writes `summary.json`, `rows.csv`, `flagged.csv`, file
  hashes and a copy of `Misc/stable_abi.toml`.
- `test_capi.py`: tests with hand-worked expected values.

Run it with `python -m unittest -v`, then `python job.py --data-dir DATA --out-dir OUT`. You need
network access and `uv`.

## Results (run 1, graded 2026-11-02)

- The gate held. **P1 held:** 221 of 227 tested markers (97.4%) match the exported symbols.
  **P2 failed:** 2 earlier, 4 later. **P3 failed:** 0 doc errors under the pre-registered labels.
- The 4 "later" rows were macros or static inline functions in 3.9, exported later. The 2
  "earlier" rows are the stack-protection functions backported to 3.14.1.
- Reading those two rows turned up a real regression in the **3.14** docs. They now say
  "Added in version 3.15" for functions that shipped in 3.14.1, and they lost the warning
  about 3.14.0 incompatibility when the C API init page was split for 3.14.4. See
  `GRADING.md` and `FIXLIST.md`, and the follow-up study
  munimtechnologies/branch-version-notes-audit.
- Data: `results/` (summary, all rows, flagged rows).

## Licence

Code Apache-2.0. Text and data CC BY 4.0. MV2, Munim, Inc., mv2@munimtech.com.
