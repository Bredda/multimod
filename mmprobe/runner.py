"""Contexte d'exécution des cas, exécution, index des résultats."""
from __future__ import annotations

import fnmatch
import json
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import capture
from .cases import REGISTRY, Case
from .config import Config
from .fixtures import Fixtures, Skip
from .http import Exchange, Req, execute
from .report import summarize


def status_ok(expect: str, status: int | None) -> bool | None:
    if expect == "any":
        return None
    if status is None:
        return False
    return (200 <= status < 300) if expect == "2xx" else (400 <= status < 500)


class Ctx:
    def __init__(self, cfg: Config, fx: Fixtures, case: Case, dry_run: bool):
        self.cfg, self.fx, self.case, self.dry_run = cfg, fx, case, dry_run
        self.dir = cfg.out_dir / case.endpoint / case.name
        self.steps: list[dict[str, Any]] = []

    def model(self, key: str) -> str:
        return self.cfg.models[key]

    def skip(self, why: str):
        raise Skip(why)

    def call(self, req: Req, step: str | None = None, expect: str | None = None) -> Exchange:
        expect = expect or self.case.expect
        ex = execute(self.cfg, req, dry_run=self.dry_run)
        d = self.dir / step if step else self.dir
        meta = capture.save(ex, d)
        summary = None if self.dry_run else summarize(self.case.endpoint, ex)
        self.steps.append({
            "step": step, "dir": str(d.relative_to(self.cfg.out_dir)), "expect": expect,
            "match": None if self.dry_run else status_ok(expect, ex.status), "summary": summary, **meta,
        })
        return ex


def select(cases: list[Case], only: list[str], tags: list[str], skip_tags: list[str]) -> list[Case]:
    out = []
    for c in cases:
        if only and not any(fnmatch.fnmatch(c.id, p) or p in c.id for p in only):
            continue
        if tags and not set(tags) & set(c.tags):
            continue
        if skip_tags and set(skip_tags) & set(c.tags):
            continue
        out.append(c)
    return out


def run_cases(cfg: Config, cases: list[Case], dry_run: bool = False, delay: float = 0.0, log=print) -> list[dict]:
    fx = Fixtures(cfg.fixtures_dir)
    results = []
    for i, c in enumerate(cases, 1):
        ctx = Ctx(cfg, fx, c, dry_run)
        t0 = time.time()
        entry: dict[str, Any] = {"case": c.id, "order": REGISTRY.index(c), "title": c.title, "expect": c.expect, "tags": list(c.tags)}
        try:
            c.fn(ctx)
            entry["outcome"] = "dry-run" if dry_run else "done"
        except Skip as s:
            entry["outcome"] = "skipped"; entry["reason"] = str(s)
        except Exception as e:  # bug de script, pas un résultat d'API
            entry["outcome"] = "script-error"; entry["reason"] = f"{type(e).__name__}: {e}"
            entry["traceback"] = traceback.format_exc()
        entry["steps"] = ctx.steps
        entry["elapsed_s"] = round(time.time() - t0, 2)
        results.append(entry)
        log(_line(i, len(cases), entry))
        if delay and not dry_run:
            time.sleep(delay)
    return results


def _line(i: int, n: int, e: dict) -> str:
    head = f"[{i:>3}/{n}] {e['case']:<46}"
    if e["outcome"] in ("skipped", "script-error"):
        return f"{head} {e['outcome'].upper()}: {e['reason']}"
    parts = []
    for s in e["steps"]:
        mark = {True: "ok", False: "!!", None: "--"}[s.get("match")]
        parts.append(f"{(s['step'] + ':') if s['step'] else ''}{s.get('status')} [{mark}]")
    return f"{head} {' '.join(parts) if parts else e['outcome']}"


def write_index(cfg: Config, results: list[dict], merge: bool = True) -> Path:
    """index.json : un run partiel (--only) met à jour les cas rejoués sans écraser les autres."""
    p = cfg.out_dir / "index.json"
    cfg.out_dir.mkdir(parents=True, exist_ok=True)
    existing: dict[str, dict] = {}
    if merge and p.exists():
        existing = {e["case"]: e for e in json.loads(p.read_text()).get("results", [])}
    for r in results:
        existing[r["case"]] = r
    doc = {
        "label": cfg.label, "base_url": cfg.base_url, "models": cfg.models,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "results": sorted(existing.values(), key=lambda e: e.get("order", 10**6)),
    }
    p.write_text(json.dumps(doc, indent=2, ensure_ascii=False))
    return p
