import json
import pickle
import random
from functools import partial
from operator import itemgetter
from os.path import exists


def is_horizontal(pos1, pos2):
    return pos1[1] == pos2[1]


def is_vertical(pos1, pos2):
    return pos1[0] == pos2[0]


def is_adjacent(pos1, pos2):
    dx = pos1[0] - pos2[0]
    dy = pos1[1] - pos2[1]
    return abs(dx) in [0, 1] and abs(dy) in [0, 1]


def melee(board, player, action, target):
    if is_adjacent(target, player.pos) and issubclass(type(enemy := board[target]), Bmiibo):
        enemy.damage(action.amount, action.element)


def heal(board, player, action, target):
    if action.is_self_targeting():
        player.heal(action.amount)
    elif issubclass(type(enemy := board[target]), Bmiibo):
        enemy.heal(action.amount)


def explosion(board, player, action, target):
    if action.radius + 1 < board.distance(player.pos, target):
        blast_area = board.get_area(action.radius, target)
        for enemy in blast_area:
            if issubclass(type(enemy), Bmiibo) and enemy != player:
                enemy.damage(action.amount, action.element)
                direction = board.direction(target, enemy.pos)
                destination = (enemy.pos[0] + direction[0] * action.force, enemy.pos[1] + direction[1] * action.force)
                board.move(enemy.pos, destination)


def blockade(board, player, action, target):
    if is_adjacent(player.pos, target):
        if "blockedCell" in action.__dict__:
            board.unblock(action.blockedCell)
        board.block(target)
        action.__dict__["blockedCell"] = target


def ranged(board, player, action, target):
    if not is_adjacent(player.pos, target) and issubclass(type(enemy := board[target]), Bmiibo):
        enemy.damage(action.amount, action.element)


def whirl(board, player, action, target):
    top_left = (player.pos[0] - 1, player.pos[1] - 1)
    whirl_area = generate_pos(3)
    whirl_area.remove((1, 1))
    for pos in whirl_area:
        transformed_pos = (pos[0] + top_left[0], pos[1] + top_left[1])
        melee(board, player, action, transformed_pos)
        direction = board.direction(player.pos, transformed_pos)
        destination = (transformed_pos[0] + direction[0] * action.force,
                       transformed_pos[1] + direction[1] * action.force)
        board.move(transformed_pos, destination)


def piercing(board, player, action, target):
    if is_horizontal(player.pos, target):
        if player.pos[0] > target[0]:
            for x in range(player.pos[0]):
                line_target = (x, player.pos[1])
                if issubclass(type(enemy := board[line_target]), Bmiibo):
                    enemy.damage(action.damage, action.element)
        else:
            for x in range(player.pos[0]+1, len(board)):
                line_target = (x, player.pos[1])
                if issubclass(type(enemy := board[line_target]), Bmiibo):
                    enemy.damage(action.damage, action.element)
    elif is_vertical(player.pos, target):
        if player.pos[1] > target[1]:
            for y in range(player.pos[1]):
                line_target = (player.pos[0], y)
                if issubclass(type(enemy := board[line_target]), Bmiibo):
                    enemy.damage(action.damage, action.element)
        else:
            for y in range(player.pos[1]+1, len(board)):
                line_target = (player.pos[0], y)
                if issubclass(type(enemy := board[line_target]), Bmiibo):
                    enemy.damage(action.damage, action.element)


def charge(board, player, action, target):
    for _ in range(action.distance):
        direction = board.direction(player.pos, target)
        destination = (player.pos[0] + direction[0], player.pos[1] + direction[1])
        board.move(player.pos, destination)
    melee(board, player, action, target)
    player.damage(action.recoil, action.element)


def weakness(board, player, action, target):
    if action.is_self_targeting():
        if bool(action.remove):
            player.remove_weakness(action.element)
        else:
            player.add_weakness(action.element)
    elif issubclass(type(enemy := board[target]), Bmiibo):
        if bool(action.remove):
            enemy.remove_weakness(action.element)
        else:
            enemy.add_weakness(action.element)


actionTypes = {
    "melee": melee,
    "heal": heal,
    "explosion": explosion,
    "blockade": blockade,
    "ranged": ranged,
    "whirl": whirl,
    "piercing": piercing,
    "charge": charge,
    "weakness": weakness
}

melee_actions = ["melee", "blockade", "whirl"]


def generate_actions(simplified_board, player):
    for cell in simplified_board:
        if "E" == cell[1] and (player.attack.is_ranged() or is_adjacent(player.pos, cell[0])) and player.attack.ready():
            yield [.0, ("attack", cell[0]), f"attack {cell[0]}"]
        elif "O" == cell[1] and is_adjacent(player.pos, cell[0]):
            yield [.0, ("move", player.pos, cell[0]), f"move to {cell[0]}"]
        if player.ability.ready():
            if player.ability.is_self_targeting():
                pass
            elif player.ability.is_ranged() or is_adjacent(player.pos, cell[0]):
                yield [.0, ("ability", cell[0]), f"ability {cell[0]}"]
        if player.ultimate.ready():
            if player.ultimate.is_self_targeting():
                pass
            elif player.ultimate.is_ranged() or is_adjacent(player.pos, cell[0]):
                yield [.0, ("ultimate", cell[0]), f"ultimate {cell[0]}"]
    if player.ability.ready():
        if player.ability.is_self_targeting():
            yield [.0, ("ability", None), "ability self"]
    if player.ultimate.ready():
        if player.ultimate.is_self_targeting():
            yield [.0, ("ultimate", None), "ultimate self"]


def best(array, key=(lambda x: x)):
    array = sorted(array, key=key, reverse=True)
    best_value = key(array[0])
    results = []
    for item in array:
        if key(item) != best_value:
            break
        results.append(item)
    return results


def desc_to_func(desc):
    if "move" == desc[0]:
        return partial(lambda player, board, start_pos, end_pos: board.move(start_pos, end_pos), start_pos=desc[1],
                       end_pos=desc[2])
    elif "attack" == desc[0]:
        return partial(lambda player, board, target: player.attack.process(player, board, target), target=desc[1])
    elif "ability" == desc[0]:
        return partial(lambda player, board, target: player.ability.process(player, board, target), target=desc[1])
    elif "ultimate" == desc[0]:
        return partial(lambda player, board, target: player.ultimate.process(player, board, target), target=desc[1])


class Brain:
    learning_rate = 0.2
    discount = 0.8

    def __getitem__(self, item):
        try:
            value = self.frames[item]
        except KeyError:
            value = [action for action in generate_actions(item[5], self.player)]
            self.frames[item] = value
        decision = random.choice(best(value, key=itemgetter(0)))
        self.memory.append([decision, 0])
        return desc_to_func(decision[1])

    def __setitem__(self, key, value):
        self.frames[key] = value

    def __init__(self, player, frames=None):
        self.player = player
        self.frames = frames if frames else {}
        self.memory = []

    @staticmethod
    def load(player):
        if exists(f"bmiibos/{player.name}_brain"):
            with open(f"bmiibos/{player.name}_brain", "rb") as file:
                frames = pickle.load(file)
                return Brain(player, frames=frames)
        else:
            return Brain(player)

    def save(self):
        with open(f"bmiibos/{self.player.name}_brain", "wb") as file:
            pickle.dump(self.frames, file)

    def learn(self):
        previous = 0
        for mem in reversed(self.memory):
            previous = Brain.q(mem[0][0], self.learning_rate, mem[1], self.discount, previous)
            mem[0][0] = previous

    @staticmethod
    def q(old_value, learning_rate, reward, discount, future_value):
        old_value = float(old_value)
        reward = float(reward)
        future_value = float(future_value)
        return old_value + (learning_rate * (reward + (discount * future_value) - old_value))


def generate_pos(size, prev=None, lst=None):
    if not prev:
        return generate_pos(size, prev=(0, 0), lst={(0, 0)})
    if (next_x := prev[0] + 1) < size and not (next_x, prev[1]) in lst:
        lst.add((next_x, prev[1]))
        generate_pos(size, prev=(next_x, prev[1]), lst=lst)
    if (next_y := prev[1] + 1) < size and not (prev[0], next_y) in lst:
        lst.add((prev[0], next_y))
        generate_pos(size, prev=(prev[0], next_y), lst=lst)
    return lst


def normalize_strings(element):
    if type(element[1]) is str:
        return element[0], element[1].lower()
    return element


class Action:
    cooldown = 1
    actionType = ""

    @classmethod
    def from_json(cls, filename):
        with open(f"bmiibos/{filename}.json", "rb") as file:
            action_data = json.load(file)
            if type(action_data) is list:
                return ActionGroup([cls(**(dict(map(normalize_strings, d.items())))) for d in action_data])
            return cls(**(dict(map(normalize_strings, action_data.items()))))

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.current_cooldown = 0

    def tick(self):
        if self.current_cooldown != self.cooldown:
            self.current_cooldown += 1

    def ready(self):
        return self.current_cooldown == self.cooldown

    def until(self):
        return self.cooldown - self.current_cooldown

    def is_ranged(self):
        return self.actionType not in melee_actions

    def is_self_targeting(self):
        try:
            return bool(self.selfTargeting)
        except AttributeError:
            return False

    def process(self, player, board, target):
        if self.ready():
            actionTypes[self.actionType](board, player, self, target)
            self.current_cooldown = 0


class ActionGroup(Action):
    def __init__(self, actions):
        Action.__init__(self)
        self.actions = actions
        self.cooldown = self.actions[0].cooldown

    def is_ranged(self):
        for action in self.actions:
            if action.is_ranged():
                return True
        return False

    def is_self_targeting(self):
        result = True
        for action in self.actions:
            result = result and action.is_self_targeting()
        return result

    def process(self, player, board, target):
        if self.ready():
            for action in self.actions:
                actionTypes[action.actionType](board, player, action, target)
            self.current_cooldown = 0


class Bmiibo:

    def __init__(self, name):
        self.name = name
        self.brain = Brain.load(self)
        self.attack = Action.from_json(f"{name}_attack")
        self.ability = Action.from_json(f"{name}_ability")
        self.ultimate = Action.from_json(f"{name}_ultimate")
        self.hp = 100
        self.weaknesses = []
        self.pos = ()
        self.score = 0

    def is_alive(self):
        return self.hp > 0

    def update(self, board):
        self.attack.tick()
        self.ability.tick()
        self.ultimate.tick()
        self.brain[(
            self.hp,
            self.pos,
            self.attack.until(),
            self.ability.until(),
            self.ultimate.until(),
            board.simplified(self)
        )](self, board)

    def damage(self, amount, element):
        multiplier = 2 if element.lower().strip() in self.weaknesses else 1
        self.hp -= amount * multiplier

    def heal(self, amount):
        if 100 < (self.hp + amount):
            self.hp = 100
        else:
            self.hp += amount

    def add_weakness(self, element):
        element = element.lower().strip()
        if element not in self.weaknesses:
            self.weaknesses.append(element)

    def remove_weakness(self, element):
        element = element.lower().strip()
        if element in self.weaknesses:
            self.weaknesses.remove(element)

    def learn(self):
        self.brain.memory[-1][1] = self.score
        self.brain.learn()

    def __repr__(self):
        return f"{self.name[0].upper()}"

    def __str__(self):
        return f"{self.name} (hp: {self.hp}, pos: {self.pos}, " \
               f"attack: {self.attack.current_cooldown}/{self.attack.cooldown}, " \
               f"ability: {self.ability.current_cooldown}/{self.ability.cooldown}, " \
               f"ultimate: {self.ultimate.current_cooldown}/{self.ultimate.cooldown})"
