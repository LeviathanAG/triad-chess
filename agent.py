"""EDIT THIS FILE. Replace prompting, tools, memory or the entire harness as you prefer."""

from chess_analysis import analyze, candidate_subset, model_messages
from chess_sdk import Decision
from chess_tools import position_notes, terminal_candidates


def choose(context):
    # Put your own search, retrieval, memory, LangChain/Pi orchestration, etc. here.
    # Keep CPU tools cancellable: call context.check_cancelled() inside long loops.
    # Original, bounded terminal-rule search. The model still selects from this
    # legal subset and supplies the actual completed request as move evidence.
    notes = position_notes(
        context.position, getattr(context, "check_cancelled", lambda: None), seconds=0.2
    )
    candidates = terminal_candidates(context.position, notes)
    config = context.initial.get("harness_config", {})
    analysis_budget = min(
        config.get("analysis_seconds", 0.8), max(0.02, context.remaining_seconds * 0.01)
    )
    analysis = analyze(
        context.position | {"legal_moves": candidates},
        getattr(context, "check_cancelled", lambda: None),
        seconds=analysis_budget,
    )
    candidates = candidate_subset(analysis, candidates)
    messages = model_messages(context.position, analysis, candidates)
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
                "reasoning_budget_tokens",
                (96 if max_tokens is None else min(96, max(0, max_tokens - reserve)))
                if effort != "none"
                else 0,
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
