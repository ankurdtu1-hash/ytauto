"""Thin wrapper around the Claude API with refusal fallback, pause_turn handling and cost logging."""
import json
import logging

import anthropic

from . import config

client = anthropic.Anthropic()
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


def structured(prompt, schema, system=None, effort="medium"):
    """JSON answer that is guaranteed to match `schema`. `prompt` is text or a list of content blocks."""
    kwargs = {"output_config": {"effort": effort, "format": {"type": "json_schema", "schema": schema}}}
    if system:
        kwargs["system"] = system
    response = _call([{"role": "user", "content": prompt}], **kwargs)
    return json.loads(_final_text(response))
