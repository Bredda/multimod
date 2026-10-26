"""Découverte Bedrock (plan de contrôle) : quels modèles / inference profiles, avec quelles modalités."""
from __future__ import annotations

import json

from .bedrock import BCall, execute_bedrock

INTERESTING = {"IMAGE", "SPEECH", "AUDIO", "VIDEO"}


def discover_bedrock_models(cfg, modalities: list[str], show_all: bool) -> int:
    if not cfg.aws_region:
        print("région AWS absente : définir MM_AWS_REGION (ou AWS_REGION)"); return 2
    wanted = {m.upper() for m in modalities} or INTERESTING
    models = execute_bedrock(cfg, BCall("list_foundation_models", {}, service="bedrock"))
    if models.error or not models.data:
        print(f"list_foundation_models a échoué: {models.error}"); return 1
    profiles, token = [], None
    while True:
        r = execute_bedrock(cfg, BCall("list_inference_profiles", {"maxResults": 1000, **({"nextToken": token} if token else {})}, service="bedrock"))
        if r.error or not r.data:
            print(f"(list_inference_profiles indisponible: {r.error})"); break
        profiles += r.data.get("inferenceProfileSummaries", [])
        token = r.data.get("nextToken")
        if not token:
            break

    by_model: dict[str, list[str]] = {}
    for pr in profiles:
        for m in pr.get("models", []):
            arn = m.get("modelArn", "")
            by_model.setdefault(arn.split("/")[-1], []).append(pr["inferenceProfileId"])

    rows = []
    for m in models.data.get("modelSummaries", []):
        ins, outs = set(m.get("inputModalities", [])), set(m.get("outputModalities", []))
        if not show_all and not ((ins | outs) & wanted):
            continue
        rows.append({"modelId": m["modelId"], "provider": m.get("providerName"), "in": sorted(ins), "out": sorted(outs),
                     "inference": m.get("inferenceTypesSupported"), "streaming": m.get("responseStreamingSupported"),
                     "lifecycle": (m.get("modelLifecycle") or {}).get("status"), "profiles": by_model.get(m["modelId"], [])})
    rows.sort(key=lambda r: (r["provider"] or "", r["modelId"]))

    cfg.out_dir.mkdir(parents=True, exist_ok=True)
    (cfg.out_dir / "models.json").write_text(json.dumps({"region": cfg.aws_region, "models": rows, "count_total": len(models.data.get("modelSummaries", []))}, indent=2))
    print(f"région {cfg.aws_region} · {len(rows)} modèle(s) affiché(s) sur {len(models.data.get('modelSummaries', []))} · détail : {cfg.out_dir / 'models.json'}\n")
    print(f"{'modelId':<58} {'in':<26} {'out':<14} {'invocation':<22} profiles")
    for r in rows:
        print(f"{r['modelId']:<58} {','.join(r['in']):<26} {','.join(r['out']):<14} {','.join(r['inference'] or []):<22} {', '.join(r['profiles'][:2])}")
    print("\nPour un modèle 'INFERENCE_PROFILE' seul, utiliser l'id du profil (ex. eu.…) dans MM_BEDROCK_MODEL_<ROLE>.")
    return 0


def discover_http_models(cfg) -> int:
    """GET /models (OpenAI-compatible) + /model/info (LiteLLM, si exposé) : alias disponibles pour MM_MODEL_*."""
    from .http import Req, execute

    ex = execute(cfg, Req(path="/models", method="GET"))
    if ex.status != 200 or not isinstance(ex.json(), dict):
        print(f"GET /models -> {ex.status} {ex.error or ex.body[:200]!r}"); return 1
    ids = sorted(m["id"] for m in ex.json().get("data", []))
    info = execute(cfg, Req(path="/model/info", method="GET"))  # spécifique LiteLLM ; absent ailleurs
    modes: dict[str, str] = {}
    if info.status == 200 and isinstance(info.json(), dict):
        for m in info.json().get("data", []):
            modes[m.get("model_name", "")] = (m.get("model_info") or {}).get("mode") or ""
    cfg.out_dir.mkdir(parents=True, exist_ok=True)
    (cfg.out_dir / "models.json").write_text(json.dumps({"base_url": cfg.base_url, "models": ids, "litellm_modes": modes or None}, indent=2))
    print(f"{len(ids)} modèle(s) exposé(s) par {cfg.base_url} · détail : {cfg.out_dir / 'models.json'}"
          + ("" if modes else "  (/model/info indisponible : pas de 'mode' par modèle)") + "\n")
    for i in ids:
        print(f"{i:<60} {modes.get(i, '')}")
    return 0
