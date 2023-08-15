import random


COLORS = ['black', 'blue', 'green', 'red', 'white']


class Player:
    def __init__(self):
        self._setup()

    def _setup(self):
        self.tokens = {color: 0 for color in COLORS}
        self.tokens['gold'] = 0
        self.cards = []
        self.reserved_cards = []
        self.nobles = []
        self.score = 0

    def get_state(self):
        return {'tokens': self.tokens,
                'cards': self.cards,
                'nobles': self.nobles,
                'reserved': self.reserved_cards,
                'score': self.score}

    def take_turn(self, game_state):
        # # Take a random set of tokens
        # num_tokens = random.randint(2, 3)
        # if num_tokens == 2:
        #     # Pick 1 random color
        #     color = random.sample(COLORS, 1)[0]
        #     tokens = [color, color]
        # else:
        #     tokens = random.sample(COLORS, 3)
        # return {'type': 'take', 'tokens': tokens}

        # Buy a random card
        for color in COLORS:
            self.tokens[color] += 2
        self.tokens['gold'] += 1
        return {'type': 'buy', 'card': random.sample(game_state['board']['t1'], 1)[0]}

    def get_buying_power(self):
        buying_power = {color: self.tokens[color] for color in self.tokens}
        for card in self.cards:
            buying_power[card[0]] += 1
        return buying_power
