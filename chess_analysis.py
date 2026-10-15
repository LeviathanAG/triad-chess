"""Original bounded algorithmic chess analysis, written during the event.

No engine imports, copied engine routines, books, tablebases or learned weights.
This hand-written minimax/capture search provides candidates and factual lines;
the approved LLM makes the final selection using a completed inference request.
Rulebook section 3.4 explicitly permits team-written algorithmic analysis.
"""

import json
import time

import chess

from chess_tools import board_from_position

VALUE = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}
MATE = 100000


class SearchExpired(Exception):
    pass


def position_key(board):
    return (
        board.pawns,
        board.knights,
        board.bishops,
        board.rooks,
        board.queens,
        board.kings,
        board.occupied_co[chess.WHITE],
        board.occupied_co[chess.BLACK],
        board.turn,
        board.clean_castling_rights(),
        board.ep_square if board.has_legal_en_passant() else None,
    )


def evaluate(board):
    """Hand-crafted material/development geometry; no externally fitted weights."""
    nonpawn = sum(
        VALUE[p.piece_type]
        for p in board.piece_map().values()
        if p.piece_type not in (chess.PAWN, chess.KING)
    )
    score = 0
    for colour in (chess.WHITE, chess.BLACK):
        subtotal = 0
        bishops = 0
        for square in chess.scan_forward(board.occupied_co[colour]):
            kind = board.piece_type_at(square)
            file = chess.square_file(square)
            rank = chess.square_rank(square)
            advance = rank if colour else 7 - rank
            center = 7 - abs(2 * file - 7) - abs(2 * rank - 7)
            subtotal += VALUE[kind]
            if kind == chess.PAWN:
                subtotal += advance * (6 if nonpawn < 2500 else 3)
                if file in (3, 4):
                    subtotal += advance * 3
            elif kind == chess.KNIGHT:
                subtotal += center * 6
            elif kind == chess.BISHOP:
                bishops += 1
                subtotal += center * 3
            elif kind == chess.ROOK:
                file_pawns = board.pawns & chess.BB_FILES[file]
                if not file_pawns:
                    subtotal += 18
                elif not (file_pawns & board.occupied_co[colour]):
                    subtotal += 9
                if advance == 6:
                    subtotal += 15
            elif kind == chess.QUEEN:
                subtotal += center
                if board.fullmove_number <= 10:
                    subtotal -= advance * 5
            else:
                if nonpawn >= 2500:
                    subtotal -= advance * 25
                    if file in (2, 6) and advance == 0:
                        subtotal += 35
                    shield_rank = rank + (1 if colour else -1)
                    if 0 <= shield_rank < 8:
                        for shield_file in range(max(0, file - 1), min(7, file + 1) + 1):
                            p = board.piece_at(chess.square(shield_file, shield_rank))
                            if p == chess.Piece(chess.PAWN, colour):
                                subtotal += 8
                else:
                    subtotal += center * 6
        if bishops >= 2:
            subtotal += 20
        score += subtotal if colour else -subtotal
    return score if board.turn else -score


class Search:
    def __init__(self, board, cancel, seconds):
        self.cancel = cancel
        self.deadline = time.monotonic() + seconds
        self.nodes = 0
        self.repetitions = {}
        self.ordering = {}
        self.evaluations = {}
        copy = board.copy(stack=True)
        while True:
            self.cancel()
            key = position_key(copy)
            self.repetitions[key] = self.repetitions.get(key, 0) + 1
            if not copy.move_stack:
                break
            copy.pop()

    def checkpoint(self):
        self.nodes += 1
        if self.nodes % 16 == 0:
            self.cancel()
            if time.monotonic() >= self.deadline:
                raise SearchExpired

    def push(self, board, move):
        board.push(move)
        key = position_key(board)
        self.repetitions[key] = self.repetitions.get(key, 0) + 1
        return key

    def pop(self, board, key):
        self.repetitions[key] -= 1
        board.pop()

    def static(self, board, key):
        key = key + (min(board.fullmove_number, 11),)
        if key not in self.evaluations:
            if len(self.evaluations) >= 12000:
                self.evaluations.clear()
            self.evaluations[key] = evaluate(board)
        return self.evaluations[key]

    def ordered(self, board, moves, key):
        previous = self.ordering.get(key)

        def priority(move):
            target = board.piece_type_at(move.to_square)
            captures = VALUE.get(target, 100 if board.is_en_passant(move) else 0)
            return (
                (10000 if move == previous else 0)
                + (
                    2000 + captures * 10 - VALUE[board.piece_type_at(move.from_square)]
                    if board.is_capture(move)
                    else 0
                )
                + (1500 + VALUE[move.promotion] if move.promotion else 0)
                + (70 if board.gives_check(move) else 0)
            )

        return sorted(moves, key=priority, reverse=True)

    def node(self, board, depth, alpha, beta, ply, qleft=4):
        self.checkpoint()
        key = position_key(board)
        moves = list(board.legal_moves)
        if not moves:
            return (-MATE + ply if board.is_check() else 0), []
        # Checkmate precedence already handled before event's automatic draws.
        if (
            board.halfmove_clock >= 100
            or self.repetitions.get(key, 0) >= 3
            or board.is_insufficient_material()
        ):
            return 0, []
        checked = board.is_check()
        if depth <= 0:
            stand = self.static(board, key)
            if qleft <= 0:
                return stand, []
            if not checked:
                if stand >= beta:
                    return stand, []
                alpha = max(alpha, stand)
                moves = [m for m in moves if board.is_capture(m) or m.promotion]
                if not moves:
                    return stand, []
            best = -MATE * 2 if checked else stand
        else:
            best = -MATE * 2
        line = []
        for move in self.ordered(board, moves, key):
            child_key = self.push(board, move)
            try:
                child, child_line = self.node(
                    board, depth - 1, -beta, -alpha, ply + 1, qleft - 1 if depth <= 0 else qleft
                )
            finally:
                self.pop(board, child_key)
            score = -child
            if score > best:
                best = score
                line = [move.uci()] + child_line
                if len(self.ordering) >= 12000:
                    self.ordering.clear()
                self.ordering[key] = move
            alpha = max(alpha, score)
            if alpha >= beta:
                break
        return best, line


def analyze(position, check_cancelled=lambda: None, seconds=0.8, max_depth=4, root_pruning=True):
    started = time.monotonic()
    board = board_from_position(position, check_cancelled)
    legal = [chess.Move.from_uci(x) for x in position["legal_moves"]]
    if any(m not in board.legal_moves for m in legal):
        raise ValueError("analysis moves not legal for FEN")
    search = Search(board, check_cancelled, seconds)
    scores = []
    # Always establish one complete, cheap snapshot before iterative search.
    for move in legal:
        check_cancelled()
        san = board.san(move)
        key = search.push(board, move)
        try:
            if board.is_checkmate():
                score = MATE - 1
            elif (
                board.halfmove_clock >= 100
                or search.repetitions.get(key, 0) >= 3
                or board.is_game_over()
            ):
                score = 0
            else:
                score = -evaluate(board)
        finally:
            search.pop(board, key)
        scores.append({"uci": move.uci(), "san": san, "score": score, "line": [move.uci()]})
    scores.sort(key=lambda x: x["score"], reverse=True)
    completed = 0
    for depth in range(1, max_depth + 1):
        trial = []
        trial_best = -MATE * 2
        try:
            for previous in scores:
                check_cancelled()
                if time.monotonic() >= search.deadline:
                    raise SearchExpired
                move = chess.Move.from_uci(previous["uci"])
                key = search.push(board, move)
                limit = -trial_best + 65 if root_pruning and trial else MATE * 2
                try:
                    score, line = search.node(board, depth - 1, -MATE * 2, limit, 1)
                finally:
                    search.pop(board, key)
                bounded = root_pruning and bool(trial) and -score <= trial_best - 65
                row = {
                    "uci": move.uci(),
                    "san": previous["san"],
                    "score": -score,
                    "line": [move.uci()] + line,
                }
                if bounded:
                    row["score_bound"] = "upper"
                else:
                    trial_best = max(trial_best, -score)
                trial.append(row)
        except SearchExpired:
            break
        scores = sorted(trial, key=lambda x: x["score"], reverse=True)
        completed = depth
        if scores and scores[0]["score"] >= MATE - 10:
            break
    return {
        "completed_depth": completed,
        "nodes": search.nodes,
        "seconds": round(time.monotonic() - started, 4),
        "method": "original bounded minimax, capture quiescence and handcrafted material/development/king safety; not a learned evaluator",
        "scores": scores,
    }


def candidate_subset(analysis, legal, max_choices=4, tolerance=65, secondary_tolerance=120):
    exact = [x for x in analysis["scores"] if "score_bound" not in x]
    if not exact:
        return legal
    best = exact[0]["score"]
    # Native mate scores encode ply distance, not centipawns. The fixed
    # evaluation is far below this band; native depth<=12 plus four capture
    # plies cannot reach a 100-ply distance. Retain equal best distances only.
    if abs(best) >= MATE - 100:
        return [x["uci"] for x in exact if x["score"] == best][:max_choices]
    candidates = [x["uci"] for x in exact if x["score"] >= best - tolerance][:max_choices]
    # Allow a meaningful model comparison when the second choice is close.
    if len(candidates) == 1 and len(exact) > 1 and exact[1]["score"] >= best - secondary_tolerance:
        candidates.append(exact[1]["uci"])
    return candidates or legal


def model_messages(position, analysis, candidates):
    rows = [x for x in analysis["scores"] if x["uci"] in candidates]
    return [
        {
            "role": "system",
            "content": "Choose the strongest chess move from the supplied candidates. Our original algorithmic analysis searched legal continuations and estimated material, development and king safety. Scores are shallow hand-written estimates, not proofs except a verified mate. Higher scores favor you. Compare the candidates, tactical lines and king safety, then select the best move yourself. Return exactly a JSON string containing its legal UCI code.",
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "fen": position["fen"],
                    "side_to_move": "white" if chess.Board(position["fen"]).turn else "black",
                    "completed_search_depth": analysis["completed_depth"],
                    "search_nodes": analysis["nodes"],
                    "candidate_analysis": rows,
                }
            ),
        },
    ]
