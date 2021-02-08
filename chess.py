import random
from math import sqrt

from bmiibo import Bmiibo


class BlockedCell:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(BlockedCell, cls).__new__(cls)
        return cls._instance

    def __str__(self):
        return "X"

    def __repr__(self):
        return str(self)


class EmptyCell:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(EmptyCell, cls).__new__(cls)
        return cls._instance

    def __str__(self):
        return "O"

    def __repr__(self):
        return str(self)


class Board(list):

    def __init__(self, size):
        list.__init__(self)
        self.extend([[EmptyCell() for i in range(size)] for j in range(size)])

    def __repr__(self):
        grid = ""
        for i, row in enumerate(self):
            if 0 == i:
                grid += "-" * (2 * len(self) - 1) + "\n"
            grid += "|".join(map(repr, row)) + "\n"
            if (len(self) - 1) == i:
                grid += "-" * (2 * len(self) - 1)
        return grid

    def simplified(self, player):
        flat = []
        for y, row in enumerate(self):
            for x, cell in enumerate(row):
                cell_type = type(cell)
                if issubclass(cell_type, Bmiibo):
                    if cell == player:
                        flat.append(((x, y), "P"))
                    else:
                        flat.append(((x, y), "E", cell.hp))
                else:
                    flat.append(((x, y), str(cell)))
        return tuple(flat)

    def __getitem__(self, item):
        getitem = list.__getitem__
        return getitem(getitem(self, item[1]), item[0])

    def __setitem__(self, item, value):
        if issubclass(type(value), Bmiibo):
            value.pos = item
        setitem = list.__setitem__
        getitem = list.__getitem__
        setitem(getitem(self, item[1]), item[0], value)

    def move(self, start_pos, end_pos):
        if ((0 <= end_pos[0] < len(self)) and (0 <= end_pos[1] < len(self))) \
                and issubclass(type(self[start_pos]), Bmiibo) \
                and type(self[end_pos]) == EmptyCell:
            temp = self[end_pos]
            self[end_pos] = self[start_pos]
            self[start_pos] = temp
            return True
        return False

    def block(self, pos):
        if type(self[pos]) is EmptyCell:
            self[pos] = BlockedCell()

    def unblock(self, pos):
        if type(self[pos]) is BlockedCell:
            self[pos] = EmptyCell()
            return True
        return False

    def get_area(self, radius, center):
        points = []
        for i in range(-radius, radius + 1):
            inner = radius - abs(i)
            for j in range(-inner, abs(inner) + 1):
                x = center[0] + i
                y = center[1] + j
                if (0 <= x < len(self)) and (0 <= y < len(self)):
                    points.append((x, y))
                else:
                    continue
        return [self[p] for p in points]

    def distance(self, start_pos, end_pos):
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        return sqrt((dx ** 2) + (dy ** 2))

    def direction(self, start_pos, end_pos):
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        distance = 1 if (dist := self.distance(start_pos, end_pos)) == 0 else dist
        return round(dx / distance), round(dy / distance)


class Game:

    def __init__(self, size=8, **players):
        self.board = Board(size)
        self.players = []
        self.dead = []
        for player in players.items():
            self.players.append(new_player := Bmiibo(player[0]))
            self.board[player[1]] = new_player

    def turn(self, reporting):
        for p in self.players:
            if p.is_alive():
                p.update(self.board)
                if reporting:
                    print(p)
                    print(self.board)
                    print(p.brain.memory[-1][0][2])
                    print("*" * 100)
            else:
                self.players.remove(p)
                self.dead.append(p)
                self.board[p.pos] = EmptyCell()

    def play(self, training=True, reporting=False):
        random.shuffle(self.players)
        while len(self.players) > 1:
            self.turn(reporting)
            if training:
                self.score()
                self.train()
        winner = self.players[0]
        if reporting:
            print(f"{winner.name} won!")
            print("=" * 100)
        return winner

    def score(self):
        for p in self.players:
            points = 0 if p.is_alive else -1000
            for e in self.players:
                if p != e:
                    points += p.hp - e.hp
            points += len(self.dead) * 200
            if len(p.brain.memory) > 1 and p.brain.memory[-2][1] == points:
                points = -((len(self.players) - 1) * 100)
            p.score = points

    def train(self):
        for player in self.players:
            player.learn()
