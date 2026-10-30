"""Thin wrapper around the Claude API with refusal fallback and pause_turn handling."""
import json

import anthropic

from . import config

client = anthropic.Anthropic()


def _call(messages, **kwargs):
    while True:
        with client.beta.messages.stream(
            model=config.MODEL,
            max_tokens=32000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=messages,
            **kwargs,
        ) as stream:
            response = stream.get_final_message()

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


def research(prompt, max_searches=6):
    """Free-text answer grounded in live web search."""
    response = _call(
        [{"role": "user", "content": prompt}],
        tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": max_searches}],
        output_config={"effort": "medium"},
    )
    return _final_text(response)


def structured(prompt, schema, system=None):
    """JSON answer that is guaranteed to match `schema`."""
    kwargs = {"output_config": {"effort": "high", "format": {"type": "json_schema", "schema": schema}}}
    if system:
        kwargs["system"] = system
    response = _call([{"role": "user", "content": prompt}], **kwargs)
    return json.loads(_final_text(response))
