"""Transport boto3 (bedrock-runtime) : mêmes mesures et même objet `Exchange` que le transport HTTP.

Le worker de la gateway appelle Bedrock via boto3 : on sonde donc avec boto3 (pas de HTTP brut), et on
capture ce que boto3 reçoit/renvoie (paramètres Python, dict de réponse, ClientError).
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from .config import Config
from .http import Exchange

STREAM_OPS = {"converse_stream": "stream", "invoke_model_with_response_stream": "body"}
# Remplaçable par un faux client dans les tests : (cfg, service, bad_credentials) -> client
CLIENT_FACTORY: Callable[[Config, str, bool], Any] | None = None


@dataclass
class BCall:
    operation: str                       # converse | converse_stream | invoke_model | count_tokens | ...
    params: dict = field(default_factory=dict)
    body: Any = None                     # invoke_model* : dict JSON sérialisé dans params["body"]
    service: str = "bedrock-runtime"     # ou "bedrock" (plan de contrôle : list_foundation_models...)
    bad_credentials: bool = False        # client avec de faux identifiants (cas d'auth)

    def final_params(self) -> dict:
        p = dict(self.params)
        if self.body is not None:
            p["body"] = json.dumps(self.body).encode()
            p.setdefault("contentType", "application/json")
            p.setdefault("accept", "application/json")
        return p


_clients: dict[tuple, Any] = {}


def make_client(cfg: Config, service: str, bad_credentials: bool = False):
    if CLIENT_FACTORY is not None:
        return CLIENT_FACTORY(cfg, service, bad_credentials)
    key = (service, cfg.aws_region, cfg.aws_profile, bad_credentials, cfg.timeout)
    if key in _clients:
        return _clients[key]
    import boto3
    from botocore.config import Config as BotoConfig

    bc = BotoConfig(retries={"max_attempts": 1, "mode": "standard"},  # aucune relance cachée
                    read_timeout=cfg.timeout, connect_timeout=10, user_agent_extra="mmprobe")
    if bad_credentials:
        session = boto3.Session(aws_access_key_id="AKIAMMPROBEINVALID", aws_secret_access_key="invalid" * 5, region_name=cfg.aws_region)
    else:
        session = boto3.Session(profile_name=cfg.aws_profile, region_name=cfg.aws_region)
    client = session.client(service, config=bc)
    _clients[key] = client
    return client


def region_of(client, cfg: Config) -> str:
    try:
        return client.meta.region_name or cfg.aws_region or "?"
    except Exception:
        return cfg.aws_region or "?"


def validate_offline(cfg: Config, call: BCall) -> str | None:
    """Valide les paramètres contre le modèle de service botocore, sans réseau ni identifiants."""
    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config as BotoConfig
    from botocore.exceptions import ParamValidationError
    from botocore.validate import validate_parameters

    client = boto3.client(call.service, region_name=cfg.aws_region or "us-east-1", config=BotoConfig(signature_version=UNSIGNED))
    op = client.meta.method_to_api_mapping.get(call.operation)
    if op is None:
        return f"opération inconnue: {call.operation}"
    shape = client.meta.service_model.operation_model(op).input_shape
    try:
        validate_parameters(call.final_params(), shape)
    except ParamValidationError as e:
        return str(e)
    return None


def execute_bedrock(cfg: Config, call: BCall, *, dry_run: bool = False) -> Exchange:
    from botocore.exceptions import BotoCoreError, ClientError, ParamValidationError

    params = call.final_params()
    ex = Exchange(req=call, url=f"{call.service}:{cfg.aws_region or 'default'}/{call.operation}", sent_headers={}, kind="boto", dry_run=dry_run)
    if dry_run:
        err = validate_offline(cfg, call)
        if err:
            ex.error, ex.client_side = f"ParamValidationError: {err}", True
        return ex

    client = make_client(cfg, call.service, call.bad_credentials)
    ex.url = f"{call.service}:{region_of(client, cfg)}/{call.operation}"
    attempt = 0
    while True:
        t0 = time.perf_counter()
        ex.events, ex.data, ex.error, ex.err_code, ex.client_side = None, None, None, None, False
        try:
            resp = getattr(client, call.operation)(**params)
            ex.ttfb_ms = round((time.perf_counter() - t0) * 1000, 1)
            meta = resp.get("ResponseMetadata", {})
            ex.status, ex.resp_headers = meta.get("HTTPStatusCode"), {k.lower(): v for k, v in (meta.get("HTTPHeaders") or {}).items()}
            ex.reason = "OK"
            if call.operation in STREAM_OPS:
                ex.events = []
                try:
                    for i, ev in enumerate(resp[STREAM_OPS[call.operation]]):
                        if i == 0:
                            ex.ttfb_ms = round((time.perf_counter() - t0) * 1000, 1)
                        ex.events.append(ev)
                except ClientError as se:  # erreur au milieu du flux : on garde ce qui a été reçu
                    ex.err_code = se.response.get("Error", {}).get("Code")
                    ex.error = f"stream interrompu: {se.response.get('Error', {}).get('Message')}"
                ex.chunks = len(ex.events)
                ex.data = {k: v for k, v in resp.items() if k not in (STREAM_OPS[call.operation], "ResponseMetadata")}
            else:
                if "body" in resp and hasattr(resp["body"], "read"):  # invoke_model : StreamingBody
                    raw = resp["body"].read()
                    resp = {**resp, "body": _try_json(raw)}
                ex.data = resp
            ex.total_ms = round((time.perf_counter() - t0) * 1000, 1)
        except ClientError as e:
            ex.total_ms = round((time.perf_counter() - t0) * 1000, 1)
            ex.data = e.response
            meta = e.response.get("ResponseMetadata", {})
            ex.status, ex.resp_headers = meta.get("HTTPStatusCode"), {k.lower(): v for k, v in (meta.get("HTTPHeaders") or {}).items()}
            ex.err_code = e.response.get("Error", {}).get("Code")
            ex.reason = ex.err_code or "ClientError"
            ex.error = f"{ex.err_code}: {e.response.get('Error', {}).get('Message')}"
        except ParamValidationError as e:  # rejeté par botocore avant l'envoi
            ex.total_ms = round((time.perf_counter() - t0) * 1000, 1)
            ex.client_side, ex.error, ex.reason = True, f"ParamValidationError: {e}", "client-side"
        except (BotoCoreError, OSError) as e:  # identifiants absents, DNS, timeout, ...
            ex.total_ms = round((time.perf_counter() - t0) * 1000, 1)
            ex.error = f"{type(e).__name__}: {e}"
        if ex.err_code in ("ThrottlingException", "TooManyRequestsException") and attempt < 3:
            time.sleep(2 ** attempt * 2)
            attempt += 1
            ex.retries = attempt
            continue
        return ex


def _try_json(raw: bytes) -> Any:
    try:
        return json.loads(raw)
    except Exception:
        return {"__raw_text__": raw.decode("utf-8", "replace")}
