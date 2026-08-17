#!/usr/bin/env python3
"""OSWorld condition driver (OSWORLD-PROTOCOL.md §2) — file-mailbox variant.

Boots the OSWorld docker VM for ONE task × ONE condition, then loops:
  1. capture observation (screenshot always; a11y tree in condition B),
  2. render the FROZEN prompt template (prompt-template.md) into
     <out>/step-N/prompt.txt,
  3. wait for the answering agent to write <out>/step-N/action.json,
  4. execute the action via env.step (WAIT/DONE/FAIL/CROP are handled here),
  5. condition B: act-guard — re-read the view after the action and attach a
     CONFIRMED / UNVERIFIED / EXPLICIT_FAILURE verdict to the next prompt.
On termination (DONE/FAIL/max steps) runs the OSWorld evaluator and writes
<out>/result.json (schema of protocol §3) plus the full trace on disk.

The answering agent is EXTERNAL (Claude Code subagent in the pilot; any
model via the API backend otherwise) — this driver never calls a model.
Condition B pixels-fallback (CROP) and coverage-guard spot-checks use the
repo's shipped judgeCrop via `node judge-crop.mjs` so the decision path is
byte-identical to the desktop campaign's.

Usage:
  python run_condition.py --domain chrome --task-id <uuid> --condition A|B \
      --out runs/<id>-A [--max-steps 15] [--osworld ~/dev/OSWorld]
"""
import argparse
import difflib
import importlib.util
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))

spec = importlib.util.spec_from_file_location(
    "distill_osworld", os.path.join(HERE, "distill-osworld.py"))
distill_osworld = importlib.util.module_from_spec(spec)
spec.loader.exec_module(distill_osworld)

TEMPLATE = open(os.path.join(HERE, "prompt-template.md")).read()


def template_section(marker):
    part = TEMPLATE.split(f"## {{OBSERVATION}} block, condition {marker}")[1]
    return part.split("\n## ")[0].strip()


BODY = TEMPLATE.split("---")[1].strip()
OBS_A = template_section("A (pixels)")
OBS_B = template_section("B (prepixel)")


def judge_crop(png_path, rect):
    """Run the repo's shipped judgeCrop on a rect of the screenshot."""
    out = subprocess.run(
        ["node", os.path.join(HERE, "judge-crop.mjs"), png_path,
         *(str(v) for v in rect)],
        capture_output=True, text=True, timeout=60)
    return json.loads(out.stdout) if out.returncode == 0 else None


def render_view(tree_xml, screenshot_path, workdir):
    """Adapter + coverage-guard A: returns the guarded view text."""
    view, suspects = distill_osworld.distill(tree_xml)
    guard_hits = 0
    for s in suspects:
        j = judge_crop(screenshot_path, s["rect"])
        if j and j.get("silentRisk"):
            guard_hits += 1
            x, y, w, h = s["rect"]
            view += (f'\n[pixels] group {x},{y},{w},{h} "{s["label"]}"'
                     f' [unverified: pixels show content]')
    return view, len(suspects), guard_hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True)
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--condition", required=True, choices=["A", "B"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-steps", type=int, default=15)
    ap.add_argument("--osworld", default=os.path.expanduser("~/dev/OSWorld"))
    ap.add_argument("--step-timeout", type=int, default=1200,
                    help="seconds to wait for action.json before infra_failure")
    args = ap.parse_args()

    sys.path.insert(0, args.osworld)
    from desktop_env.desktop_env import DesktopEnv

    task_path = os.path.join(args.osworld, "evaluation_examples", "examples",
                             args.domain, f"{args.task_id}.json")
    task = json.load(open(task_path))
    os.makedirs(args.out, exist_ok=True)
    t0 = time.time()

    env = DesktopEnv(provider_name="docker", os_type="Ubuntu",
                     action_space="pyautogui", headless=True,
                     require_a11y_tree=(args.condition == "B"))
    obs = env.reset(task_config=task)

    actions, act_verdicts = [], []
    prev_view_lines, prev_obs_paths = None, []
    pixel_fallbacks = guard_hits_total = suspects_total = 0
    infra_failure, term = False, "max_steps"

    for step in range(1, args.max_steps + 1):
        sd = os.path.join(args.out, f"step-{step}")
        os.makedirs(sd, exist_ok=True)
        shot = os.path.join(sd, "screenshot.png")
        open(shot, "wb").write(obs["screenshot"])

        if args.condition == "A":
            observation = OBS_A.replace("{SCREENSHOT_PATH}", shot) \
                .replace("{PREV_SCREENSHOT_PATHS}",
                         "\n".join(prev_obs_paths[-3:]) or "(none)")
            prev_obs_paths.append(shot)
        else:
            view, n_susp, n_hits = render_view(
                obs.get("accessibility_tree") or "", shot, sd)
            suspects_total += n_susp
            guard_hits_total += n_hits
            vpath = os.path.join(sd, "view.txt")
            open(vpath, "w").write(view)
            lines = view.split("\n")
            if prev_view_lines is None:
                shown = view
            else:
                diff = list(difflib.unified_diff(prev_view_lines, lines,
                                                 lineterm="", n=0))
                # diff applicable when it is genuinely smaller than the view
                if len(diff) < 0.6 * len(lines):
                    shown = ("[diff vs previous view]\n" + "\n".join(diff)) \
                        if diff else "[no change vs previous view]"
                else:
                    shown = view + "\n[diff inapplicable: full view re-emitted]"
            prev_view_lines = lines
            verdict_line = act_verdicts[-1] if act_verdicts else ""
            observation = OBS_B.replace("{VIEW_OR_DIFF}", shown) \
                .replace("{ACT_GUARD_LINE}",
                         f"[act-guard] previous action: {verdict_line}"
                         if verdict_line else "") \
                .replace("{PREV_VIEW_PATHS}",
                         "\n".join(prev_obs_paths[-3:]) or "(none)")
            prev_obs_paths.append(vpath)

        history = "\n".join(f"{i+1}. {a}" for i, a in enumerate(actions)) or "(none)"
        prompt = BODY.replace("{INSTRUCTION}", task["instruction"]) \
            .replace("{N}", str(step)).replace("{MAX_STEPS}", str(args.max_steps)) \
            .replace("{ACTION_HISTORY}", history) \
            .replace("{OBSERVATION}", observation) \
            .replace("{ACTION_PATH}", os.path.join(sd, "action.json"))
        open(os.path.join(sd, "prompt.txt"), "w").write(prompt)
        # signal readiness for the orchestrator
        open(os.path.join(args.out, "CURRENT_STEP"), "w").write(str(step))

        apath = os.path.join(sd, "action.json")
        waited = 0
        while not os.path.exists(apath):
            time.sleep(2)
            waited += 2
            if waited > args.step_timeout:
                infra_failure, term = True, "step_timeout"
                break
        if infra_failure:
            break
        time.sleep(1)  # let the writer finish
        action = json.load(open(apath))["action"].strip()
        actions.append(action)

        if action == "DONE" or action == "FAIL":
            term = action
            break
        if action == "WAIT":
            time.sleep(5)
            obs = env._get_obs() if hasattr(env, "_get_obs") else obs
            act_verdicts.append("WAIT (no action executed)")
            continue
        if action.startswith("CROP ") and args.condition == "B":
            pixel_fallbacks += 1
            rect = [int(v) for v in action[5:].split(",")]
            from PIL import Image
            img = Image.open(shot)
            x, y, w, h = rect
            crop_path = os.path.join(sd, "crop.png")
            img.crop((x, y, x + w, y + h)).save(crop_path)
            act_verdicts.append(f"CROP served: {crop_path}")
            # next prompt carries the crop path in the act-guard line
            obs = env._get_obs() if hasattr(env, "_get_obs") else obs
            continue

        prev_tree = obs.get("accessibility_tree") if args.condition == "B" else None
        try:
            obs, reward, done, info = env.step(action)
            if args.condition == "B":
                new_tree = obs.get("accessibility_tree")
                if prev_tree is not None and new_tree == prev_tree:
                    act_verdicts.append("UNVERIFIED (view unchanged after action)")
                else:
                    act_verdicts.append("CONFIRMED (view changed)")
        except Exception as e:
            act_verdicts.append(f"EXPLICIT_FAILURE ({str(e)[:120]})")
            obs = env._get_obs() if hasattr(env, "_get_obs") else obs

    score = None
    if not infra_failure:
        try:
            score = env.evaluate()
        except Exception as e:
            infra_failure = True
            term = f"evaluator_error: {str(e)[:200]}"
    env.close()

    result = {
        "task_id": args.task_id, "domain": args.domain,
        "condition": args.condition,
        "model": os.environ.get("CAMPAIGN_MODEL", "UNSET"),
        "success": bool(score) if score is not None else False,
        "score_raw": score, "steps": len(actions), "termination": term,
        "input_tokens": None, "output_tokens": None,   # filled by orchestrator
        "wall_clock_s": round(time.time() - t0, 1),
        "pixel_fallbacks": pixel_fallbacks if args.condition == "B" else None,
        "guard_hits": guard_hits_total if args.condition == "B" else None,
        "guard_suspects_checked": suspects_total if args.condition == "B" else None,
        "act_verdicts": act_verdicts if args.condition == "B" else None,
        "infra_failure": infra_failure, "notes": "",
        "actions": actions,
    }
    json.dump(result, open(os.path.join(args.out, "result.json"), "w"), indent=1)
    open(os.path.join(args.out, "CURRENT_STEP"), "w").write("FINISHED")
    print(json.dumps({k: result[k] for k in
                      ("task_id", "condition", "success", "steps",
                       "termination", "infra_failure")}))


if __name__ == "__main__":
    main()
