import chess
import pytest

from chess_tools import board_from_position, position_notes, terminal_candidates, terminal_draw


def position(board):
    return {'fen': board.fen(), 'legal_moves': [m.uci() for m in board.legal_moves]}


def test_candidates_are_actual_mates_when_a_win_exists():
    board = chess.Board('7k/8/5KQ1/8/8/8/8/8 w - - 0 1')
    candidates = terminal_candidates(position(board))
    assert 'g6g7' in candidates
    assert len(candidates) < len(list(board.legal_moves))
    for uci in candidates:
        board.push_uci(uci)
        assert board.is_checkmate()
        board.pop()


def test_fifty_move_draw_prevents_hypothetical_enemy_mate_filter():
    board = chess.Board('8/K5k1/8/8/8/8/1q6/5r2 w - - 0 1')
    notes = position_notes(position(board), seconds=1)
    assert notes['allows_opponent_mate_in_one']['a7a8'] == 'f1a1'
    board.halfmove_clock = 99
    notes = position_notes(position(board), seconds=1)
    assert 'a7a8' not in notes['allows_opponent_mate_in_one']
    assert 'a7a8' in terminal_candidates(position(board), notes)


def test_rebuild_history_preserves_event_threefold_draw():
    moves = ['g1f3', 'g8f6', 'f3g1', 'f6g8', 'g1f3', 'g8f6', 'f3g1']
    board = chess.Board()
    for uci in moves:
        board.push_uci(uci)
    state = position(board) | {'initial_fen': chess.STARTING_FEN, 'moves': moves}
    rebuilt = board_from_position(state)
    rebuilt.push_uci('f6g8')
    assert terminal_draw(rebuilt)
    assert not terminal_draw(chess.Board(rebuilt.fen()))
    with pytest.raises(ValueError, match='history does not match'):
        board_from_position(state | {'moves': []})


def test_all_proven_losing_moves_still_leave_nonempty_model_choices():
    state = position(chess.Board())
    notes = {'mate_in_one': [], 'allows_opponent_mate_in_one': dict.fromkeys(state['legal_moves'], 'witness')}
    assert terminal_candidates(state, notes) == state['legal_moves']


def test_search_honors_cancellation():
    def cancelled():
        raise RuntimeError('cancelled')
    with pytest.raises(RuntimeError, match='cancelled'):
        position_notes(position(chess.Board()), cancelled)
