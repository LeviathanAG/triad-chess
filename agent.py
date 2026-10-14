"""EDIT THIS FILE. Replace prompting, tools, memory or the entire harness as you prefer."""

import json

from chess_sdk import Decision
from chess_tools import position_notes, terminal_candidates


def choose(context):
    # Put your own search, retrieval, memory, LangChain/Pi orchestration, etc. here.
    # Keep CPU tools cancellable: call context.check_cancelled() inside long loops.
    # Original, bounded terminal-rule search. The model still selects from this
    # legal subset and supplies the actual completed request as move evidence.
    notes = position_notes(context.position, getattr(context, 'check_cancelled', lambda: None), seconds=.2)
    candidates = terminal_candidates(context.position, notes)
    messages = [
        {
            "role": "system",
            "content": "You play chess. Analyze the position and select the best legal move. Put any reasoning in your model's thinking section. Your final answer must be a JSON string containing one legal UCI move, for example \"e2e4\".",
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "fen": context.position["fen"],
                    "legal_moves": candidates,
                    "clock": context.position["clock"],
                    "last_rejection": context.last_response
                    if context.last_response and not context.last_response.get("accepted")
                    else None,
                }
            ),
        },
    ]
    if notes['mate_in_one']:
        messages[0]['content'] += ' The rules checker verified that every supplied candidate is immediate checkmate; choose one to win now.'
    elif len(candidates) < len(context.position['legal_moves']):
        messages[0]['content'] += ' The rules checker excluded moves with a verified enemy mate-in-one reply. Analyze the supplied remaining choices.'
    # Actual clocks come from observations. Leave time to serialize and deliver the move.
    budget = max(0.05, context.remaining_seconds - 0.5) if context.own_turn else 120
    # Recommended final move: explicitly constrain the answer to legal moves.
    # Earlier planning/tool calls can omit this response_format and decoding.
    # inference.generate_move() is a convenience helper for the same pattern.
    move_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "chess_move_selection",
            "strict": True,
            "schema": {"type": "string", "enum": candidates},
        },
    }
    capabilities = context.initial["inference"]
    config = context.initial.get("harness_config", {})
    max_tokens = config.get("max_tokens", 512)
    legacy_cap = context.initial["limits"].get("output_tokens")
    if legacy_cap is not None and max_tokens is not None:
        max_tokens = min(max_tokens, legacy_cap)
    controls = {}
    if capabilities.get("reasoning_efforts"):
        effort = config.get("reasoning_effort")
        if effort is not None and effort not in capabilities["reasoning_efforts"]:
            raise ValueError("Unsupported reasoning_effort in harness_config")
        reserve = capabilities["answer_token_reserve"]
        controls = {
            "reasoning_budget_tokens": config.get(
                "reasoning_budget_tokens", (96 if max_tokens is None else min(96, max(0, max_tokens - reserve))) if effort != "none" else 0
            ),
        }
        if effort is not None:
            controls["reasoning_effort"] = effort
    trace = context.inference.generate(
        context.position,
        messages,
        cancel=context.cancel,
        timeout=budget,
        max_tokens=max_tokens,
        temperature=0,
        decoding="uci",
        response_format=move_format,
        **controls,
    )
    return Decision.from_trace(trace)
