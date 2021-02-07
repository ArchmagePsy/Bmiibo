import unittest

from bmiibo import Bmiibo, Brain, normalize_strings, Action, ActionGroup, generate_actions, is_adjacent
from chess import Board, EmptyCell, BlockedCell


class MockBrain(Brain):
    def __init__(self, player, brain_data):
        Brain.__init__(self, player)
        for k, v in brain_data.items():
            self[k] = v


class MockBmiibo(Bmiibo):
    def __init__(self, name, brain_data, attack, ability, ultimate):
        self.name = name
        self.brain = MockBrain(self, brain_data)
        self.attack = ActionGroup([Action(**(dict(map(normalize_strings, d.items())))) for d in attack]) \
            if type(attack) is list else Action(**(dict(map(normalize_strings, attack.items()))))
        self.ability = ActionGroup([Action(**(dict(map(normalize_strings, d.items())))) for d in ability]) \
            if type(ability) is list else Action(**(dict(map(normalize_strings, ability.items()))))
        self.ultimate = ActionGroup([Action(**(dict(map(normalize_strings, d.items())))) for d in ultimate]) \
            if type(ultimate) is list else Action(**(dict(map(normalize_strings, ultimate.items()))))
        self.hp = 100
        self.weaknesses = []
        self.pos = ()
        self.score = 0


class BoardTestCase(unittest.TestCase):
    def setUp(self):
        self.board = Board(8)

    def test_board_size(self):
        self.assertEqual(len(self.board), 8)
        self.assertEqual(len(list.__getitem__(self.board, 0)), 8)

    def test_board_get(self):
        self.assertEqual(self.board[(0, 0)], EmptyCell())

    def test_board_block(self):
        self.board.block((0, 0))
        self.assertEqual(self.board[(0, 0)], BlockedCell())
        self.assertFalse(self.board.unblock((0, 1)))
        self.assertTrue(self.board.unblock((0, 0)))
        self.assertEqual(self.board[(0, 0)], EmptyCell())

    def test_get_area(self):
        full_test_area = self.board.get_area(3, (4, 4))
        partial_test_area = self.board.get_area(3, (0, 0))
        self.assertEqual(len(full_test_area), 25)
        self.assertEqual(len(partial_test_area), 10)

    def test_distance(self):
        self.assertEqual(self.board.distance((1, 0), (7, 0)), 6)

    def test_direction(self):
        tests = [
            (((4, 4), (4, 3)), (0, -1)),
            (((4, 4), (6, 2)), (1, -1)),
            (((4, 4), (6, 4)), (1, 0)),
            (((4, 4), (5, 5)), (1, 1)),
            (((4, 4), (4, 5)), (0, 1)),
            (((4, 4), (3, 5)), (-1, 1)),
            (((4, 4), (3, 4)), (-1, 0)),
            (((4, 4), (3, 3)), (-1, -1))
        ]
        for test_pos, result in tests:
            pos1, pos2 = test_pos
            self.assertEqual(self.board.direction(pos1, pos2), result)


class GameTestCase(unittest.TestCase):
    pass


class BmiiboTestCase(unittest.TestCase):
    def setUp(self):
        self.player = MockBmiibo("player", {
            (100, (0, 0), 1, 1, 1, (((0, 0), "P"), ((1, 0), "O"), ((0, 1), "O"), ((1, 1), "E", 100))):
                [[.0, ("move", (0, 0), (0, 1))]],
            (100, (0, 1), 0, 0, 0, (((0, 0), "O"), ((1, 0), "O"), ((0, 1), "P"), ((1, 1), "E", 100))):
                [[1.0, ("attack", (1, 1))], [.0, ("move", (0, 1), (1, 0))]],
            (100, (0, 1), 1, 0, 0, (((0, 0), "O"), ((1, 0), "O"), ((0, 1), "P"), ((1, 1), "E", 90))):
                [[.0, ("ability", (1, 1))]],
            (100, (0, 1), 0, 1, 0, (((0, 0), "O"), ((1, 0), "O"), ((0, 1), "P"), ((1, 1), "E", 100))):
                [[.0, ("ultimate", (1, 1))]]
        }, {
             "actionType": "melee",
             "amount": 10,
             "element": "normal",
             "cooldown": 2
         }, [
             {
                 "actionType": "melee",
                 "amount": 20,
                 "element": "normal",
                 "cooldown": 2
             },
             {
                 "actionType": "heal",
                 "amount": 40,
                 "selfTargeting": 0,
             }
         ], {
             "actionType": "melee",
             "amount": 50,
             "element": "fire",
             "cooldown": 2
         })

        self.enemy = MockBmiibo("enemy", {}, {}, {}, {})

        self.board = Board(2)

        self.board[(0, 0)] = self.player
        self.board[(1, 1)] = self.enemy

    def test_update_move_damage_heal(self):
        self.player.update(self.board)
        self.assertEqual(self.player.pos, (0, 1))
        self.player.update(self.board)
        self.assertEqual(self.player.pos, (0, 1))
        self.assertEqual(self.enemy.hp, 90)
        self.player.update(self.board)
        self.assertEqual(self.enemy.hp, 100)
        self.player.update(self.board)
        self.assertEqual(self.enemy.hp, 50)

    def test_weakness_is_alive(self):
        self.enemy.add_weakness("fIrE")
        self.assertEqual(self.enemy.weaknesses[0], "fire")
        for _ in range(4):
            self.player.update(self.board)
        self.assertFalse(self.enemy.is_alive())
        self.enemy.remove_weakness("fire")
        self.assertEqual(self.enemy.weaknesses, [])


class MiscTestCase(unittest.TestCase):
    def test_is_adjacent(self):
        self.assertTrue(is_adjacent((0, 0), (0, 1)))
        self.assertFalse(is_adjacent((0, 0), (0, 2)))

    def test_normalize_strings(self):
        self.assertEqual(dict(map(normalize_strings, {
            "test_1": "sTrInG",
            "test_2": "normal",
            "test_3": 6
        }.items())), {
            "test_1": "string",
            "test_2": "normal",
            "test_3": 6
        })


class ActionTestCase(unittest.TestCase):
    def setUp(self):
        self.board = Board(8)
        self.player = MockBmiibo("player", {},
                                 {
                                     "actionType": "melee",
                                     "amount": 10,
                                     "element": "normal",
                                     "cooldown": 1
                                 }, {
                                     "actionType": "heal",
                                     "selfTargeting": 1,
                                     "amount": 10,
                                     "cooldown": 1
                                 }, {
                                     "actionType": "explosion",
                                     "amount": 50,
                                     "force": 1,
                                     "element": "fire",
                                     "radius": 2,
                                     "cooldown": 1
                                 })
        self.enemy = MockBmiibo("enemy", {}, {}, {}, {})
        self.action = Action(actionType="explosion", force=1, amount=50, cooldown=1, element="normal", radius=2)
        self.actionGroup = ActionGroup([Action(actionType="heal", amount=50, selfTargeting=1, cooldown=1)])

        self.board[(4, 4)] = self.player
        self.board[(4, 3)] = self.enemy

    def test_is_self_targeting(self):
        self.assertTrue(self.actionGroup.is_self_targeting())

    def test_is_ranged(self):
        self.assertTrue(self.action.is_ranged())

    def test_explosion(self):
        self.action.tick()
        self.action.process(self.enemy, self.board, (4, 5))
        self.assertEqual(self.player.pos, (4, 4))
        self.action.tick()
        self.action.process(self.enemy, self.board, (5, 4))
        self.assertEqual(self.player.pos, (3, 4))
        self.assertEqual(self.enemy.pos, (4, 3))

    def test_over_self_heal(self):
        self.actionGroup.tick()
        self.actionGroup.process(self.player, self.board, None)
        self.assertEqual(self.player.hp, 100)

    def test_generate_actions(self):
        self.assertEqual(len(list(generate_actions(self.board.simplified(self.player), self.player))), 7)
        self.player.ability.tick()
        self.assertEqual(len(list(generate_actions(self.board.simplified(self.player), self.player))), 8)
        self.player.attack.tick()
        self.assertEqual(len(list(generate_actions(self.board.simplified(self.player), self.player))), 9)
        self.player.ultimate.tick()
        self.board.move(self.player.pos, (4, 5))
        self.assertEqual(len(list(generate_actions(self.board.simplified(self.player), self.player))), 73)


if __name__ == '__main__':
    unittest.main()
