"""LLM calls: Google Gemini (free tier) first, Claude as the paid backup.

Claude also handles the rare web-search research step. Costs are logged per run.
"""
import json
import logging
import os
import time

import anthropic
import requests

from . import config

client = anthropic.Anthropic() if os.getenv("ANTHROPIC_API_KEY") else None
log = logging.getLogger("ytauto")

# USD per million tokens for claude-opus-5-5, and per web search.
PRICE_IN, PRICE_OUT, PRICE_CACHE_READ, PRICE_SEARCH = 4.00, 20.00, 0.20, 0.01
spent_usd = 0.0


def _track(usage):
    global spent_usd
    searches = getattr(getattr(usage, "server_tool_use", None), "web_search_requests", 0) or 0
    cost = (
        usage.input_tokens * PRICE_IN
        + (usage.cache_creation_input_tokens or 0) * PRICE_IN * 1.25
        + (usage.cache_read_input_tokens or 0) * PRICE_CACHE_READ
        + usage.output_tokens * PRICE_OUT
    ) / 1_000_000 + searches * PRICE_SEARCH
    spent_usd += cost
    log.info("Claude: %d in / %d out tokens, %d searches = $%.3f (run total $%.3f)",
             usage.input_tokens, usage.output_tokens, searches, cost, spent_usd)


def _call(messages, max_tokens=16000, **kwargs):
    while True:
        with client.beta.messages.stream(
            model=config.MODEL,
            max_tokens=max_tokens,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=messages,
            **kwargs,
        ) as stream:
            response = stream.get_final_message()
        _track(response.usage)

        if response.stop_reason == "pause_turn":
            # Long web-search turns pause; send the partial turn back to continue it.
            messages = messages + [{"role": "assistant", "content": response.content}]
            continue
        if response.stop_reason == "refusal":
            raise RuntimeError(f"Claude declined the request: {response.stop_details}")
        if response.stop_reason == "max_tokens":
            raise RuntimeError("Claude response was cut off at max_tokens")
        return response


def _final_text(response):
    # If a fallback model took over mid-turn, only the text after the switch counts.
    blocks = list(response.content)
    last_switch = max((i for i, b in enumerate(blocks) if b.type == "fallback"), default=-1)
    return "".join(b.text for b in blocks[last_switch + 1:] if b.type == "text").strip()


def research(prompt, max_searches=3):
    """Free-text answer grounded in live web search."""
    response = _call(
        [{"role": "user", "content": prompt}],
        tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": max_searches}],
        output_config={"effort": "low"},
    )
    return _final_text(response)


GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODELS = [m for m in dict.fromkeys([os.getenv("GEMINI_MODEL", ""), "gemini-3.5-flash", "gemini-flash-latest",
                                           "gemini-3.1-flash-lite"]) if m]


def _gemini_parts(prompt):
    if isinstance(prompt, str):
        return [{"text": prompt}]
    parts = []
    for block in prompt:
        if block.get("type") == "text":
            parts.append({"text": block["text"]})
        elif block.get("type") == "image" and block.get("source", {}).get("type") == "base64":
            parts.append({"inline_data": {"mime_type": block["source"]["media_type"], "data": block["source"]["data"]}})
    return parts


def _gemini_structured(prompt, schema, system):
    body = {"contents": [{"role": "user", "parts": _gemini_parts(prompt)}],
            "generationConfig": {"responseMimeType": "application/json", "responseJsonSchema": schema,
                                 "maxOutputTokens": 16000}}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    last = None
    for model in [m for m in GEMINI_MODELS for _ in range(3)]:  # each model up to 3 tries: free tier is often "busy"
        try:
            if last and " 503 " in f" {last} ":
                time.sleep(20)
            r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                              headers={"x-goog-api-key": GEMINI_KEY}, json=body, timeout=150)
            if r.status_code in (404, 429, 500, 503):  # model missing, free quota used up, or busy: try again/next
                last = f"{model}: HTTP {r.status_code} {r.text[:120]}"
                log.warning("Gemini %s", last)
                continue
            r.raise_for_status()
            data = r.json()
            text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"] if not p.get("thought"))
            result = json.loads(text)
            missing = [k for k in schema.get("required", []) if k not in result]
            if missing:
                raise ValueError(f"missing fields {missing}")
            u = data.get("usageMetadata", {})
            log.info("Gemini %s (free): %s in / %s out tokens", model, u.get("promptTokenCount"), u.get("candidatesTokenCount"))
            return result
        except (requests.RequestException, KeyError, IndexError, ValueError) as e:
            last = f"{model}: {e}"
            log.warning("Gemini %s", last)
    raise RuntimeError(f"All Gemini models failed ({last})")


def structured(prompt, schema, system=None, effort="medium"):
    """JSON answer matching `schema`. `prompt` is text or a list of content blocks (text + base64 images).

    Tries free Gemini first; falls back to Claude (paid) if Gemini is missing or fails.
    """
    if GEMINI_KEY:
        try:
            return _gemini_structured(prompt, schema, system)
        except RuntimeError as e:
            log.warning("%s; using Claude instead", e)
    kwargs = {"output_config": {"effort": effort, "format": {"type": "json_schema", "schema": schema}}}
    if system:
        kwargs["system"] = system
    response = _call([{"role": "user", "content": prompt}], **kwargs)
    return json.loads(_final_text(response))
