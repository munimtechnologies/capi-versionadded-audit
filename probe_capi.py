"""Report which C symbols the running interpreter exports.

Usage: python -I probe_capi.py names.json result.json
names.json is a list of symbol names. Each is looked up with dlsym through
ctypes.pythonapi (the interpreter's own global symbol scope). Nothing is called.
Runs on every interpreter from 3.7 up, so it keeps to 3.7 syntax.

MV2, Munim, Inc. Apache-2.0. Made with AI agents.
"""
import json
import sys


def main():
    with open(sys.argv[1], encoding="utf-8") as f:
        names = json.load(f)
    out = {}
    try:
        import ctypes
        api = ctypes.pythonapi
    except BaseException:
        api = None
    for name in names:
        if api is None:
            out[name] = "error"
            continue
        try:
            getattr(api, name)
            out[name] = "yes"
        except AttributeError:
            out[name] = "no"
        except BaseException:
            out[name] = "error"
    v = sys.version_info
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump({"version": "%d.%d.%d" % (v[0], v[1], v[2]),
                   "releaselevel": v[3], "results": out}, f)


if __name__ == "__main__":
    main()
