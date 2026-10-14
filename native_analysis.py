"""Development wrapper for original native analysis, never a final move selector."""

import json
import subprocess
import time
from pathlib import Path

import chess

from chess_tools import board_from_position

BINARY = Path(__file__).with_name("native") / "analysis"


def analyze(position, check_cancelled=lambda: None, seconds=0.8, max_depth=6, root_pruning=True):
    board = board_from_position(position, check_cancelled)
    root = board.root()
    args = [
        str(BINARY),
        str(seconds),
        str(max_depth),
        root.fen(),
        ",".join(move.uci() for move in board.move_stack),
        board.fen(),
        ",".join(position["legal_moves"]),
        str(int(root_pruning)),
    ]
    started = time.monotonic()
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        while True:
            check_cancelled()
            if time.monotonic() - started > seconds + 0.5:
                raise TimeoutError("native analysis exceeded its wall budget")
            try:
                output, errors = process.communicate(timeout=0.01)
                break
            except subprocess.TimeoutExpired:
                pass
        if process.returncode:
            raise RuntimeError("native analysis failed: " + errors[:200])
        report = json.loads(output)
        if set(report["legal_moves"]) != {move.uci() for move in board.legal_moves}:
            raise RuntimeError("native and official chess-rules libraries disagree on legality")
        if set(row["uci"] for row in report["scores"]) != set(position["legal_moves"]):
            raise RuntimeError("native analysis did not retain all supplied root choices")
        for row in report["scores"]:
            row["san"] = board.san(chess.Move.from_uci(row["uci"]))
        report["wall_seconds"] = time.monotonic() - started
        report["method"] = (
            "original native minimax/capture search and handcrafted evaluation; attributed general rules library"
        )
        return report
    except BaseException:
        if process.poll() is None:
            process.kill()
        process.communicate()
        raise
