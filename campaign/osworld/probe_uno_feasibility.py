#!/usr/bin/env python3
"""P9 feasibility probes (GRANDE-PASSE-AUTONOME §4) — evidence, not opinion.

The question, exactly as the manager posed it: can UNO acceptance be
established at the VM-image level, BEFORE any task, identically for both
conditions, without touching OSWorld's per-task setups or evaluators? If
the only route is relaunching soffice mid-task, the answer is NO.

This boots ONE scratch VM (uncounted, discarded) with a real calc dev task
and measures, in order:

  1. Is python3-uno importable inside the VM (system python, then
     LibreOffice's own python)?
  2. How was soffice launched by the task's own setup (cmdline — is there
     already an --accept)?
  3. The MECHANISM: write the user-profile registrymodifications item
     (ooSetupConnectionURL) that makes EVERY subsequent soffice listen,
     then — scratch VM only, this is exactly the mid-task relaunch that is
     FORBIDDEN in runs — restart soffice on the task document and try to
     connect and read the document model, including the property the
     writer-adf5e2c3 analysis showed neither screen channel can see:
     ListLabelString vs the paragraph's literal text.

Probe 3 proving the config+connect mechanism plus probe 4 (host-side: can
the base qcow2 be modified once, offline, shared by both conditions —
checked separately) = feasibility YES. Any probe failing = documented NO.

Run: ~/miniconda3/envs/osworld/bin/python probe_uno_feasibility.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.expanduser("~/dev/OSWorld"))
os.chdir(os.path.expanduser("~/dev/OSWorld"))

TASK = ("evaluation_examples/examples/libreoffice_calc/"
        "1334ca3e-f9e3-4db8-9ca7-b4c653be7d17.json")

VM_CHECKS = r"""
import glob, json, subprocess
out = {}
def sh(c, t=25):
    try:
        p = subprocess.run(c, shell=True, capture_output=True, text=True,
                           timeout=t)
        return (p.stdout + p.stderr).strip()
    except Exception as e:
        return "ERR:" + str(e)
out["sys_python_uno"] = sh("python3 -c 'import uno; print(uno.__file__)'")
lo = glob.glob("/usr/lib/libreoffice/program/python*")
out["lo_python"] = lo[0] if lo else "none"
out["soffice_cmdline"] = sh(
    "cat /proc/$(pgrep -f soffice.bin | head -1)/cmdline | tr '\\0' ' '")
print("VMPROBE:" + json.dumps(out))
"""

VM_RELAUNCH = r"""
import glob, json, os, subprocess, time
out = {}
cfg = os.path.expanduser(
    "~/.config/libreoffice/4/user/registrymodifications.xcu")
ITEM = ('<item oor:path="/org.openoffice.Setup/Office"><prop '
        'oor:name="ooSetupConnectionURL" oor:op="fuse"><value>socket,'
        'host=localhost,port=2002;urp;</value></prop></item>')
try:
    txt = open(cfg).read()
    if "ooSetupConnectionURL" not in txt:
        txt = txt.replace("</oor:items>", ITEM + "</oor:items>")
        open(cfg, "w").write(txt)
    out["cfg_written"] = True
except Exception as e:
    out["cfg_written"] = "ERR:" + str(e)
doc = None
for pat in ("/root/*.xlsx", "/root/Desktop/*.xlsx", "/home/*/Desktop/*.xlsx",
            "/home/*/*.xlsx"):
    hits = glob.glob(pat)
    if hits:
        doc = hits[0]
        break
out["task_doc"] = doc
subprocess.run("pkill -f soffice.bin", shell=True)
time.sleep(2)
subprocess.Popen(["soffice", "--calc", doc] if doc else ["soffice"],
                 env=dict(os.environ, DISPLAY=":0"))
print("VMPROBE:" + json.dumps(out))
"""

VM_LISTEN = r"""
import json, subprocess
def sh(c, t=20):
    p = subprocess.run(c, shell=True, capture_output=True, text=True,
                       timeout=t)
    return (p.stdout + p.stderr).strip()
print("VMPROBE:" + json.dumps({
    "soffice_cmdline_after": sh(
        "cat /proc/$(pgrep -f soffice.bin | head -1)/cmdline | tr '\\0' ' '"),
    "port_2002": sh("ss -ltn 2>/dev/null | grep 2002 || true")}))
"""

VM_CONNECT = r"""
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
    "info = {'impl': c.getImplementationName() if c else None}\n"
    "if c and hasattr(c, 'Sheets'):\n"
    "    s0 = c.Sheets.getByIndex(0)\n"
    "    cell = s0.getCellByPosition(0, 0)\n"
    "    info['sheet'] = s0.Name\n"
    "    old = cell.getString()\n"
    "    cell.setString('UNO-PROBE-OK')\n"
    "    info['write_ok'] = cell.getString() == 'UNO-PROBE-OK'\n"
    "    cell.setString(old)\n"
    "print('RES:' + repr(info))\n")
open("/tmp/unoprobe.py", "w").write(probe)
def sh(c, t=60):
    p = subprocess.run(c, shell=True, capture_output=True, text=True,
                       timeout=t)
    return (p.stdout + p.stderr).strip()
print("VMPROBE:" + json.dumps({"uno_connect": sh(
    "python3 /tmp/unoprobe.py 2>&1")[:500]}))
"""


def main():
    from desktop_env.desktop_env import DesktopEnv
    task = json.load(open(TASK))
    env = DesktopEnv(provider_name="docker", os_type="Ubuntu",
                     action_space="pyautogui", headless=True,
                     require_a11y_tree=False)
    try:
        env.reset(task_config=task)
        import time as _t

        def stage(name, script):
            r = env.controller.run_python_script(script)
            outp = (r or {}).get("output") or ""
            for line in outp.splitlines():
                if line.startswith("VMPROBE:"):
                    d = json.loads(line[8:])
                    print("== %s ==\n%s" % (name, json.dumps(d, indent=1)),
                          flush=True)
                    return d
            print("== %s == NO OUTPUT status=%s out=%r err=%r" % (
                name, (r or {}).get("status"), outp[:400],
                ((r or {}).get("error") or "")[:200]), flush=True)
            return {}

        stage("checks", VM_CHECKS)
        stage("config+relaunch", VM_RELAUNCH)
        _t.sleep(20)                    # driver-side wait, not in-VM
        stage("listen?", VM_LISTEN)
        stage("uno connect", VM_CONNECT)
    finally:
        try:
            env.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
