"""Tests for capi.py with hand-worked expected values.

MV2, Munim, Inc. Apache-2.0. Made with AI agents.
"""
import unittest

import capi

FIXTURE = "\n".join([
    "Integer Objects",                                       # 1
    "===============",                                       # 2
    "",                                                      # 3
    ".. c:function:: PyObject* PyLong_FromLong(long v)",     # 4
    "",                                                      # 5
    "   Return a new object.",                               # 6
    "",                                                      # 7
    "   .. versionadded:: 3.13",                             # 8
    "",                                                      # 9
    ".. c:function:: int PyLong_AsInt(PyObject *obj)",       # 10
    "                long PyLong_AsLong(PyObject *obj)",     # 11
    "",                                                      # 12
    "   Convert.",                                           # 13
    "",                                                      # 14
    "   .. versionadded:: 3.13",                             # 15
    "",                                                      # 16
    "   .. note::",                                          # 17
    "",                                                      # 18
    "      .. versionadded:: 3.12",                          # 19
    "",                                                      # 20
    ".. c:var:: PyTypeObject PyLong_Type",                   # 21
    "",                                                      # 22
    "   .. versionadded:: 3.10",                             # 23
    "      With text below.",                                # 24
    "",                                                      # 25
    ".. c:macro:: Py_RETURN_NONE",                           # 26
    "",                                                      # 27
    "   .. versionadded:: 3.9",                              # 28
    "",                                                      # 29
    ".. versionadded:: 3.8",                                 # 30
    "",                                                      # 31
    ".. c:type:: PyFoo",                                     # 32
    "",                                                      # 33
    "   .. c:member:: int bar",                              # 34
    "",                                                      # 35
    "      .. versionadded:: 3.11",                          # 36
    "",                                                      # 37
    "   .. versionadded:: 3.11.2",                           # 38
])


class TestNames(unittest.TestCase):
    def test_function(self):
        self.assertEqual(capi.c_name("function", "PyObject* PyLong_FromLong(long v)"),
                         "PyLong_FromLong")
        self.assertEqual(capi.c_name("function", "int PyLong_AsInt(PyObject *obj)"),
                         "PyLong_AsInt")

    def test_function_pointer_return(self):
        self.assertEqual(capi.c_name("function", "void (*PyOS_setsig(int i, void (*h)(int)))(int)"),
                         "PyOS_setsig")

    def test_var(self):
        self.assertEqual(capi.c_name("var", "PyTypeObject PyLong_Type"), "PyLong_Type")
        self.assertEqual(capi.c_name("var", "const unsigned long Py_Version"), "Py_Version")
        self.assertEqual(capi.c_name("var", "int (*PyOS_InputHook)(void)"), "PyOS_InputHook")

    def test_macro_and_empty(self):
        self.assertEqual(capi.c_name("macro", "Py_RETURN_NONE"), "Py_RETURN_NONE")
        self.assertIsNone(capi.c_name("function", ""))


class TestScan(unittest.TestCase):
    def setUp(self):
        self.rows = capi.scan(FIXTURE, "Doc/c-api/long.rst")

    def test_count(self):
        self.assertEqual(len(self.rows), 9)

    def test_rows(self):
        got = [(r["line"], r["kind"], r["name"], r["version"], r["described"])
               for r in self.rows]
        self.assertEqual(got, [
            (8, "function", "PyLong_FromLong", "3.13", False),
            (15, "function", "PyLong_AsInt", "3.13", False),
            (15, "function", "PyLong_AsLong", "3.13", False),
            (19, "unattached", None, "3.12", False),
            (23, "var", "PyLong_Type", "3.10", True),
            (28, "macro", "Py_RETURN_NONE", "3.9", False),
            (30, "unattached", None, "3.8", False),
            (36, "member", "bar", "3.11", False),
            (38, "type", "PyFoo", "3.11.2", False),
        ])

    def test_primary(self):
        prim = [(r["line"], r["name"]) for r in self.rows if capi.primary(r)]
        self.assertEqual(prim, [(8, "PyLong_FromLong"), (15, "PyLong_AsInt"),
                                (15, "PyLong_AsLong")])

    def test_micro(self):
        self.assertEqual(self.rows[8]["micro"], 2)
        self.assertEqual(self.rows[0]["file"], "Doc/c-api/long.rst")


class TestClassify(unittest.TestCase):
    def test_categories(self):
        self.assertEqual(capi.classify(13, {12: "no", 13: "yes", 14: "yes"}), "ok")
        self.assertEqual(capi.classify(13, {12: "yes", 13: "yes"}), "earlier")
        self.assertEqual(capi.classify(12, {11: "no", 12: "no", 13: "yes"}), "later")
        self.assertEqual(capi.classify(12, {10: "yes", 11: "no", 12: "no"}), "gap")
        self.assertEqual(capi.classify(12, {11: "no", 12: "no", 13: "no"}), "never_found")
        self.assertEqual(capi.classify(8, {8: "yes", 9: "yes"}), "untested")
        self.assertEqual(capi.classify(12, {11: "error", 12: "yes"}), "probe_error")


class TestGate(unittest.TestCase):
    def base(self):
        always = {m: "yes" for m in range(8, 14)}
        return {"Py_Initialize": dict(always), "PyLong_FromLong": dict(always),
                "PyType_GetName": {10: "no", 11: "yes"},
                "Py_NewRef": {9: "no", 10: "yes"},
                "PyLong_AsInt": {12: "no", 13: "yes"}}

    def test_held(self):
        verdict, details = capi.gate(self.base())
        self.assertEqual(verdict, "HELD")
        self.assertEqual(set(details.values()), {"ok"})

    def test_failed(self):
        st = self.base()
        st["PyLong_AsInt"] = {12: "yes", 13: "yes"}
        verdict, details = capi.gate(st)
        self.assertEqual(verdict, "FAILED")
        self.assertEqual(details["PyLong_AsInt"], "FAILED")

    def test_untested_control(self):
        st = self.base()
        del st["PyType_GetName"]
        verdict, details = capi.gate(st)
        self.assertEqual(verdict, "HELD")
        self.assertEqual(details["PyType_GetName"], "untested")

    def test_always_missing(self):
        st = self.base()
        st["Py_Initialize"][9] = "no"
        self.assertEqual(capi.gate(st)[0], "FAILED")


class TestGrade(unittest.TestCase):
    def test_grade(self):
        rows = [
            {"primary": True, "category": "ok", "minor": 13},
            {"primary": True, "category": "ok", "minor": 13},
            {"primary": True, "category": "earlier", "minor": 12},
            {"primary": True, "category": "never_found", "minor": 12},
            {"primary": False, "category": "later", "minor": 12},
        ]
        g = capi.grade(rows)
        self.assertEqual(g["P1"]["n"], 3)
        self.assertEqual(g["P1"]["ok"], 2)
        self.assertAlmostEqual(g["P1"]["share"], 2 / 3)
        self.assertEqual(g["P1"]["verdict"], "failed")
        self.assertEqual(g["P2"]["earlier"], 1)
        self.assertEqual(g["P2"]["later"], 0)
        self.assertEqual(g["P2"]["verdict"], "held")
        self.assertEqual(g["P3"]["flagged"], 1)
        self.assertEqual(g["categories_all_rows"],
                         {"ok": 2, "earlier": 1, "never_found": 1, "later": 1})
        self.assertEqual(g["primary_by_version"], {"3.13": {"ok": 2}, "3.12": {"earlier": 1}})

    def test_empty(self):
        g = capi.grade([])
        self.assertIsNone(g["P1"]["share"])
        self.assertEqual(g["P1"]["verdict"], "failed")


if __name__ == "__main__":
    unittest.main()
