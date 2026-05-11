# tests/test_sarsa_smoke.py
import os
import tempfile

from gomoku.board import Board, BLACK
from agents.sarsa_agent import SARSAAgent
from rl.train_sarsa import train_sarsa


def test_sarsa_agent_import_and_legal_move():
    #agent returns a valid move on an empty board
    b = Board()
    a = SARSAAgent(weights={"my_stones": 1.0}, epsilon=0.0, seed=0)
    m = a.select_move(b, BLACK)
    assert b.in_bounds(m)
    assert b.is_empty(m)


def test_sarsa_agent_discoverable():
    from scripts.agent_loader import available_agents
    agents = available_agents()
    assert "sarsa" in agents


def test_sarsa_train_writes_weights_file():
    # run 1 episode of training and verify weights are saved
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "w.json")
        train_sarsa(out_path=path, episodes=1, seed=0, log_interval=1)
        assert os.path.exists(path)

        from rl.train import load_weights
        w = load_weights(path)
        assert isinstance(w, dict)
