"""Original bounded chess rules checks; no imported engine or learned evaluator.

SDK rules/RULES.md explicitly permits original tactical search and general rules
libraries. These notes describe terminal outcomes and legal checks, with no
heuristic score or move choice. The approved LLM retains the final selection.
"""
import time

import chess


def board_from_position(position, check_cancelled=lambda: None):
    current = chess.Board(position['fen'])
    if 'initial_fen' not in position or 'moves' not in position:
        return current
    board = chess.Board(position['initial_fen'])
    for uci in position['moves']:
        check_cancelled()
        board.push_uci(uci)
    if board.fen() != current.fen():
        raise ValueError('move history does not match current FEN')
    return board


def terminal_draw(board):
    # The event applies current-position 3fold/50move automatically, while
    # checkmate takes precedence. Preserve history for this exact rule.
    return not board.is_checkmate() and (board.is_game_over() or board.is_repetition(3) or board.halfmove_clock >= 100)


def position_notes(position, check_cancelled=lambda: None, seconds=.2):
    started = time.monotonic()
    board = board_from_position(position, check_cancelled)
    legal = position['legal_moves']
    notes = {'side_to_move': 'white' if board.turn else 'black',
             'pieces': {chess.square_name(s): ('white ' if p.color else 'black ') + chess.piece_name(p.piece_type) for s,p in sorted(board.piece_map().items())},
             'checking_moves': [], 'mate_in_one': [], 'stalemate_in_one': [],
             'captures': {}, 'allows_queen_capture': {},
             'allows_opponent_mate_in_one': {}, 'reply_checks_complete': True}
    moves = []
    for uci in legal:
        check_cancelled()
        move = chess.Move.from_uci(uci)
        if move not in board.legal_moves:
            raise ValueError('supplied legal move does not match current FEN')
        moves.append(move)
        captured = board.piece_at(move.to_square)
        if captured is not None:
            notes['captures'][uci] = chess.piece_name(captured.piece_type)
        board.push(move)
        if board.is_check():
            notes['checking_moves'].append(uci)
        if board.is_checkmate():
            notes['mate_in_one'].append(uci)
        elif board.is_stalemate():
            notes['stalemate_in_one'].append(uci)
        board.pop()
    # No need to probe replies when a terminal winning move is already available.
    if not notes['mate_in_one']:
        for move in moves:
            check_cancelled()
            if time.monotonic()-started > seconds:
                notes['reply_checks_complete'] = False
                break
            board.push(move)
            if terminal_draw(board):
                board.pop()
                continue
            for reply in list(board.legal_moves):
                check_cancelled()
                if time.monotonic()-started > seconds:
                    notes['reply_checks_complete'] = False
                    break
                target = board.piece_at(reply.to_square)
                if target is not None and target.piece_type == chess.QUEEN:
                    notes['allows_queen_capture'].setdefault(move.uci(), reply.uci())
                board.push(reply)
                mate = board.is_checkmate()
                board.pop()
                if mate:
                    notes['allows_opponent_mate_in_one'][move.uci()] = reply.uci()
                    break
            board.pop()
    return notes


def terminal_candidates(position, notes=None):
    """A legal subset proved by terminal rules, still selected by the real LLM.

    SDK docs/reasoning.md explicitly permits a legal candidate subset. Remove
    only moves with an actual opponent mate witness; incomplete search never
    certifies other moves safe. If all moves lose immediately, keep them all.
    """
    notes = notes if notes is not None else position_notes(position)
    if notes['mate_in_one']:
        return notes['mate_in_one']
    safe = [m for m in position['legal_moves'] if m not in notes['allows_opponent_mate_in_one']]
    return safe or position['legal_moves']

