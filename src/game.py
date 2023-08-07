from deck import Deck
from player import Player


SETUP_COUNTS = {2: (4, 3),  # num_players: (num_tokens, num_nobles)
                3: (5, 4),  # there are always 5 gold tokens
                4: (7, 4)}
COLORS = ['black', 'blue', 'green', 'red', 'white']


class Game:
    def __init__(self, n_players=4):
        self.n_players = n_players
        self.players = [Player() for _ in range(n_players)]
        self.current_player = 0

        self._setup()

    def _setup(self):
        self.round = 0
        self.previous_state = None

        self.tokens = {color: SETUP_COUNTS[self.n_players][0] for color in COLORS}
        self.tokens['gold'] = 5

        # Create decks
        self.t1_deck = Deck(1)
        self.t2_deck = Deck(2)
        self.t3_deck = Deck(3)
        self.noble_deck = Deck('n')

        # Create board
        self.board = {'t1': [self.t1_deck.draw() for _ in range(4)],
                      't2': [self.t2_deck.draw() for _ in range(4)],
                      't3': [self.t3_deck.draw() for _ in range(4)],
                      'nobles': [self.noble_deck.draw() for _ in range(SETUP_COUNTS[self.n_players][1])]}

    def next_player(self):
        self.current_player = (self.current_player + 1) % self.n_players
        return self.get_current_player()

    def get_current_player(self):
        return self.players[self.current_player]

    def get_state(self):
        return {'round': self.round,
                'tokens': self.tokens,
                'board': self.board}

    def process_turn(self):
        game_state = self.get_state()
        print(self)
        action = self.get_current_player().take_turn(game_state)

        # Actions can be 'take', 'buy', or 'reserve'
        if action['type'] == 'take':
            # If action type is 'take', then action must have a 'tokens' key with a list of colors to take
            self._take_tokens(action['tokens'])

        elif action['type'] == 'buy':
            # If action type is 'buy', then action must have a 'card' key with a list of card attributes
            self._buy_card(action['card'])

        elif action['type'] == 'reserve':
            # If action type is 'reserve', then action must have a 'card' key with a list of card attributes
            self._reserve_card(action['card'])

        else:
            raise ValueError('action type must be "take", "buy", or "reserve"')

        # Set next player
        self.next_player()

        # Save previous state
        self.previous_state = game_state

        return self.get_state()

    def _take_tokens(self, tokens):
        print(tokens)
        # Check if the board has enough tokens for the requested tokens to be taken
        if len(tokens) > 3:
            raise ValueError('cannot take more than 3 tokens')

        elif len(tokens) == 3:
            # Validate that all three tokens are of different colors
            if len(set(tokens)) != 3:
                raise ValueError('tokens must be of different colors')
            # and that the board has enough of each color in the bank
            for color in tokens:
                if self.tokens[color] < 1:
                    raise ValueError('not enough tokens on board')
            for color in tokens:
                self.tokens[color] -= 1
                self.get_current_player().tokens[color] += 1

        elif len(tokens) == 2:
            # If 2 tokens are taken, they must be the same color
            if len(set(tokens)) != 1:
                raise ValueError('tokens must be of the same color')
            # and the board must have at least 4 of that color
            if self.tokens[tokens[0]] < 4:
                raise ValueError('not enough tokens on board')
            self.tokens[tokens[0]] -= 2
            self.get_current_player().tokens[tokens[0]] += 2

        else:
            raise ValueError('must take at least 2 tokens')

    def _check_card_tier(self, card):
        if card in self.board['t1']:
            return 1
        elif card in self.board['t2']:
            return 2
        elif card in self.board['t3']:
            return 3
        else:
            raise ValueError('card not on board')

    def check_card_buyable(self, card):
        # Check if player has enough tokens to buy card
        player_buying_power = self.get_current_player().get_buying_power()
        cost = card['cost'].copy()
        # Apply player cards/tokens to cost
        for color in cost:
            cost[color] -= player_buying_power[color]

        # If cost is <= 0, player can buy card without gold tokens
        can_buy = all(v <= 0 for v in cost.values())
        if not can_buy:
            # Check if player has enough gold tokens to buy card
            outstanding_cost = sum(v for v in cost.values() if v > 0)
            can_buy = (
                outstanding_cost <= 0
                or player_buying_power['gold'] >= outstanding_cost
            )

        return can_buy

    def _buy_card(self, card):
        # Get card tier & make sure card is on board
        tier = self._check_card_tier(card)

        # Check that the card is purchasable
        if not self.check_card_buyable(card):
            raise ValueError('card not buyable')

        # Figure out how many tokens to take from the player
        cost = card['cost'].copy()
        # Deduct player cards from cost
        for card in self.get_current_player().cards:
            cost[color] -= 1
        # Take player tokens to cover remaining cost
        for color in cost:
            if cost[color] > 0:
                # Take appropriate amount of tokens from player
                self.get_current_player().tokens[color] -= cost[color]
                self.tokens[color] += cost[color]
                # If player doesn't have enough tokens, take gold tokens
                if self.get_current_player().tokens[color] < 0:
                    self.get_current_player().tokens['gold'] -= abs(self.get_current_player().tokens[color])
                    self.get_current_player().tokens[color] = 0
                    self.tokens['gold'] += abs(self.get_current_player().tokens[color])

        # Remove card from board
        self.board[f't{tier}'].remove(card)

        # Give the card to the player
        self.get_current_player().cards.append(card)

        # Add new card to board
        deck = getattr(self, f't{tier}_deck')
        self.board[f't{tier}'].append(deck.draw())

    def _reserve_card(self, card):
        # Get card tier & make sure card is on board
        tier = self._check_card_tier(card)

        # Make sure the player has less than 3 cards in their hand
        if len(self.get_current_player().reserved_cards) >= 3:
            raise ValueError('cannot reserve more than 3 cards')

        # Remove card from board
        self.board[f't{tier}'].remove(card)

        # Give the card to the player
        self.get_current_player().reserved_cards.append(card)

        # Add new card to board
        deck = getattr(self, f't{tier}_deck')
        self.board[f't{tier}'].append(deck.draw())

    def __repr__(self):
        s = 'Nobles:'
        for noble in self.board['nobles']:
            s += f'\t{noble}'
        s += f'\nT3 ({self.t3_deck.cards_left()}):'
        for card in self.board['t3']:
            s += f'\t{card}'
        s += f'\nT2 ({self.t2_deck.cards_left()}):'
        for card in self.board['t2']:
            s += f'\t{card}'
        s += f'\nT1 ({self.t1_deck.cards_left()}):'
        for card in self.board['t1']:
            s += f'\t{card}'
        s += '\nTokens:'
        for color in self.tokens:
            s += f'\t{color}: {self.tokens[color]}'
        return s


if __name__ == '__main__':
    game = Game()
    game.process_turn()
    # print(game)