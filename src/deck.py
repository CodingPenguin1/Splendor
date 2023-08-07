import pandas as pd
import random


COLORS = ['black', 'blue', 'green', 'red', 'white']


class Deck:
    def __init__(self, tier):
        self.tier = tier
        self.cards = []

        if type(tier) == int:
            self._create_tier_deck(tier)
        elif type(tier) == str:
            if tier.lower().startswith('n'):
                self._create_noble_deck()
        else:
            raise ValueError('tier must be an integer or a string')

    def _create_noble_deck(self):
        df = pd.read_csv('noble_data.csv')
        for _, row in df.iterrows():
            cost = {color: row[f'cost_{color}'] for color in COLORS}
            self.cards.append(cost)
        self.shuffle()

    def _create_tier_deck(self, tier):
        df = pd.read_csv('card_data.csv')
        df = df[df['tier'] == int(tier)]
        for _, row in df.iterrows():
            color = row['color']
            points = row['points']
            cost = {color: row[f'cost_{color}'] for color in COLORS}
            self.cards.append({'color': color, 'points': points, 'cost': cost})
        self.shuffle()

    def reset(self):
        self.__init__(self.tier)

    def shuffle(self):
        random.shuffle(self.cards)

    def cards_left(self):
        return len(self.cards)

    def draw(self):
        if self.cards_left() > 0:
            return self.cards.pop()