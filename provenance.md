# Chess development harness provenance and validation

Team: TungMasterSoloClear / TECHTEAM11600. This private development branch is
not an official entry. The default branch remains subject to the organizer freeze.

The organizer SDK starts at Sir-Nike/chessSDK commit
2572686cfe2653e1fe8680f631008cd27962ee47. This development configuration selects
`gemma`: the exact organizer-approved gemma-4-E4B-it-Q4_K_M.gguf, revision
bfc15c382204943c3a8fff0c750b94ae2364d7a3, SHA-256
85a896a047553e842f25297ee5b031d64ff30147d9c4af17b1e4b394cd1fab87.
Its weights are frozen and no adapter is supplied. No extra learned evaluator,
model server, opening book or tablebase is bundled in the participant image.

`chess_tools.py` and `chess_analysis.py` contain original AI-assisted algorithmic
analysis written during the event. The authoritative Rulebook section 3.4 permits
team-written algorithmic search, planning and analysis. No imported engine,
engine fork or copied engine search/evaluation code is used. python-chess 1.11.2
provides generic board state, legal moves and terminal rules; the wheel is vendored
with its upstream license/metadata and recorded SHA-256.

The search reconstructs supplied initial FEN and move history and verifies current
FEN. Checkmate precedes the event's automatic threefold and fifty-move draws.
A bounded exact terminal probe finds immediate own mates and opponent mate-in-one
witnesses. Incomplete probing excludes only moves with actual losing witnesses.
If all moves have such witnesses, the final candidate list remains nonempty.

The additional search is an original iterative minimax traversal with alpha-beta
bounds and up to four capture/recapture quiescence plies. Check evasions are searched
as legal responses. Only complete root iterations replace the retained snapshot.
Root fail-high child results are explicitly labeled as upper bounds for the root
move and excluded from final candidate admission; they are not treated as exact
scores. Cancellation and a default 0.8 second budget bound CPU work. The budget
shrinks with authoritative remaining clock, rather than inferring a match format
from current clock readings. Search caches are local to one decision and bounded.

All evaluation formulas and coefficients were selected manually from general
chess principles. They were not fitted to training data, rewards, CEM, reinforcement
learning or supervised labels. The formulas are original code: pawn=100, knight=320,
bishop=330, rook=500, queen=900; doubled-coordinate distance from the center rewards
minor-piece development; pawn advancement receives a small phase-dependent bonus;
rooks receive small open-file/seventh-rank bonuses; a bishop pair receives 20;
early queen excursions are discouraged; middlegame king advancement is penalized
and home pawn shielding/castling shelter rewarded, while endgame king centrality
is encouraged. These are shallow handcrafted estimates, not a learned model or
a proof of a globally best move. No automated parameter fitting is permitted.

The approved LLM selects the final move from a near-best legal subset using the
submitted current FEN. The prompt supplies approximate scores and legal principal
variations with SAN/UCI mapping. The strict final JSON enum constrains those
choices. `Decision.from_trace` preserves completed request evidence; code never
replaces missing/invalid model output with a fallback. SDK docs/reasoning.md
explicitly permits legal candidate subsets. Reasoning is disabled in this
configuration for a compact final selection; the organizer gateway owns native
serving controls.

Development-only tests use exact approved GGUFs and llama.cpp commit
097cf33d9499b1eade67d51e16d7c75427e7b267. Stockfish 17.1 is an external development
opponent and offline diagnostic reference. Neither its source/binary nor reference
scores are supplied as runtime model context. Model files, local servers and
benchmark scripts stay outside this repository's participant image.

Validation: 45 SDK tests passed, with one optional organizer test skipped. Tests
cover actual mates, event draw/history edges, cancellation, snapshot/board unwind,
poisoned captures, legal nonempty candidates and root score-bound semantics.
The fixture passed both colors with one CPU, 512 MiB RAM, 64 PIDs, a read-only root,
64 MiB tmpfs and networking disabled. The fixture checks protocol/evidence with a
fake gateway and is not official organizer approval.

On 48 fresh mixed-color positions from eight development selfplay games, actual
Gemma completions with the original first algorithmic prototype reduced offline
depth-10 Stockfish diagnostic mean regret from 273.02 to 70.02 centipawns and
moves exceeding 200 centipawns regret from 20 to 5. Baseline and prototype both
used the exact terminal guard. Positions within each game are correlated, and
these diagnostics are neither Elo nor official event benchmarks.

A first algorithmic White game won against local Stockfish 17.1, skill 0, depth 3
in 83 plies with 520.7 seconds remaining from a 600 second clock. An initial Black
180 second trial expired on clock while also losing material. After root-bound
pruning and clock-adaptive budgeting, a Black 180 second trial won in 64 plies with
124.2 seconds remaining. Every own move came from an actual completed approved
LLM request. These are a few development games against a deliberately weak
reference setting, not a guarantee of tournament victory or mathematical optimum.
On a second fresh 48-position set, the bound-aware revision reduced mean regret
from 258.96 to 74.92 centipawns and >200 centipawn errors from 25 to 4. A source-game
cluster bootstrap across eight games estimated a mean reduction of 184.04
centipawns, with a 95% interval of 109.31 to 252.94. A White trial against the
slightly deeper skill-0/depth-4 reference also won in 53 plies, with 553.2 seconds
remaining; initial requests may have briefly shared the local server queue with
the tail of position validation, so that timing includes possible additional
queueing. evaluation/ contains compact reports. Further strength and clock
testing remains active; final submission is held.
