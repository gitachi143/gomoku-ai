from __future__ import annotations

import json
import sys
from pathlib import Path

# resolve engine package root (sibling of web/)
_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from flask import Flask, jsonify, render_template, request

from agents.ab_agent import AlphaBetaAgent
from agents.greedy_agent import GreedyAgent
from agents.random_agent import RandomAgent
from agents.rl_agent import RLAgent
from agents.sarsa_agent import SARSAAgent
from gomoku.board import BLACK, BOARD_SIZE, EMPTY, WHITE, Board
from gomoku.game import Game

app = Flask(__name__, template_folder="templates", static_folder="static")


# build agent registry once at startup
def _build_agents():
    registry = {}
    registry["alphabeta"] = AlphaBetaAgent()
    registry["greedy"] = GreedyAgent()
    registry["random"] = RandomAgent(seed=42)

    # load RL weights if available
    rl_path = _ROOT / "rl_weights.json"
    if rl_path.exists():
        with open(rl_path, "r") as f:
            rl_w = json.load(f)
        registry["rl"] = RLAgent(weights=rl_w, epsilon=0.0, seed=0)

    # load SARSA weights if available
    sarsa_path = _ROOT / "weights_sarsa.json"
    if sarsa_path.exists():
        with open(sarsa_path, "r") as f:
            sarsa_w = json.load(f)
        registry["sarsa"] = SARSAAgent(weights=sarsa_w, epsilon=0.0, seed=0)

    return registry


_agents = _build_agents()


def _get_agent(name):
    agent = _agents.get(name)
    if agent is None:
        raise ValueError(f"Unknown agent: {name!r}. Available: {', '.join(sorted(_agents.keys()))}")
    return agent


def _normalize_cell(v):
    if v is None or v == "":
        return EMPTY
    if v == BLACK or v == WHITE:
        return v
    if isinstance(v, str) and len(v) == 1 and v.strip() == "":
        return EMPTY
    return v


def board_from_grid(grid) -> Board:
    if not grid or len(grid) != BOARD_SIZE:
        raise ValueError(f"grid must be {BOARD_SIZE}x{BOARD_SIZE}")
    b = Board(BOARD_SIZE)
    for r in range(BOARD_SIZE):
        row = grid[r]
        if not row or len(row) != BOARD_SIZE:
            raise ValueError(f"grid must be {BOARD_SIZE}x{BOARD_SIZE}")
        for c in range(BOARD_SIZE):
            stone = _normalize_cell(row[c])
            if stone not in (EMPTY, BLACK, WHITE):
                raise ValueError("invalid cell value")
            b._grid[r][c] = stone
    return b


def infer_to_move(board: Board) -> str:
    black_n = sum(row.count(BLACK) for row in board._grid)
    white_n = sum(row.count(WHITE) for row in board._grid)
    if black_n == white_n:
        return BLACK
    if black_n == white_n + 1:
        return WHITE
    raise ValueError("illegal stone counts for Gomoku")


def grid_from_board(board: Board):
    return [list(row) for row in board.grid]


# create a Game with the right agents depending on mode
def make_game(board, to_move, mode="human_vs_ai", human_side="black",
              agent_name="alphabeta", black_agent_name=None, white_agent_name=None):
    if mode == "ai_vs_ai":
        ba = _get_agent(black_agent_name or "alphabeta")
        wa = _get_agent(white_agent_name or "alphabeta")
        return Game(board, black_agent=ba, white_agent=wa, to_move=to_move)
    else:
        ai = _get_agent(agent_name or "alphabeta")
        human_side = (human_side or "black").lower()
        if human_side == "black":
            return Game(board, black_agent=None, white_agent=ai, to_move=to_move)
        elif human_side == "white":
            return Game(board, black_agent=ai, white_agent=None, to_move=to_move)
        else:
            raise ValueError("human_side must be 'black' or 'white'")


def state_payload(game: Game):
    w = game.winner()
    over = game.is_over()
    return {
        "grid": grid_from_board(game.board),
        "to_move": game.to_move,
        "winner": w,
        "game_over": over,
        "is_draw": over and w is None,
    }


@app.route("/")
def index():
    return render_template("index.html")


# return list of available agents for frontend dropdowns
@app.get("/api/agents")
def api_agents():
    return jsonify({"agents": sorted(_agents.keys())})


@app.get("/api/new")
def api_new():
    side = (request.args.get("side") or "black").lower()
    mode = (request.args.get("mode") or "human_vs_ai").lower()
    agent_name = request.args.get("agent") or "alphabeta"
    black_agent_name = request.args.get("black_agent") or "alphabeta"
    white_agent_name = request.args.get("white_agent") or "alphabeta"

    try:
        board = Board(BOARD_SIZE)
        game = make_game(board, BLACK, mode=mode, human_side=side,
                         agent_name=agent_name,
                         black_agent_name=black_agent_name,
                         white_agent_name=white_agent_name)

        # if human plays white, AI opens; if ai-vs-ai, black agent opens
        if (mode == "human_vs_ai" and side == "white") or mode == "ai_vs_ai":
            if not game.maybe_ai_move():
                return jsonify({"error": "failed to apply AI opening move"}), 500

        return jsonify(state_payload(game))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# human makes a move, AI responds
@app.post("/api/move")
def api_move():
    data = request.get_json(silent=True) or {}
    grid = data.get("grid")
    human_side = (data.get("human_side") or "black").lower()
    move = data.get("move")
    client_to_move = data.get("to_move")
    agent_name = data.get("agent") or "alphabeta"

    if not isinstance(move, (list, tuple)) or len(move) != 2:
        return jsonify({"error": "move must be [row, col]"}), 400

    try:
        r, c = int(move[0]), int(move[1])
    except (TypeError, ValueError):
        return jsonify({"error": "move must be integers"}), 400

    try:
        board = board_from_grid(grid)
        inferred = infer_to_move(board)
        if client_to_move is not None and client_to_move != inferred:
            return jsonify({"error": "to_move does not match board state"}), 400
        to_move = inferred
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    human_stone = BLACK if human_side == "black" else WHITE
    if human_side not in ("black", "white"):
        return jsonify({"error": "human_side must be 'black' or 'white'"}), 400

    if to_move != human_stone:
        return jsonify({"error": "not human's turn"}), 400

    game = make_game(board, to_move, mode="human_vs_ai",
                     human_side=human_side, agent_name=agent_name)

    if game.is_over():
        return jsonify({"error": "game is already over"}), 400

    if not board.in_bounds((r, c)) or not board.is_empty((r, c)):
        return jsonify({"error": "illegal move"}), 400

    if not game.step((r, c)):
        return jsonify({"error": "failed to apply move"}), 400

    if not game.is_over():
        if not game.maybe_ai_move():
            return jsonify({"error": "AI failed to move"}), 500

    return jsonify(state_payload(game))


# ai-vs-ai: make one move for the current player's agent
@app.post("/api/ai_move")
def api_ai_move():
    data = request.get_json(silent=True) or {}
    grid = data.get("grid")
    black_agent_name = data.get("black_agent") or "alphabeta"
    white_agent_name = data.get("white_agent") or "alphabeta"

    try:
        board = board_from_grid(grid)
        to_move = infer_to_move(board)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    game = make_game(board, to_move, mode="ai_vs_ai",
                     black_agent_name=black_agent_name,
                     white_agent_name=white_agent_name)

    if game.is_over():
        return jsonify({"error": "game is already over"}), 400

    if not game.maybe_ai_move():
        return jsonify({"error": "AI failed to move"}), 500

    return jsonify(state_payload(game))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
