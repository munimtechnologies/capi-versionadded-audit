"""Find every ``.. versionadded::`` in CPython's Doc/c-api, name the C function or variable
it marks, and grade the documented version against which interpreters export that symbol.

MV2, Munim, Inc. Apache-2.0. Made with AI agents.
"""
import re

EXPORTED = ("function", "var")  # only these name a symbol a shared object can export
DIRECTIVE = re.compile(r"^( *)\.\. c:([a-z]+)::(.*)$")
OTHER = re.compile(r"^( *)\.\. ([a-z][a-z:-]*)::(.*)$")
VERSION = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?$")
FUNC_NAME = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*\(")
PTR_NAME = re.compile(r"\(\s*\*\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)")
LAST_NAME = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[[^\]]*\])?\s*$")
CTYPE_WORDS = {"void", "int", "char", "long", "short", "const", "unsigned", "signed",
               "double", "float", "struct", "size_t"}
PRIMARY = ("ok", "earlier", "later", "gap")
P1_BAR = 0.93
P3_BAR = 2
# Gate: symbols whose first exported release is known. name -> (absent in, present in).
CONTROLS = {"PyType_GetName": (10, 11), "Py_NewRef": (9, 10), "PyLong_AsInt": (12, 13)}
ALWAYS = ("Py_Initialize", "PyLong_FromLong")


def indent(line):
    return len(line) - len(line.lstrip(" "))


def c_name(kind, decl):
    """Symbol name in a C declaration: 'PyLong_FromLong' from 'PyObject* PyLong_FromLong(long v)'."""
    d = decl.strip()
    if not d:
        return None
    if kind == "function":
        for m in FUNC_NAME.finditer(d):  # skip 'void (' in function-pointer return types
            if m.group(1) not in CTYPE_WORDS:
                return m.group(1)
        return None
    m = PTR_NAME.search(d)
    if m:
        return m.group(1)
    if kind == "macro":
        m = re.match(r"[A-Za-z_][A-Za-z0-9_]*", d)
        return m.group(0) if m else None
    m = LAST_NAME.search(d)
    return m.group(1) if m else None


def next_indent(lines, i):
    for line in lines[i + 1:]:
        if line.strip():
            return indent(line)
    return -1


def parse_version(tok):
    m = VERSION.match(tok)
    if not m:
        return None, None, None
    micro = int(m.group(3)) if m.group(3) else 0
    return int(m.group(1)), int(m.group(2)), micro


def scan(text, path=""):
    """One row per versionadded directive in an .rst file.

    kind is the marked C directive (function, var, macro, type, member, ...), or
    "unattached" when the marker is not a direct child of a C directive.
    """
    rows = []
    lines = text.splitlines()
    stack = []  # open C directives, innermost last
    sig = None  # C directive whose signature lines are still open
    for i, line in enumerate(lines):
        if not line.strip():
            sig = None
            continue
        ind = indent(line)
        if sig is not None and ind > sig["indent"]:
            s = line.strip()
            if not s.startswith(":"):
                n = c_name(sig["kind"], s)
                if n:
                    sig["names"].append(n)
            continue
        sig = None
        while stack and stack[-1]["indent"] >= ind:
            stack.pop()
        if stack and stack[-1]["body"] is None:
            stack[-1]["body"] = ind
        m = DIRECTIVE.match(line)
        if m:
            kind = m.group(2)
            n = c_name(kind, m.group(3))
            entry = {"indent": ind, "kind": kind, "names": [n] if n else [], "body": None}
            stack.append(entry)
            sig = entry
            continue
        m = OTHER.match(line)
        if not m or m.group(2) != "versionadded":
            continue
        tok = m.group(3).split()
        major, minor, micro = parse_version(tok[0] if tok else "")
        base = {"file": path, "line": i + 1, "version": tok[0] if tok else "",
                "major": major, "minor": minor, "micro": micro,
                "described": len(tok) > 1 or next_indent(lines, i) > ind}
        if stack and stack[-1]["body"] == ind and stack[-1]["names"]:
            owner = stack[-1]
            for n in owner["names"]:
                rows.append(dict(base, kind=owner["kind"], name=n))
        else:
            rows.append(dict(base, kind="unattached", name=None))
    return rows


def primary(row):
    """Is this row in the pre-registered test set (before probing)?"""
    return (row["kind"] in EXPORTED and row["name"] is not None
            and not row["described"] and row["major"] == 3
            and row["minor"] is not None and row["micro"] == 0)


def classify(minor, st):
    """Category for a 'versionadded:: 3.<minor>' given probe statuses keyed by 3.x minor."""
    if minor not in st or (minor - 1) not in st:
        return "untested"
    cur, prev = st[minor], st[minor - 1]
    if cur not in ("yes", "no") or prev not in ("yes", "no"):
        return "probe_error"
    if not any(v == "yes" for v in st.values()):
        return "never_found"
    if prev == "yes":
        return "earlier"
    if cur == "yes":
        return "ok"
    if any(v == "yes" for k, v in st.items() if k > minor):
        return "later"
    return "gap"


def gate(status):
    """Do the control symbols behave as expected in every installed interpreter?

    status maps symbol -> {minor: "yes"/"no"/...}. Returns (verdict, details).
    """
    details, ok = {}, True
    for name in ALWAYS:
        st = status.get(name, {})
        good = bool(st) and all(v == "yes" for v in st.values())
        details[name] = "ok" if good else "FAILED"
        ok = ok and good
    for name, (absent, present) in sorted(CONTROLS.items()):
        st = status.get(name, {})
        if absent not in st or present not in st:
            details[name] = "untested"
            continue
        good = st[absent] == "no" and st[present] == "yes"
        details[name] = "ok" if good else "FAILED"
        ok = ok and good
    return ("HELD" if ok else "FAILED"), details


def grade(rows):
    """Mechanical verdicts for P1 and P2; P3 needs the hand review."""
    prim = [r for r in rows if r.get("primary") and r.get("category") in PRIMARY]
    n = len(prim)
    ok = sum(1 for r in prim if r["category"] == "ok")
    early = sum(1 for r in prim if r["category"] == "earlier")
    late = sum(1 for r in prim if r["category"] == "later")
    gap = sum(1 for r in prim if r["category"] == "gap")
    share = ok / n if n else None
    cats, by_minor = {}, {}
    for r in rows:
        c = r.get("category", "not_probed")
        cats[c] = cats.get(c, 0) + 1
    for r in prim:
        d = by_minor.setdefault("3.%d" % r["minor"], {})
        d[r["category"]] = d.get(r["category"], 0) + 1
    return {
        "P1": {"n": n, "ok": ok, "share": share, "bar": P1_BAR,
               "verdict": "held" if share is not None and share >= P1_BAR else "failed"},
        "P2": {"earlier": early, "later": late, "gap": gap,
               "verdict": "held" if early > late else "failed"},
        "P3": {"bar": P3_BAR, "flagged": early + late + gap,
               "verdict": "pending hand review"},
        "categories_all_rows": cats,
        "primary_by_version": by_minor,
    }
