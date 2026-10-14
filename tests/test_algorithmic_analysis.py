import chess
import pytest

from chess_analysis import MATE, Search, SearchExpired, analyze, candidate_subset


def state(fen):
    board = chess.Board(fen)
    return {"fen": board.fen(), "legal_moves": [m.uci() for m in board.legal_moves]}


def test_quiescence_distinguishes_poisoned_bishop_and_queen_captures():
    position = state("rnb1kbnr/pp2pppp/2p5/1B1q4/8/8/PPPP1PPP/RNBQK1NR w KQkq - 0 4")
    result = analyze(position, seconds=2, max_depth=1)
    scores = {row["uci"]: row["score"] for row in result["scores"]}
    assert result["completed_depth"] == 1
    assert scores["b5c6"] < scores["b5f1"] - 100
    assert scores["d1h5"] < scores["b5f1"] - 600
    assert "d1h5" not in candidate_subset(result, position["legal_moves"])


def test_actual_checkmate_precedes_fifty_move_draw_in_search():
    position = state("7k/8/5KQ1/8/8/8/8/8 w - - 99 1")
    result = analyze(position, seconds=0.2, max_depth=1)
    mate = next(row for row in result["scores"] if row["uci"] == "g6g7")
    assert mate["score"] == MATE - 1
    assert candidate_subset(result, position["legal_moves"]) == ["g6g7"]


def test_fifty_move_draw_scores_zero_and_retains_legal_choices():
    position = state("8/K5k1/8/8/8/8/1q6/5r2 w - - 99 1")
    result = analyze(position, seconds=0.2)
    assert all(row["score"] == 0 for row in result["scores"])
    assert set(candidate_subset(result, position["legal_moves"])) == set(position["legal_moves"])


def test_expired_search_unwinds_board_and_only_exports_complete_root_snapshot():
    board = chess.Board()
    search = Search(board, lambda: None, -1)
    with pytest.raises(SearchExpired):
        search.node(board, 4, -MATE * 2, MATE * 2, 0)
    assert board.fen() == chess.STARTING_FEN
    assert not board.move_stack
    position = state(chess.STARTING_FEN)
    result = analyze(position, seconds=0)
    assert result["completed_depth"] == 0
    assert {row["uci"] for row in result["scores"]} == set(position["legal_moves"])


def test_algorithmic_search_cancels_without_a_coded_move_fallback():
    def cancelled():
        raise RuntimeError("cancelled")

    with pytest.raises(RuntimeError, match="cancelled"):
        analyze(state(chess.STARTING_FEN), cancelled)


def test_root_cutoff_bounds_are_valid_and_not_used_as_candidate_scores():
    position = state("rnb1kbnr/pp2pppp/2p5/1B1q4/8/8/PPPP1PPP/RNBQK1NR w KQkq - 0 4")
    exhaustive = analyze(position, seconds=3, max_depth=2, root_pruning=False)
    pruned = analyze(position, seconds=3, max_depth=2, root_pruning=True)
    assert exhaustive["completed_depth"] == pruned["completed_depth"] == 2
    assert exhaustive["scores"][0]["score"] == pruned["scores"][0]["score"]
    truth = {row["uci"]: row["score"] for row in exhaustive["scores"]}
    admitted = candidate_subset(pruned, position["legal_moves"])
    bounded = 0
    for row in pruned["scores"]:
        if row.get("score_bound") == "upper":
            bounded += 1
            assert row["score"] >= truth[row["uci"]]
            assert row["uci"] not in admitted
        else:
            assert row["score"] == truth[row["uci"]]
    assert bounded and pruned["nodes"] < exhaustive["nodes"]
