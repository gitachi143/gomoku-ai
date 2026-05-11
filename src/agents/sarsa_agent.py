from agents.rl_agent import RLAgent
from heuristics.features import featurize_after_move


# On-policy SARSA agent — inherits everything from RLAgent (Q-learning)
# except the update rule. Q-learning uses max Q(s', a'); SARSA uses
# Q(s', a') for the actual next action a'.
class SARSAAgent(RLAgent):
    name = "sarsa"

    def update(self, board, stone, move, reward, next_board, next_stone, done,
               next_move=None):
        # extract features for current (state, action)
        feats = featurize_after_move(board, stone, move)

        # compute current Q(s, a) = sum of weights * features
        current_q = 0.0
        for k, v in feats.items():
            current_q += float(self.weights.get(k, 0.0)) * float(v)

        # TD target: the key difference from Q-learning
        if done:
            # terminal state — no future reward
            target = reward
        elif next_move is None:
            # fallback to max Q if next action unknown (last non-terminal transition)
            target = reward + self.gamma * self.best_q(next_board, next_stone)
        else:
            # SARSA: use Q for the actual next action, not max
            target = reward + self.gamma * self.q_value(next_board, next_stone, next_move)

        # clip TD error to stabilize learning
        error = target - current_q
        error = max(-10.0, min(10.0, error))

        # linear weight update: w += alpha * error * feature
        for k, v in feats.items():
            fv = float(v)
            if fv == 0.0:
                continue
            old_w = float(self.weights.get(k, 0.0))
            self.weights[k] = old_w + self.alpha * error * fv
