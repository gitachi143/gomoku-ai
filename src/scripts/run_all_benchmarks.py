import json
import csv
import itertools
from pathlib import Path

from gomoku.board import Board, BLACK, WHITE
from gomoku.game import Game
from gomoku import rules
from agents.ab_agent import AlphaBetaAgent
from agents.greedy_agent import GreedyAgent
from agents.random_agent import RandomAgent
from agents.rl_agent import RLAgent
from agents.sarsa_agent import SARSAAgent

_ROOT = Path(__file__).resolve().parent.parent.parent


# build all agents with proper weights
def build_agents():
    agents = {}
    agents["alphabeta"] = AlphaBetaAgent()
    agents["greedy"] = GreedyAgent()
    agents["random"] = RandomAgent(seed=42)

    rl_path = _ROOT / "rl_weights.json"
    if rl_path.exists():
        with open(rl_path) as f:
            agents["rl"] = RLAgent(weights=json.load(f), epsilon=0.0, seed=0)

    sarsa_path = _ROOT / "weights_sarsa.json"
    if sarsa_path.exists():
        with open(sarsa_path) as f:
            agents["sarsa"] = SARSAAgent(weights=json.load(f), epsilon=0.0, seed=0)

    return agents


# play one game between two agent instances
def play_one(black_agent, white_agent):
    game = Game(board=Board(), black_agent=black_agent, white_agent=white_agent, to_move=BLACK)
    while not game.is_over():
        agent = game.agent_for_turn()
        move = agent.select_move(game.board, game.to_move)
        game.step(move)
    return game.winner()


# run N games between two agents, swapping sides each game
def run_matchup(agent_a, agent_b, games):
    a_wins = 0
    b_wins = 0
    draws = 0
    for i in range(games):
        # swap sides on odd games
        if i % 2 == 0:
            winner = play_one(agent_a, agent_b)
            if winner == BLACK:
                a_wins += 1
            elif winner == WHITE:
                b_wins += 1
            else:
                draws += 1
        else:
            winner = play_one(agent_b, agent_a)
            if winner == BLACK:
                b_wins += 1
            elif winner == WHITE:
                a_wins += 1
            else:
                draws += 1
    return a_wins, b_wins, draws


def main():
    agents = build_agents()
    names = sorted(agents.keys())
    print(f"Agents loaded: {', '.join(names)}\n")

    # 20 games for matchups involving alphabeta, 100 for the rest
    results = []

    for a_name, b_name in itertools.combinations(names, 2):
        if "alphabeta" in (a_name, b_name):
            n_games = 20
        else:
            n_games = 100

        print(f"{a_name} vs {b_name} ({n_games} games)...", end=" ", flush=True)
        a_wins, b_wins, draws = run_matchup(agents[a_name], agents[b_name], n_games)
        print(f"{a_name}={a_wins}  {b_name}={b_wins}  draws={draws}")

        results.append({
            "agent_a": a_name,
            "agent_b": b_name,
            "games": n_games,
            "a_wins": a_wins,
            "b_wins": b_wins,
            "draws": draws,
        })

    # save to CSV
    csv_path = _ROOT / "benchmark_results.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["agent_a", "agent_b", "games", "a_wins", "b_wins", "draws"])
        writer.writeheader()
        writer.writerows(results)
    print(f"\nResults saved to {csv_path}")

    # print summary table
    print("\n=== RESULTS TABLE ===\n")
    print(f"{'Matchup':<30} {'Games':>6} {'Win A':>7} {'Win B':>7} {'Draws':>7}")
    print("-" * 60)
    for r in results:
        label = f"{r['agent_a']} vs {r['agent_b']}"
        print(f"{label:<30} {r['games']:>6} {r['a_wins']:>7} {r['b_wins']:>7} {r['draws']:>7}")


if __name__ == "__main__":
    main()
