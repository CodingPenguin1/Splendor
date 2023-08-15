import numpy as np
import torch
from torch import nn

from player import Player


# Torch constants
DEVICE = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')


COLORS = ['black', 'blue', 'green', 'red', 'white']


def _tokenize_card(card):
    # Card color 1 hot encoding
    color_arr = 5 * [0]
    color_arr[COLORS.index(card["color"])] = 1

    # Cost
    cost_arr = 5 * [0]
    for color, count in card["cost"].items():
        cost_arr[COLORS.index(color)] = count

    # Tier
    tier_arr = 3 * [0]
    tier_arr[card["tier"] - 1] = 1

    # 5 + 1 + 5 + 3 = 14 elements
    return np.array(color_arr + [card["points"]] + cost_arr + tier_arr, dtype=np.int8)


def _tokenize_noble(noble):
    color_arr = 5 * [0]
    for color, count in noble.items():
        color_arr[COLORS.index(color)] = count

    # 5 elements
    return np.array(color_arr, dtype=np.int8)


def _tokenize_player(player):
    # Score (1 element)
    score = player["score"]

    # Tokens (6 elements)
    tokens = 6 * [0]
    for i, color in enumerate(player["tokens"]):
        tokens[i] = player["tokens"][color]

    # Discounts from purchased cards (5 elements)
    discounts = 5 * [0]
    for card in player["cards"]:
        discounts[COLORS.index(card["color"])] += 1

    # Reserved cards (42 elements)
    reserved = []
    for card in player["reserved"]:
        reserved.extend(_tokenize_card(card))
    # Pad with 0s for missing cards (when player hasn't reserved maximum of 3 cards)
    reserved.extend((42 - len(reserved)) * [0])

    # Nobles (25 elements)
    nobles = []
    for noble in player["nobles"]:
        nobles.extend(_tokenize_noble(noble))
    # Pad with 0s for missing nobles (when player doesn't have all 5 nobles)
    nobles.extend((25 - len(nobles)) * [0])

    # Final array (1 + 6 + 5 + 42 + 25 = 79 elements)
    return {
        "state": np.array([score] + tokens + discounts, dtype=np.int8),
        "reserved": np.array(reserved, dtype=np.int8)
    }


class AI_Player(Player):
    def __init__(self):
        super().__init__()
        self.name = "AI Player"

    def take_turn(self, game_state):
        inputs = self._map_inputs(game_state)
        for key in inputs[0]:
            print(key, inputs[0][key].shape)
        for i, player_arr in enumerate(inputs[1]):
            print(f"Player {i}")
            for key in player_arr:
                print(f"  {key} {player_arr[key].shape}")

    def _map_inputs(self, game_state):
        player_states = game_state["players"]
        my_state = self.get_state()

        # === Board State ===
        # 1. Round number (1 element)
        round_num = game_state["round"]

        # 2. Tokens in bank (6 elements)
        tokens = 6 * [0]
        for i, color in enumerate(game_state["tokens"]):
            tokens[i] = game_state["tokens"][color]

        # 3. Cards on board (12 * 14 = 168 elements)
        cards = []
        for tier in game_state["board"].keys():
            if tier != "nobles":
                for card in game_state["board"][tier]:
                    cards.extend(_tokenize_card(card))

        # 4. Nobles (5 * 5 = 25 elements)
        nobles = []
        for noble in game_state["board"]["nobles"]:
            nobles.extend(_tokenize_noble(noble))

        # Board state (1 + 6 + 168 + 25 = 200 elements)
        board_input = {
            "state": np.array([round_num] + tokens, dtype=np.int8),
            "cards": np.array(cards, dtype=np.int8),
            "nobles": np.array(nobles, dtype=np.int8)
        }

        # === Player State ===
        # Reorder players so that my state is the first one
        while player_states[0] != my_state:
            player_states.append(player_states.pop(0))

        # Player state (79 * 4 = 316 elements)
        player_input = [_tokenize_player(player) for player in game_state["players"]]

        # All inputs (200 + 316 = 516 elements)
        return board_input, player_input


class Model(nn.Module):
    def __init__(self):
        super().__init__()
        # Comment format:
        # # input -> # output (# times duplicated with shared weights)

        # === Board State Networks ===
        # 14 -> 10 (x12)
        self.game_card_nn = nn.Sequential(
            nn.Linear(14, 12),
            nn.ReLU(),
            nn.Linear(12, 12),
            nn.ReLU(),
            nn.Linear(12, 10),
            nn.ReLU(),
        )
        # 5 -> 8 (x5)
        self.game_noble_nn = nn.Sequential(
            nn.Linear(5, 10),
            nn.ReLU(),
            nn.Linear(10, 8),
            nn.ReLU(),
            nn.Linear(8, 8),
            nn.ReLU(),
        )
        # 7 -> 10
        self.game_state_nn = nn.Sequential(
            nn.Linear(7, 15),
            nn.ReLU(),
            nn.Linear(15, 12),
            nn.ReLU(),
            nn.Linear(12, 10),
            nn.ReLU(),
        )

        # === Player State Networks ===
        # 14 -> 10 (x3) (x4 for players)
        self.player_reserved_nn = nn.Sequential(
            nn.Linear(14, 12),
            nn.ReLU(),
            nn.Linear(12, 10),
            nn.ReLU(),
        )
        # 37 -> 20 (x4 for players), input also skips to input of combiner network
        self.player_state_nn = nn.Sequential(
            nn.Linear(37, 30),
            nn.ReLU(),
            nn.Linear(30, 24),
            nn.ReLU(),
            nn.Linear(24, 20),
            nn.ReLU(),
        )

        # === Combiner Network ===
        # (14 * 12) + (5 * 5) + 7 + 4 * ((14 * 3) + 37) = 516 -> 4
        # Outputs are to predict own score in 5 turns, 3 turns, 1 turn, and the probability of winning
        self.combiner_nn = nn.Sequential(
            nn.Linear(516, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 4),
        )

    def forward(self, x):
        board_input, player_input = x
