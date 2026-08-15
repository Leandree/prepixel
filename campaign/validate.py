#!/usr/bin/env python3
"""Validate every campaign result JSON against results-schema.json.

Run before aggregating so the cross-OS data from Windows/macOS/Linux agents is
guaranteed comparable. Exits non-zero if any file fails.
"""
import json, glob, os, sys
try:
    from jsonschema import Draft202012Validator
except ImportError:
    print("jsonschema not installed: pip install jsonschema"); sys.exit(2)

HERE = os.path.dirname(__file__)
schema = json.load(open(os.path.join(HERE, 'results-schema.json'), encoding='utf-8'))
v = Draft202012Validator(schema)
files = sorted(glob.glob(os.path.join(HERE, 'results', '*.json')))
bad = 0
for f in files:
    d = json.load(open(f, encoding='utf-8'))
    errs = sorted(v.iter_errors(d), key=lambda e: e.path)
    name = os.path.basename(f)
    if errs:
        bad += 1
        print(f"FAIL {name}")
        for e in errs[:5]:
            loc = '/'.join(map(str, e.path)) or '(root)'
            print(f"   - {loc}: {e.message}")
    else:
        print(f"ok   {name}")
print(f"\n{len(files)-bad}/{len(files)} valid")
sys.exit(1 if bad else 0)
