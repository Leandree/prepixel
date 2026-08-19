#!/usr/bin/env python3
"""Development-iteration runner: the 20 dev tasks x both conditions, two VMs
at a time (DEV-PHASE-PLAN.md §3).

Parallelism is bounded by the host, not by taste: the docker provider gives
each VM RAM_SIZE=4G / CPU_CORES=4, this host has 6 cores and ~10 GB free, so
two concurrent VMs fit and three do not. Port allocation is safe to race —
`DockerProvider.start_emulator` allocates VNC/server/chromium/VLC ports and
starts the container while holding a FileLock — and the qcow2 is mounted
read-only, each container writing its own copy-on-write layer.

The queue is ordered A1,B1,A2,B2,… so the two cells in flight are normally
the two conditions of the SAME task: contention is then symmetric between
the conditions, which is what matters for a measured comparison. When one
condition finishes early the pair desynchronises and the mix stays roughly
balanced; the honest statement, recorded in the returns file, is that
dev-phase wall-clock is measured under 2-way contention and is NOT
comparable to batch-1's serial wall-clock. Success and token cost — the two
numbers that decide the freeze — do not depend on host load.

Contention does touch one budget: B spends SETTLE_BUDGET re-capturing while
A spends it sleeping, so a loaded host buys B fewer captures inside the same
4 s. As with the original sizing, the asymmetry runs against the condition
under test, which is the safe direction.

The iteration runs against a PINNED COPY of the driver, snapshotted into
`<runs>/_driver/` at launch. An iteration takes hours; the next improvement
gets built during those hours, and a driver edited underneath a running
queue would silently give the last cells a different system than the first.
The snapshot also means each iteration directory carries the exact code that
produced it, next to the commit hash each cell already stamps.

Resumable: a cell whose result.json already exists is skipped, so an
interrupted iteration is restarted with the same command — and it resumes on
the pinned driver, not on whatever the working tree has become.

Usage:
  python run_dev_iteration.py --runs ~/dev/osworld-dev-iter1 [--workers 2]
                              [--max-steps 15] [--only chrome,os]
"""
import argparse
import calendar
import json
import os
import queue
import shutil
import subprocess
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OSWORLD = os.path.expanduser("~/dev/OSWorld")
PY = os.path.expanduser("~/miniconda3/envs/osworld/bin/python")
TASKS = os.path.join(HERE, "tasks-dev.json")
# Everything the driver reads at import or run time. prompt-template.md is in
# the list because it IS the experiment's frozen text.
PINNED = ("run_condition.py", "distill-osworld.py", "answer_loop.py",
          "prompt-template.md", "judge-crop.mjs",
          # The web channel. Left out of the first version of this list, and
          # the router would then have been silently absent from a pinned
          # iteration while the code said it was there — the exact failure
          # the pin is supposed to prevent.
          "cdp_view.mjs", "cdp_act.mjs",
          # The empty MCP config. Without it the answering CLI loads the
          # session's tool schemas — up to 162k prefix tokens per call,
          # belonging to neither channel — so a pinned iteration missing
          # this file would silently measure something else.
          "answer-mcp-empty.json")

# A fresh DesktopEnv boot is the one moment two workers genuinely compete
# (image start, VM boot, server handshake). Staggering the second worker
# keeps the boots from overlapping without slowing anything else down.
STAGGER_S = 45

# The answering model, IDENTICAL in both conditions (DEV-PHASE-PLAN P8; user
# decision 2026-08-18). Named in full because the CLI's `opus` alias resolves
# to Opus 4.8, and because the driver filters the CLI's token accounting by
# this exact key to separate the model under test from the CLI's own helper.
ANSWER_MODEL = "claude-opus-5[1m]"

OSWORLD_IMAGE = "happysixd/osworld-docker"

print_lock = threading.Lock()
reap_lock = threading.Lock()
# Cell start times of the cells currently in flight, keyed by worker.
inflight = {}


def say(msg):
    with print_lock:
        print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def reap_orphans(wid):
    """Remove OSWorld VM containers that no live cell can own.

    A driver that dies before `env.close()` leaves its 4 GB VM running, and
    on a 15 GB host one orphan is enough to starve every later cell: measured
    in iteration 1, where a single setup failure leaked a container and the
    next FOUR cells died at the VM-boot timeout — including one whose task
    was perfectly runnable. The driver-side fix (close the env on setup
    error) is the right one, but a two-hour unattended run should not depend
    on the driver never crashing in a new way.

    The rule is safe by construction: under the lock, any OSWorld container
    that started BEFORE the oldest cell currently in flight cannot belong to
    a cell that is still running. Nothing outside the OSWorld image is ever
    touched — this host also runs the user's own containers.
    """
    with reap_lock:
        oldest = min(inflight.values()) if inflight else time.time()
        try:
            out = subprocess.run(
                ["docker", "ps", "-a", "--filter", "ancestor=" + OSWORLD_IMAGE,
                 "--format", "{{.ID}} {{.CreatedAt}}"],
                capture_output=True, text=True, timeout=30).stdout
        except Exception as e:
            say("w%d: could not list containers to reap: %s" % (wid, e))
            return
        doomed = []
        for line in out.strip().splitlines():
            cid = line.split()[0] if line.split() else ""
            if not cid:
                continue
            try:
                started = subprocess.run(
                    ["docker", "inspect", "--format",
                     "{{.State.StartedAt}}", cid],
                    capture_output=True, text=True, timeout=30).stdout.strip()
                # timegm, not mktime: docker reports UTC and mktime would
                # read it as local time. Under CEST that made containers look
                # an hour OLDER than they are — and this function deletes
                # things by age, so the error had exactly one direction:
                # killing live VMs.
                ts = calendar.timegm(time.strptime(started[:19],
                                                   "%Y-%m-%dT%H:%M:%S"))
            except Exception:
                continue
            if ts < oldest - 30:
                doomed.append(cid)
        for cid in doomed:
            try:
                subprocess.run(["docker", "rm", "-f", cid],
                               capture_output=True, timeout=60)
                say("w%d: reaped orphaned VM container %s" % (wid, cid[:12]))
            except Exception as e:
                say("w%d: could not reap %s: %s" % (wid, cid[:12], e))


def pin_driver(runs):
    """Snapshot the driver so the queue cannot be changed under itself."""
    d = os.path.join(runs, "_driver")
    if os.path.exists(os.path.join(d, "run_condition.py")):
        say("driver already pinned at %s (resuming on it)" % d)
        return d
    os.makedirs(d, exist_ok=True)
    for f in PINNED:
        shutil.copy2(os.path.join(HERE, f), os.path.join(d, f))
    # Node resolves a bare ESM import by walking node_modules up from the
    # IMPORTING FILE, and the pinned copy lives outside the repo — so
    # `import 'playwright-core'` finds nothing there. Verified: it raised
    # ERR_MODULE_NOT_FOUND. A symlink fixes it for every future dependency
    # without hard-coding repo paths into the sources.
    link = os.path.join(d, "node_modules")
    if not os.path.exists(link):
        try:
            os.symlink(os.path.join(os.path.dirname(HERE), "..",
                                    "node_modules"), link)
        except OSError as e:
            say("WARNING: could not link node_modules (%s); JS channels "
                "will fail on the pinned copy" % e)
    head = subprocess.run(["git", "-C", HERE, "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", HERE, "status", "--porcelain"] +
                           [os.path.join(HERE, f) for f in PINNED],
                           capture_output=True, text=True).stdout.strip()
    json.dump({"commit": head, "uncommitted_changes": dirty or None,
               "files": list(PINNED)},
              open(os.path.join(d, "PINNED.json"), "w"), indent=1)
    if dirty:
        say("WARNING: pinned driver has uncommitted changes:\n%s" % dirty)
    say("driver pinned at %s (commit %s)" % (d, head[:8]))
    return d


def pinned_commit(driver_dir):
    """The pinned copy lives outside the repo, so the driver cannot read its
    own commit with git — it is handed down through the environment."""
    try:
        return json.load(open(os.path.join(driver_dir,
                                           "PINNED.json")))["commit"]
    except Exception:
        return "unknown"


def run_cell(cell, runs, driver_dir, max_steps, wid=0):
    domain, tid, cond = cell
    name = "%s-%s-%s" % (domain, tid[:8], cond)
    out = os.path.join(runs, name)
    if os.path.exists(os.path.join(out, "result.json")):
        say("SKIP  %s (result.json present)" % name)
        return name, "skipped"

    say("START %s" % name)
    t0 = time.time()
    inflight[wid] = t0
    env = dict(os.environ,
               CAMPAIGN_DRIVER_COMMIT=pinned_commit(driver_dir),
               CAMPAIGN_ANSWER_MODEL=ANSWER_MODEL,
               CAMPAIGN_MODEL=os.environ.get(
                   "CAMPAIGN_MODEL", "claude-code-cli:" + ANSWER_MODEL))
    with open(os.path.join(runs, name + ".log"), "wb") as dlog, \
            open(os.path.join(runs, name + "-answer.log"), "wb") as alog:
        drv = subprocess.Popen(
            [PY, os.path.join(driver_dir, "run_condition.py"),
             "--domain", domain, "--task-id", tid, "--condition", cond,
             "--out", out, "--max-steps", str(max_steps),
             "--phase", "development"],
            cwd=OSWORLD, env=env, stdout=dlog, stderr=subprocess.STDOUT)
        time.sleep(3)   # let the driver create <out> before the loop polls it
        ans = subprocess.Popen(
            [PY, os.path.join(driver_dir, "answer_loop.py"),
             "--run", out, "--condition", cond, "--model", ANSWER_MODEL],
            cwd=OSWORLD, env=env, stdout=alog, stderr=subprocess.STDOUT)
        drv.wait()
        # The answer loop is a poller with no termination signal of its own;
        # the driver finishing IS the signal. Kill by this exact PID only.
        ans.terminate()
        try:
            ans.wait(timeout=20)
        except subprocess.TimeoutExpired:
            ans.kill()

    dt = time.time() - t0
    inflight.pop(wid, None)
    # Reap BEFORE the next cell asks for 4 GB, not after it has failed to
    # get it.
    reap_orphans(wid)
    rj = os.path.join(out, "result.json")
    if not os.path.exists(rj):
        say("FAILED %s (no result.json, driver rc=%s, %.0fs)"
            % (name, drv.returncode, dt))
        return name, "no-result"
    r = json.load(open(rj))
    say("DONE  %s success=%s steps=%s term=%s (%.0fs)"
        % (name, r.get("success"), r.get("steps"), r.get("termination"), dt))
    return name, "ok"


def worker(wid, q, runs, driver_dir, max_steps, results):
    if wid:
        time.sleep(STAGGER_S * wid)
    while True:
        try:
            cell = q.get_nowait()
        except queue.Empty:
            return
        try:
            results.append(
                run_cell(cell, runs, driver_dir, max_steps, wid))
        except Exception as e:                       # noqa: BLE001
            say("ERROR %s: %s" % (cell, e))
            results.append(("-".join(cell), "exception"))
        finally:
            inflight.pop(wid, None)
            q.task_done()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--max-steps", type=int, default=15)
    ap.add_argument("--only", default="", help="comma-separated domain filter")
    ap.add_argument("--tasks", default="",
                    help="comma-separated task files (default: tasks-dev.json)"
                         " — iteration 3 passes dev-core + dev-browser and"
                         " the queues interleave per file, A,B per task")
    a = ap.parse_args()

    runs = os.path.expanduser(a.runs)
    os.makedirs(runs, exist_ok=True)
    driver_dir = pin_driver(runs)
    files = [f for f in a.tasks.split(",") if f] or [TASKS]
    only = {d for d in a.only.split(",") if d}

    q = queue.Queue()
    n = 0
    for f in files:
        spec = json.load(open(os.path.join(HERE, f) if not
                              os.path.isabs(f) else f))
        for domain in sorted(spec["tasks"]):
            if only and domain not in only:
                continue
            for tid in spec["tasks"][domain]:
                for cond in ("A", "B"):     # A then B, adjacent in the queue
                    q.put((domain, tid, cond))
                    n += 1
    say("queue: %d cells, %d workers, max_steps=%d, runs=%s"
        % (n, a.workers, a.max_steps, runs))

    results, threads = [], []
    t0 = time.time()
    for wid in range(a.workers):
        t = threading.Thread(
            target=worker,
            args=(wid, q, runs, driver_dir, a.max_steps, results))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

    say("ITERATION COMPLETE in %.0f min" % ((time.time() - t0) / 60))
    for name, status in sorted(results):
        say("  %-28s %s" % (name, status))


if __name__ == "__main__":
    main()
