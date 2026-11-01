"""Data run: scan CPython Doc/c-api on main, probe exported symbols in 3.8-3.15, grade PREREG.md.

MV2, Munim, Inc. Apache-2.0. Made with AI agents.
"""
import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import capi  # noqa: E402

UA = {"User-Agent": "mv2-capi-versionadded-audit/0.1 (Munim, Inc.; mv2@munimtech.com)"}
TARBALL = "https://codeload.github.com/python/cpython/tar.gz/refs/heads/main"
MINORS = list(range(8, 16))  # 3.8 .. 3.15 (uv had no 3.7 build on 2026-11-01)
UV_ENV = dict(os.environ, UV_PYTHON_PREFERENCE="only-managed",
              UV_PYTHON_INSTALL_DIR="/tmp/uv-python")


def get(url, tries=3):
    err = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except Exception as e:  # network hiccup: retry
            err = e
        time.sleep(5 * (k + 1))
    raise err


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def read_tree(path):
    """Doc/c-api/**.rst and Misc/stable_abi.toml from the tarball, plus the commit id."""
    docs, extra = {}, {}
    with tarfile.open(path, "r:gz") as tf:
        for m in tf:
            parts = m.name.split("/", 1)
            if len(parts) != 2 or not m.isfile():
                continue
            rel = parts[1]
            if rel.startswith("Doc/c-api/") and rel.endswith(".rst"):
                docs[rel] = tf.extractfile(m).read()
            elif rel == "Misc/stable_abi.toml":
                extra[rel] = tf.extractfile(m).read()
        commit = tf.pax_headers.get("comment", "")
    return docs, extra, commit


def interpreter(minor):
    v = "3.%d" % minor
    r = subprocess.run(["uv", "python", "install", v], env=UV_ENV,
                       capture_output=True, text=True, timeout=1200)
    if r.returncode != 0:
        return None, (r.stderr or r.stdout)[-400:]
    r = subprocess.run(["uv", "python", "find", v], env=UV_ENV,
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0 or not r.stdout.strip():
        return None, (r.stderr or r.stdout)[-400:]
    return r.stdout.strip().splitlines()[-1], ""


def probe(py, names, tmp):
    tin = os.path.join(tmp, "names.json")
    tout = os.path.join(tmp, "result.json")
    with open(tin, "w", encoding="utf-8") as f:
        json.dump(names, f)
    try:
        subprocess.run([py, "-I", os.path.join(HERE, "probe_capi.py"), tin, tout],
                       cwd=tmp, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=600)
        with open(tout, encoding="utf-8") as f:
            got = json.load(f)
        return got["results"], [got["version"], got["releaselevel"]]
    except Exception:
        return {n: "error" for n in names}, None
    finally:
        for p in (tin, tout):
            if os.path.exists(p):
                os.remove(p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    snap = os.path.join(a.out_dir, "snapshot")
    os.makedirs(snap, exist_ok=True)

    fetched_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    tar_path = os.path.join(a.data_dir, "cpython-main-%s.tar.gz" % fetched_at[:10])
    if not os.path.exists(tar_path):
        raw = get(TARBALL)
        with open(tar_path, "wb") as f:
            f.write(raw)
    with open(tar_path, "rb") as f:
        tar_sha = sha256(f.read())
    docs, extra, commit = read_tree(tar_path)

    rows = []
    for name in sorted(docs):
        rows.extend(capi.scan(docs[name].decode("utf-8"), name))
    for r in rows:
        r["primary"] = capi.primary(r)
    names = sorted({r["name"] for r in rows if r["kind"] in capi.EXPORTED and r["name"]}
                   | set(capi.CONTROLS) | set(capi.ALWAYS))

    uv_version = subprocess.run(["uv", "--version"], capture_output=True,
                                text=True).stdout.strip()
    status, interpreters = {}, {}
    with tempfile.TemporaryDirectory() as tmp:
        for minor in MINORS:
            py, err = interpreter(minor)
            if not py:
                interpreters["3.%d" % minor] = {"installed": False, "error": err}
                print("3.%d not installed: %s" % (minor, err.strip()[-200:]))
                continue
            res, ver = probe(py, names, tmp)
            found = sum(1 for v in res.values() if v == "yes")
            interpreters["3.%d" % minor] = {"installed": True, "version": ver,
                                            "exported_found": found}
            print("3.%d probed: %s, %d of %d names exported" % (minor, ver, found, len(names)))
            for key, s in res.items():
                status.setdefault(key, {})[minor] = s

    gate_verdict, gate_details = capi.gate(status)
    for r in rows:
        if r["kind"] not in capi.EXPORTED or not r["name"]:
            r["category"] = "not_exported_kind" if r["kind"] != "unattached" else "unattached"
            continue
        st = status.get(r["name"], {})
        r["status"] = {"3.%d" % k: v for k, v in sorted(st.items())}
        if r["major"] == 3 and r["minor"] is not None:
            r["category"] = capi.classify(r["minor"], st)
        else:
            r["category"] = "other_version"

    res = capi.grade(rows)
    res["P0_gate"] = {"verdict": gate_verdict, "details": gate_details}
    if gate_verdict != "HELD":
        for k in ("P1", "P2", "P3"):
            res[k]["verdict"] = "NOT_TESTABLE (gate failed)"
    res["counts"] = {
        "rst_files": len(docs),
        "versionadded_rows": len(rows),
        "attached": sum(1 for r in rows if r["kind"] != "unattached"),
        "attached_exported_kinds": sum(1 for r in rows if r["kind"] in capi.EXPORTED),
        "described": sum(1 for r in rows if r["described"]),
        "primary_before_probe": sum(1 for r in rows if r["primary"]),
        "names_probed": len(names),
    }
    res["source"] = {
        "fetched_at": fetched_at,
        "tarball_url": TARBALL,
        "tarball_sha256": tar_sha,
        "cpython_commit": commit,
        "uv": uv_version,
        "interpreters": interpreters,
        "platform": sys.platform,
    }
    with open(os.path.join(snap, "doc_capi_sha256.json"), "w", encoding="utf-8") as f:
        json.dump({k: sha256(v) for k, v in sorted(docs.items())}, f, indent=1)
    for rel, data in extra.items():
        with open(os.path.join(snap, os.path.basename(rel)), "wb") as f:
            f.write(data)
    with open(os.path.join(a.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, sort_keys=True)
    with open(os.path.join(a.out_dir, "rows.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1)
    cols = ["file", "line", "kind", "name", "version", "described", "primary", "category"]
    flagged = [r for r in rows if r["primary"] and r["category"] in ("earlier", "later", "gap")]
    for fname, subset in (("rows.csv", rows), ("flagged.csv", flagged)):
        with open(os.path.join(a.out_dir, fname), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cols + ["status"])
            for r in subset:
                st = r.get("status", {})
                w.writerow([r[c] for c in cols] + [";".join("%s=%s" % kv for kv in st.items())])
    print("P0", gate_verdict, json.dumps(gate_details))
    for k in ("P1", "P2", "P3"):
        print(k, res[k])
    for r in flagged:
        print("FLAG", r["file"], r["line"], r["name"], r["version"], r["category"],
              ";".join("%s=%s" % kv for kv in r.get("status", {}).items()))


if __name__ == "__main__":
    main()
