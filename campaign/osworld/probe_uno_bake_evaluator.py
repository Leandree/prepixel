#!/usr/bin/env python3
"""Pre-run proof on the BAKED image (REPONSEGRANDEPASSE, chantier 1).

Extends ee27aff to what the order demands before any counted run: a full
evaluator pass on a dev calc task, on the baked image, with ZERO soffice
relaunch — the whole point of the bake is that the soffice the task's own
setup launches is already listening.

One throwaway VM (uncounted, destroyed):
  1. DesktopEnv(path_to_vm=Ubuntu-uno.qcow2) + env.reset(calc 1334ca3e)
     — the task setup downloads the xlsx and launches soffice itself.
  2. Prove port 2002 listens WITHOUT any (re)launch, and record the
     soffice cmdline as evidence nothing was touched.
  3. UNO connect from inside the VM: read the TASK's document model
     (implementation name, sheet, a cell) — read-only, no writes.
  4. env.evaluate() — the task's real evaluator runs on the baked image
     and returns a sane score for the untouched document.
  5. env.close().

Run: ~/miniconda3/envs/osworld/bin/python probe_uno_bake_evaluator.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.expanduser("~/dev/OSWorld"))
os.chdir(os.path.expanduser("~/dev/OSWorld"))

IMAGE = os.path.expanduser("~/dev/OSWorld/docker_vm_data/Ubuntu-uno.qcow2")
TASK = ("evaluation_examples/examples/libreoffice_calc/"
        "1334ca3e-f9e3-4db8-9ca7-b4c653be7d17.json")

VM_CHECK = r"""
import json, subprocess
def sh(c, t=20):
    p = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t)
    return (p.stdout + p.stderr).strip()
print("PROBE:" + json.dumps({
    "soffice_cmdline": sh("cat /proc/$(pgrep -f soffice.bin | head -1)/cmdline"
                          " | tr '\\0' ' '")[:200],
    "port_2002": sh("ss -ltn 2>/dev/null | grep 2002 || true")[:120]}))
"""

VM_UNO_READ = r"""
import json, subprocess
probe = (
    "import uno\n"
    "ctx = uno.getComponentContext()\n"
    "r = ctx.ServiceManager.createInstanceWithContext("
    "'com.sun.star.bridge.UnoUrlResolver', ctx)\n"
    "rc = r.resolve('uno:socket,host=localhost,port=2002;urp;"
    "StarOffice.ComponentContext')\n"
    "d = rc.ServiceManager.createInstanceWithContext("
    "'com.sun.star.frame.Desktop', rc)\n"
    "c = d.getCurrentComponent()\n"
    "info = {'impl': c.getImplementationName() if c else None,\n"
    "        'url': (c.getURL() if c else '')[-60:]}\n"
    "if c and hasattr(c, 'Sheets'):\n"
    "    s0 = c.Sheets.getByIndex(0)\n"
    "    info['sheet'] = s0.Name\n"
    "    info['a1'] = s0.getCellByPosition(0, 0).getString()[:40]\n"
    "print('RES:' + repr(info))\n")
open("/tmp/unoread.py", "w").write(probe)
p = subprocess.run("python3 /tmp/unoread.py 2>&1", shell=True,
                   capture_output=True, text=True, timeout=60)
print("PROBE:" + json.dumps({"uno_read": (p.stdout + p.stderr).strip()[:300]}))
"""


def main():
    from desktop_env.desktop_env import DesktopEnv
    task = json.load(open(TASK))
    env = DesktopEnv(provider_name="docker", os_type="Ubuntu",
                     action_space="pyautogui", headless=True,
                     require_a11y_tree=False, path_to_vm=IMAGE)
    try:
        env.reset(task_config=task)
        print("== reset OK (task setup ran on the baked image)", flush=True)
        for name, script in (("no-relaunch listen", VM_CHECK),
                             ("uno reads the task doc", VM_UNO_READ)):
            r = env.controller.run_python_script(script)
            outp = ((r or {}).get("output") or "")
            hit = [l for l in outp.splitlines() if l.startswith("PROBE:")]
            print(f"== {name} ==",
                  json.dumps(json.loads(hit[0][6:])) if hit else
                  f"NO OUTPUT {str(r)[:200]}", flush=True)
        score = env.evaluate()
        print("== evaluate ==", score, "(untouched doc — 0 expected)",
              flush=True)
    finally:
        try:
            env.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
