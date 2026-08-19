#!/usr/bin/env python3
"""Bake the UNO affordance into the VM image (REPONSEGRANDEPASSE chantier 1).

Establishes `ooSetupConnectionURL` in the LibreOffice user profile of a COPY
of the base image, offline, before any task, identically for both conditions
— the route identified in the P9 study (ee27aff): the OSWorld container
boots /boot.qcow2, a qcow2 overlay backed by /System.qcow2 (install.sh:191),
so committing the overlay into a writable copy bakes the change.

Stages, each logged, the script stops at the first failure:
  H1  manual container on Ubuntu-uno.qcow2 mounted RW, wait /screenshot
  G1  in guest: soffice --headless --terminate_after_init → profile exists
  G2  in guest: insert the ooSetupConnectionURL item, re-read to verify
  G3  in guest: start soffice --headless, poll port 2002, then pkill -9
      (NOT a clean exit: LibreOffice rewrites registrymodifications.xcu on
      clean exit, and the point is to prove the file on disk keeps the item
      when soffice never gets to rewrite it), re-read the file again
  G4  in guest: sync, then poweroff (fire and forget)
  H2  host: wait container exit, docker cp the /boot.qcow2 delta out
  H3  host: qemu-img commit via a utility container of the same image
      (the delta's embedded backing path /System.qcow2 matches the mount)
  H4  post-verify on the COMMITTED image, mounted RO exactly like the
      provider: fresh throwaway container, profile item present, soffice
      --headless listens on 2002, pkill -9, container removed

No counted run may be in flight (single 4G VM at a time on this host).
Run: python3 bake_uno_image.py
"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.expanduser("~/dev/OSWorld"))

IMAGE = os.path.expanduser("~/dev/OSWorld/docker_vm_data/Ubuntu-uno.qcow2")
DOCKER_IMG = "happysixd/osworld-docker"
NAME = "uno-bake"
PORT = 5099
ITEM = ('<item oor:path="/org.openoffice.Setup/Office"><prop '
        'oor:name="ooSetupConnectionURL" oor:op="fuse"><value>socket,'
        'host=localhost,port=2002;urp;</value></prop></item>')

G1 = r"""
import glob, json, os, subprocess, time
cfg = os.path.expanduser("~/.config/libreoffice/4/user/registrymodifications.xcu")
if not os.path.exists(cfg):
    subprocess.Popen(["soffice", "--headless", "--invisible",
                      "--terminate_after_init"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     stdin=subprocess.DEVNULL, start_new_session=True)
    for _ in range(60):
        if os.path.exists(cfg):
            break
        time.sleep(1)
    time.sleep(3)   # let terminate_after_init finish writing
print("BAKE:" + json.dumps({"profile_exists": os.path.exists(cfg),
                            "size": os.path.getsize(cfg) if os.path.exists(cfg) else 0}))
"""

G2 = r"""
import json, os
ITEM = %r
cfg = os.path.expanduser("~/.config/libreoffice/4/user/registrymodifications.xcu")
txt = open(cfg).read()
if "ooSetupConnectionURL" not in txt:
    txt = txt.replace("</oor:items>", ITEM + "</oor:items>")
    open(cfg, "w").write(txt)
back = open(cfg).read()
print("BAKE:" + json.dumps({"item_written": "ooSetupConnectionURL" in back}))
""" % ITEM

G3 = r"""
import json, os, subprocess, time
subprocess.Popen(["soffice", "--headless", "--invisible"],
                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                 stdin=subprocess.DEVNULL, start_new_session=True)
port = ""
for _ in range(30):
    time.sleep(1)
    p = subprocess.run("ss -ltn 2>/dev/null | grep 2002 || true",
                       shell=True, capture_output=True, text=True)
    if p.stdout.strip():
        port = p.stdout.strip()
        break
subprocess.run("pkill -9 -f soffice.bin", shell=True)
time.sleep(1)
cfg = os.path.expanduser("~/.config/libreoffice/4/user/registrymodifications.xcu")
still = "ooSetupConnectionURL" in open(cfg).read()
print("BAKE:" + json.dumps({"port_2002": port[:120], "item_survives": still}))
"""

G4 = r"""
import json, subprocess
subprocess.run("sync", shell=True)
print("BAKE:" + json.dumps({"synced": True}))
subprocess.Popen(["shutdown", "-h", "now"])
"""


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)


def stage_guest(ctrl, name, script, timeout_note=""):
    r = ctrl.run_python_script(script)
    outp = ((r or {}).get("output") or "")
    for line in outp.splitlines():
        if line.startswith("BAKE:"):
            d = json.loads(line[5:])
            print(f"== {name} == {json.dumps(d)}", flush=True)
            return d
    print(f"== {name} == NO OUTPUT r={str(r)[:300]}", flush=True)
    return None


def wait_ready(port, timeout=300):
    import requests
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if requests.get(f"http://localhost:{port}/screenshot",
                            timeout=(5, 10)).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(5)
    return False


def main():
    from desktop_env.controllers.python import PythonController
    assert os.path.exists(IMAGE), IMAGE
    print("image before:", sh(f"docker run --rm -v {IMAGE}:/System.qcow2:ro "
                              f"--entrypoint qemu-img {DOCKER_IMG} info "
                              f"/System.qcow2").stdout.strip()[:300], flush=True)

    sh(f"docker rm -f {NAME} 2>/dev/null")
    r = sh(f"docker run -d --name {NAME} --device /dev/kvm --cap-add NET_ADMIN "
           f"-e DISK_SIZE=32G -e RAM_SIZE=4G -e CPU_CORES=4 "
           f"-v {IMAGE}:/System.qcow2:rw -p {PORT}:5000 {DOCKER_IMG}")
    assert r.returncode == 0, r.stderr
    print("== H1 == container", r.stdout.strip()[:12], flush=True)
    try:
        assert wait_ready(PORT), "VM never became ready"
        print("== H1 == VM ready", flush=True)
        ctrl = PythonController(vm_ip="localhost", server_port=PORT)

        d = stage_guest(ctrl, "G1 profile", G1)
        assert d and d.get("profile_exists"), "no profile"
        d = stage_guest(ctrl, "G2 patch", G2)
        assert d and d.get("item_written"), "item not written"
        d = stage_guest(ctrl, "G3 listen+survive", G3)
        assert d and d.get("port_2002") and d.get("item_survives"), \
            f"affordance not proven: {d}"
        try:
            stage_guest(ctrl, "G4 shutdown", G4)
        except Exception:
            pass                      # server dies with the guest — expected

        print("== H2 == waiting for container exit", flush=True)
        rc = sh(f"timeout 180 docker wait {NAME}")
        print("== H2 == container exited rc=", rc.stdout.strip(), flush=True)
        delta = "/tmp/uno-boot-delta.qcow2"
        sh(f"rm -f {delta}")
        r = sh(f"docker cp {NAME}:/boot.qcow2 {delta}", timeout=600)
        assert r.returncode == 0, r.stderr
        print("== H2 == delta size:",
              os.path.getsize(delta) // (1 << 20), "MiB", flush=True)

        r = sh(f"docker run --rm -v /tmp:/work -v {IMAGE}:/System.qcow2:rw "
               f"--entrypoint qemu-img {DOCKER_IMG} commit /work/uno-boot-delta.qcow2",
               timeout=600)
        assert r.returncode == 0, r.stdout + r.stderr
        print("== H3 == commit:", (r.stdout + r.stderr).strip()[:200], flush=True)
    finally:
        sh(f"docker rm -f {NAME} 2>/dev/null")
        sh("rm -f /tmp/uno-boot-delta.qcow2")

    # H4 — provider-identical (RO) verification on the committed image
    sh(f"docker rm -f {NAME}-verify 2>/dev/null")
    r = sh(f"docker run -d --name {NAME}-verify --device /dev/kvm "
           f"--cap-add NET_ADMIN -e DISK_SIZE=32G -e RAM_SIZE=4G "
           f"-e CPU_CORES=4 -v {IMAGE}:/System.qcow2:ro -p {PORT}:5000 "
           f"{DOCKER_IMG}")
    assert r.returncode == 0, r.stderr
    try:
        assert wait_ready(PORT), "verify VM never became ready"
        from desktop_env.controllers.python import PythonController as PC
        ctrl = PC(vm_ip="localhost", server_port=PORT)
        d = stage_guest(ctrl, "H4 verify (ro, committed)", G3)
        assert d and d.get("port_2002") and d.get("item_survives"), \
            f"committed image does not carry the affordance: {d}"
        print("== H4 == BAKE PROVEN on RO-mounted committed image", flush=True)
    finally:
        sh(f"docker rm -f {NAME}-verify 2>/dev/null")

    print("image after:", sh(f"docker run --rm -v {IMAGE}:/System.qcow2:ro "
                             f"--entrypoint qemu-img {DOCKER_IMG} info "
                             f"/System.qcow2").stdout.strip()[:300], flush=True)
    print("BAKE COMPLETE", flush=True)


if __name__ == "__main__":
    main()
