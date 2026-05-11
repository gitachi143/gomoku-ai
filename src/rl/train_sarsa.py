import argparse
import csv
import random

from gomoku.board import BLACK, WHITE
from scripts.agent_loader import load_agent
from agents.sarsa_agent import SARSAAgent
from rl.train import play_one_game, assign_rewards, save_weights, load_weights


# train SARSA agent with epsilon decay
# mirrors rl/train.py but uses on-policy SARSA updates
def train_sarsa(
    out_path="weights_sarsa.json",
    episodes=5000,
    board_size=9,
    alpha=0.01,
    gamma=0.99,
    epsilon_start=1.0,
    epsilon_end=0.05,
    seed=0,
    log_interval=500,
    self_play=False,
    csv_log=None,
    opponent_type="random",
    init_weights_path=None,
):
    # load pre-existing weights if provided
    if init_weights_path:
        print(f"Loading weights from {init_weights_path}")
        init_weights = load_weights(init_weights_path)
    else:
        init_weights = {}

    agent = SARSAAgent(
        weights=init_weights,
        alpha=alpha,
        gamma=gamma,
        epsilon=epsilon_start,
        seed=seed,
    )

    # self-play or play against a fixed opponent
    if opponent_type == "self" or self_play:
        opponent = agent
    else:
        opponent = load_agent(opponent_type, seed=seed)

    stats = {"wins": 0, "losses": 0, "draws": 0}
    rng = random.Random(seed)

    # optional CSV logging for training curves
    csv_file = None
    csv_writer = None
    if csv_log:
        csv_file = open(csv_log, "w", newline="")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["episode", "epsilon", "wins", "losses", "draws", "win_rate"])

    for ep in range(1, episodes + 1):
        # linear epsilon decay
        progress = ep / episodes
        agent.epsilon = epsilon_start + (epsilon_end - epsilon_start) * progress

        # alternate sides each episode
        rl_stone = BLACK if ep % 2 == 0 else WHITE

        # play one game and get shaped rewards
        winner, transitions = play_one_game(agent, opponent, board_size, rl_stone)
        rewarded = assign_rewards(transitions, winner, rl_stone)

        # SARSA update loop — pair each transition with the next one
        # to get the actual (s', a') for the on-policy TD target.
        # next_rl_board is the board at the agent's NEXT decision point
        # (after opponent has also moved), not right after the agent's move.
        for i, (board_b, stone, move, reward, next_board, next_stone, done) in enumerate(rewarded):
            if done or i + 1 >= len(rewarded):
                # terminal or last transition — no next action available
                agent.update(board_b, stone, move, reward,
                             next_board, next_stone, done, next_move=None)
            else:
                # look ahead to next RL transition for actual (s', a')
                next_rl_board = rewarded[i + 1][0]
                next_rl_stone = rewarded[i + 1][1]
                next_rl_move = rewarded[i + 1][2]
                agent.update(board_b, stone, move, reward,
                             next_rl_board, next_rl_stone, done,
                             next_move=next_rl_move)

        # track win/loss/draw stats
        if winner == rl_stone:
            stats["wins"] += 1
        elif winner is None:
            stats["draws"] += 1
        else:
            stats["losses"] += 1

        # periodic logging
        if ep % log_interval == 0:
            total = stats["wins"] + stats["losses"] + stats["draws"]
            win_rate = stats["wins"] / total if total > 0 else 0.0
            print(
                f"Episode {ep}/{episodes} | "
                f"epsilon={agent.epsilon:.3f} | "
                f"W:{stats['wins']} L:{stats['losses']} D:{stats['draws']} | "
                f"win_rate={win_rate:.1%}"
            )
            if csv_writer:
                csv_writer.writerow([
                    ep, f"{agent.epsilon:.3f}",
                    stats["wins"], stats["losses"], stats["draws"],
                    f"{win_rate:.4f}",
                ])
            stats = {"wins": 0, "losses": 0, "draws": 0}

    if csv_file:
        csv_file.close()
        print(f"Training log saved to {csv_log}")

    save_weights(out_path, agent.weights)
    print(f"Weights saved to {out_path}")
    return agent.weights


# evaluate trained SARSA agent against a given opponent
def evaluate_vs(weights_path, opponent_type="random", board_size=9, games=100, seed=42):
    from gomoku.board import Board
    from gomoku import rules

    weights = load_weights(weights_path)
    sarsa = SARSAAgent(weights=weights, epsilon=0.0, seed=seed)

    opp = load_agent(opponent_type, seed=seed)
    opp_name = getattr(opp, "name", opponent_type)

    sarsa_wins = 0
    opp_wins = 0
    draws = 0

    for g in range(games):
        board = Board(size=board_size)
        # alternate who plays black/white for fairness
        if g % 2 == 0:
            agents = {BLACK: sarsa, WHITE: opp}
            sarsa_stone = BLACK
        else:
            agents = {BLACK: opp, WHITE: sarsa}
            sarsa_stone = WHITE

        stone = BLACK
        while not rules.is_terminal(board.grid):
            move = agents[stone].select_move(board, stone)
            board.place(move, stone)
            stone = WHITE if stone == BLACK else BLACK

        w = rules.winner(board.grid)
        if w == sarsa_stone:
            sarsa_wins += 1
        elif w is None:
            draws += 1
        else:
            opp_wins += 1

    print(f"SARSA vs {opp_name} ({board_size}x{board_size}, {games} games): "
          f"SARSA wins {sarsa_wins}, {opp_name} wins {opp_wins}, Draws {draws} "
          f"({100*sarsa_wins/games:.1f}% win rate)")
    return sarsa_wins, opp_wins, draws


# CLI: train or evaluate
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train SARSA Gomoku agent")
    parser.add_argument("--episodes", type=int, default=5000)
    parser.add_argument("--board-size", type=int, default=9)
    parser.add_argument("--alpha", type=float, default=0.01)
    parser.add_argument("--gamma", type=float, default=0.99)
    parser.add_argument("--out", default="weights_sarsa.json")
    parser.add_argument("--eval", action="store_true", help="Evaluate after training")
    parser.add_argument("--eval-only", type=str, default=None, help="Skip training, evaluate this weights file")
    parser.add_argument("--csv-log", type=str, default=None, help="Save training stats to CSV")
    parser.add_argument("--opponent", type=str, default="random", help="Opponent agent name")
    parser.add_argument("--init-weights", type=str, default=None, help="Path to initial weights")
    parser.add_argument("--eval-opponents", nargs="+", default=["random", "greedy"],
                        help="Opponent agents to evaluate against")
    args = parser.parse_args()

    if args.eval_only:
        for opp_name in args.eval_opponents:
            evaluate_vs(args.eval_only, opp_name, board_size=args.board_size)
    else:
        train_sarsa(
            out_path=args.out,
            episodes=args.episodes,
            board_size=args.board_size,
            alpha=args.alpha,
            gamma=args.gamma,
            csv_log=args.csv_log,
            opponent_type=args.opponent,
        )
        if args.eval:
            for opp_name in args.eval_opponents:
                evaluate_vs(args.out, opp_name, board_size=args.board_size)
