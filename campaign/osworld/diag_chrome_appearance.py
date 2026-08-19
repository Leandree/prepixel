#!/usr/bin/env python3
"""Diagnostic, model-free, uncounted (GRANDE-PASSE §3, chrome-93eabf48).

Four runs (A and B, both iterations) claim chrome://settings/appearance has
no Light/Dark "Mode" row on this Linux build, and the evaluator requires the
`browser.theme.color_scheme` pref to become light/system THROUGH that page.
This boots the task's own VM, opens the page exactly as the evaluator's
getter does, and dumps (a) every row label the settings UI actually shows,
(b) the prefs the getter's walk would read. That settles "row absent — task
infeasible via the UI, to be documented" versus "row present — both
channels missed it".

Run: ~/miniconda3/envs/osworld/bin/python diag_chrome_appearance.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.expanduser("~/dev/OSWorld"))
os.chdir(os.path.expanduser("~/dev/OSWorld"))

TASK = ("evaluation_examples/examples/chrome/"
        "93eabf48-6a27-4cb6-b963-7d5fe1e0d3a9.json")

JS = r"""
() => {
  const out = {rows: [], selects: [], prefs: {}};
  const roots = [document];
  const collect = (root) => {
    for (const el of root.querySelectorAll('*')) {
      if (el.shadowRoot) { roots.push(el.shadowRoot); collect(el.shadowRoot); }
    }
  };
  collect(document);
  for (const r of roots) {
    for (const el of r.querySelectorAll(
        '.cr-row, settings-toggle-button, settings-dropdown-menu, ' +
        'cr-radio-group, select, [role="button"]')) {
      const t = (el.innerText || el.textContent || '')
        .trim().replace(/\s+/g, ' ').slice(0, 90);
      if (t) out.rows.push(el.tagName.toLowerCase() + ': ' + t);
    }
    for (const s of r.querySelectorAll('select')) {
      out.selects.push([...s.options].map(o => o.textContent.trim())
        .join('|').slice(0, 120));
    }
  }
  try {
    const ui = document.querySelector('settings-ui');
    const walk = (o, path, depth) => {
      if (!o || typeof o !== 'object' || depth > 6) return;
      if (Object.prototype.hasOwnProperty.call(o, 'value') &&
          /color_scheme|system_theme/.test(path)) {
        out.prefs[path] = o.value;
      }
      for (const [k, v] of Object.entries(o)) walk(v, path + '.' + k, depth + 1);
    };
    walk(ui && ui.prefs, 'prefs', 0);
  } catch (e) { out.prefs.error = String(e); }
  out.rows = [...new Set(out.rows)].slice(0, 60);
  return out;
}
"""


def main():
    from desktop_env.desktop_env import DesktopEnv
    from playwright.sync_api import sync_playwright

    task = json.load(open(TASK))
    env = DesktopEnv(provider_name="docker", os_type="Ubuntu",
                     action_space="pyautogui", headless=True,
                     require_a11y_tree=False)
    try:
        env.reset(task_config=task)
        url = "http://localhost:%d" % env.chromium_port
        print("CDP:", url, flush=True)
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(url)
            page = browser.contexts[0].new_page()
            page.goto("chrome://settings/appearance",
                      wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            out = page.evaluate(JS)
            print(json.dumps(out, indent=1))
            browser.close()
    finally:
        try:
            env.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
