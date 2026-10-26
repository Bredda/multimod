from __future__ import annotations

import argparse
import sys

from . import fixtures, report, runner
from .cases import load_all
from .config import ROOT, load_config


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="mmprobe", description=__doc__)
    ap.add_argument("--env-file", help="fichier .env de la cible (défaut: ./.env)")
    ap.add_argument("--label", help="nom du dossier captures/<label> (défaut: host de la cible)")
    ap.add_argument("--base-url", help="surcharge MM_BASE_URL")
    ap.add_argument("--provider", choices=["http", "bedrock"], help="http = OpenAI/LiteLLM en HTTP brut ; bedrock = boto3 / bedrock-runtime (défaut: MM_PROVIDER ou http)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def sel(p):
        p.add_argument("--only", "-k", action="append", default=[], help="glob ou sous-chaîne sur l'id du cas (ex: 'speech/*', 'image', 'format_wav'). Répétable")
        p.add_argument("--tags", action="append", default=[], help="n'inclure que ces tags (répétable)")
        p.add_argument("--skip-tags", action="append", default=[], help="exclure ces tags (répétable)")
        p.add_argument("--heavy", action="store_true", help="inclure les cas `heavy` (payloads > 20 Mo)")
        p.add_argument("--security", action="store_true", help="inclure les cas `security` (SSRF) — à réserver à TA gateway, pas à un provider tiers")

    p = sub.add_parser("list", help="lister les cas sélectionnés"); sel(p)
    sub.add_parser("catalog", help="régénérer docs/cases-catalog.md")
    p = sub.add_parser("fixtures", help="générer les fixtures (images/audio locaux + parole via /audio/speech)")
    p.add_argument("--local-only", action="store_true", help="ne pas appeler l'API")
    p = sub.add_parser("run", help="exécuter les cas et capturer les échanges"); sel(p)
    p.add_argument("--dry-run", action="store_true", help="construire/écrire les requêtes sans les envoyer")
    p.add_argument("--delay", type=float, default=0.0, help="pause (s) entre cas")
    p.add_argument("--fresh", action="store_true", help="repartir d'un index vide (sinon un run partiel fusionne)")
    p = sub.add_parser("bedrock-models", help="lister les modèles / inference profiles Bedrock (plan de contrôle) avec leurs modalités")
    p.add_argument("--modality", action="append", default=[], help="filtrer sur une modalité d'entrée ou de sortie (IMAGE, SPEECH, AUDIO…) ; défaut: image + speech + audio")
    p.add_argument("--all", action="store_true", help="ne pas filtrer")
    sub.add_parser("http-models", help="(OpenAI/LiteLLM) lister les modèles exposés (GET /models, + /model/info LiteLLM) pour renseigner MM_MODEL_*")
    p = sub.add_parser("report", help="générer REPORT.md (et COMPARE_*.md avec --compare)")
    p.add_argument("--compare", nargs="+", metavar="LABEL", help="labels de captures/ à comparer")

    a = ap.parse_args(argv)
    cfg = load_config(a.env_file, a.label, a.base_url, a.provider)
    cases = load_all()

    if a.cmd == "catalog":
        print(report.write_catalog(cases, ROOT / "docs" / "cases-catalog.md")); return 0

    if a.cmd == "report":
        if a.compare:
            print(report.write_compare(cfg.captures_dir, a.compare))
        else:
            print(report.write_report(cfg.out_dir))
        return 0

    if a.cmd == "bedrock-models":
        from .discover import discover_bedrock_models
        return discover_bedrock_models(cfg, a.modality, a.all)

    if a.cmd == "http-models":
        from .discover import discover_http_models
        return discover_http_models(cfg)

    if a.cmd == "fixtures":
        if cfg.provider == "bedrock":
            made = fixtures.build_local(cfg.fixtures_dir)
            print(f"fixtures locales : {len(made)} fichiers. La parole (speech_en.*) vient de /audio/speech : la générer avec une cible HTTP (ex. `--provider http`, OpenAI) — les fixtures sont partagées.")
            return 0
        made = fixtures.build_local(cfg.fixtures_dir)
        print(f"fixtures locales : {len(made)} fichiers dans {cfg.fixtures_dir}")
        if not a.local_only:
            if not cfg.api_key:
                print("MM_API_KEY absent : parole non générée (relancer avec --local-only pour masquer ce message)"); return 1
            print(f"parole via {cfg.base_url}/audio/speech (modèle {cfg.models['tts']}) …")
            made = fixtures.build_speech(cfg, cfg.fixtures_dir)
            print(f"  {len(made)} fichiers de parole créés")
        return 0

    skip = list(a.skip_tags)
    if not a.heavy: skip.append("heavy")
    if not a.security: skip.append("security")
    chosen = runner.select(cases, a.only, a.tags, skip, cfg.provider)

    if a.cmd == "list":
        for c in chosen:
            print(f"{c.id:<50} {c.expect:<4} {','.join(c.tags):<28} {c.title}")
        print(f"\n{len(chosen)} cas", file=sys.stderr); return 0

    # run
    if cfg.provider == "http" and not a.dry_run and not cfg.api_key:
        print("MM_API_KEY (ou OPENAI_API_KEY) absent — voir .env.example", file=sys.stderr); return 2
    if cfg.provider == "bedrock" and not cfg.aws_region:
        print("région AWS absente : définir MM_AWS_REGION (ou AWS_REGION) — voir .env.example", file=sys.stderr); return 2
    cfg.fixtures_dir.mkdir(exist_ok=True)
    if not (cfg.fixtures_dir / "scene.png").exists():
        print("génération des fixtures locales…"); fixtures.build_local(cfg.fixtures_dir)
    if cfg.provider == "http" and not (cfg.fixtures_dir / "speech_en.mp3").exists() and not a.dry_run and cfg.api_key:
        print("génération des fixtures de parole via /audio/speech…")
        print(f"  {len(fixtures.build_speech(cfg, cfg.fixtures_dir))} fichiers")
    print(f"cible : {cfg.base_url if cfg.provider == 'http' else 'bedrock-runtime ' + str(cfg.aws_region)}  label : {cfg.label}  cas : {len(chosen)}{'  (dry-run)' if a.dry_run else ''}")
    results = runner.run_cases(cfg, chosen, a.dry_run, a.delay)
    if not a.dry_run:
        runner.write_index(cfg, results, merge=not a.fresh)
        print(f"\nindex : {cfg.out_dir / 'index.json'}")
        print(f"rapport : {report.write_report(cfg.out_dir)}")
    mism = sum(1 for r in results for s in r["steps"] if s.get("match") is False)
    errs = sum(1 for r in results if r["outcome"] == "script-error")
    print(f"\n{len(results)} cas · {mism} écart(s) vs attente · {errs} erreur(s) de script")
    return 1 if errs else 0
