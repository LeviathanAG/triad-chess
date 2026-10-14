# Chess harness provenance and validation

Team: TungMasterSoloClear / TECHTEAM11600. This is private development source,
not an official entry or a claim of tournament strength.

The organizer SDK is based on Sir-Nike/chessSDK commit
2572686cfe2653e1fe8680f631008cd27962ee47. The configured approved model remains
`qwen`, with frozen organizer-selected Q4_K_M weights and no adapter. No additional
learned evaluator or model server is bundled in the participant image.

`chess_tools.py` contains original, AI-assisted terminal-rule search written
during the event. It uses the organizer-permitted python-chess 1.11.2 rules
library for legal moves, checkmate, and draw checks. It contains no imported
engine, engine fork, or copied engine search/evaluation code. The runtime wheel
is vendored with its upstream metadata/license and recorded SHA-256.

The tool reconstructs the supplied move history and checks it against current
FEN. It searches for immediate own checkmates and actual opponent mate-in-one
reply witnesses. It respects the event's automatic current-position threefold
and fifty-move draws, with checkmate precedence. Search is cancellable and the
reply probe has a 0.2 second wall-clock budget. Incomplete probing removes only
moves with a verified losing witness; unprobed moves are not certified safe.
If every move has a losing witness, all legal choices remain available.

The resulting legal subset is passed to the final strict JSON schema. The
approved model still completes the final inference request and selects the
submitted move. The harness returns `Decision.from_trace` without replacing
invalid output with a coded fallback. The SDK explicitly permits original
tactical search in rules/RULES.md and legal candidate subsets, including scalar
enums, in docs/reasoning.md. General prompting and reasoning defaults otherwise
retain the starter behavior.

Development-only tests use exact approved GGUFs and a local llama.cpp runtime
pinned to 097cf33d9499b1eade67d51e16d7c75427e7b267. Stockfish 17.1 is a separate
development opponent/offline diagnostic reference. It never supplies inference
context or moves, and neither Stockfish nor the development scripts/model files
is included in this repository's participant runtime.

Validation: 39 SDK tests passed, with one optional organizer test skipped. New
regressions cover actual mate candidates, the fifty-move draw edge, reconstructed
threefold history, nonempty candidate lists, and cancellation. The Docker fixture
checks both colors with network disabled, a read-only root, one CPU and 1 GiB RAM.
These fixtures validate protocol/evidence behavior using a fake gateway.

An independent 64-position synthetic king/queen/rook mate-in-one set
(seed 2026101458) produced 64 legal actual Horizon Q4_K_M completions and 64 mates
with the terminal subset. This is narrow tactical/decoding evidence, not a general
rating and not validation of a different base's serving behavior. Earlier
Nemotron and Horizon experimental full games lost to local Stockfish skill 0,
depth 3. Those experimental general prompts were not adopted. General playing
strength remains under active development; no win or global optimum is claimed.
