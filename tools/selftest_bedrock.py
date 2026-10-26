"""Auto-test du transport boto3 SANS AWS : un faux client imite Converse/ConverseStream/InvokeModel (+ ClientError).
Ne reproduit pas Bedrock ; vérifie la capture, les résumés, les rapports. Usage : uv run python tools/selftest_bedrock.py
"""
import io
import json
import os
import sys

from botocore.exceptions import ClientError

from mmprobe import bedrock, cli


def err(code, msg, status=400):
    return ClientError({"Error": {"Code": code, "Message": msg}, "ResponseMetadata": {"HTTPStatusCode": status, "HTTPHeaders": {"x-amzn-requestid": "fake"}}}, "Converse")


def meta(status=200):
    return {"HTTPStatusCode": status, "HTTPHeaders": {"x-amzn-requestid": "fake", "content-type": "application/json"}}


class FakeRuntime:
    bad = False

    def _check(self, params):
        if self.bad:
            raise err("UnrecognizedClientException", "The security token included in the request is invalid.", 403)
        for m in params.get("messages", []):
            for b in m["content"]:
                if "image" in b:
                    if m["role"] != "user":
                        raise err("ValidationException", "images can only be included in user messages")
                    if len(b["image"]["source"].get("bytes", b"x")) > 3_750_000:
                        raise err("ValidationException", "Input is too long for requested model: image exceeds 3.75 MB")
                    if "micro" in params["modelId"]:
                        raise err("ValidationException", "This model doesn't support the image content block.")
                if "audio" in b and "voxtral" not in params["modelId"]:
                    raise err("ValidationException", "This model doesn't support the audio content block.")

    def converse(self, **p):
        self._check(p)
        tool = p.get("toolConfig")
        content = [{"toolUse": {"toolUseId": "t1", "name": "report_shapes", "input": {"count": 3}}}] if tool else [{"text": "A red square, a blue circle and a green triangle."}]
        return {"ResponseMetadata": meta(), "output": {"message": {"role": "assistant", "content": content}}, "stopReason": "tool_use" if tool else "end_turn",
                "usage": {"inputTokens": 1200, "outputTokens": 20, "totalTokens": 1220}, "metrics": {"latencyMs": 840}}

    def converse_stream(self, **p):
        self._check(p)
        evs = [{"messageStart": {"role": "assistant"}}, {"contentBlockDelta": {"delta": {"text": "A red "}, "contentBlockIndex": 0}},
               {"contentBlockDelta": {"delta": {"text": "square."}, "contentBlockIndex": 0}}, {"contentBlockStop": {"contentBlockIndex": 0}},
               {"messageStop": {"stopReason": "end_turn"}}, {"metadata": {"usage": {"inputTokens": 1200, "outputTokens": 5, "totalTokens": 1205}, "metrics": {"latencyMs": 700}}}]
        return {"ResponseMetadata": meta(), "stream": iter(evs)}

    def invoke_model(self, **p):
        if "sonic" in p["modelId"]:
            raise err("ValidationException", "Invocation of model ID amazon.nova-2-sonic-v1:0 with on-demand throughput isn't supported.")
        body = json.loads(p["body"])
        if any(c.get("source", {}).get("type") == "url" for m in body.get("messages", []) for c in m["content"] if isinstance(c, dict) and "source" in c):
            raise err("ValidationException", "messages.0.content.1.image.source.type: Input should be 'base64'")
        return {"ResponseMetadata": meta(), "contentType": "application/json", "body": io.BytesIO(json.dumps({"content": [{"type": "text", "text": "A red square."}], "stop_reason": "end_turn", "usage": {"input_tokens": 1100, "output_tokens": 9}}).encode())}

    def count_tokens(self, **p):
        return {"ResponseMetadata": meta(), "inputTokens": 1180}


def factory(cfg, service, bad):
    c = FakeRuntime(); c.bad = bad
    return c


if __name__ == "__main__":
    bedrock.CLIENT_FACTORY = factory
    os.environ.update({"MM_PROVIDER": "bedrock", "MM_AWS_REGION": "eu-west-3", "MM_LABEL": "bedrock-selftest",
                       "MM_BEDROCK_MODEL_VISION": "eu.anthropic.claude-haiku-4-5", "MM_BEDROCK_MODEL_VISION_NOVA": "eu.amazon.nova-lite-v1:0",
                       "MM_BEDROCK_MODEL_AUDIO_IN": "mistral.voxtral-small-24b-2507", "MM_BEDROCK_MODEL_AUDIO_IN_MINI": "mistral.voxtral-mini-3b-2507",
                       "MM_BEDROCK_MODEL_TEXT_ONLY": "amazon.nova-micro-v1:0", "MM_BEDROCK_MODEL_SONIC": "amazon.nova-2-sonic-v1:0"})
    sys.exit(cli.main(["run", "--fresh", "-k", "chat-image/", "-k", "speech/", "-k", "transcriptions/model_", "-k", "chat-audio/in_wav"]))
