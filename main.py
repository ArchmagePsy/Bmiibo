import argparse

from chess import Game

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="play Bmiibo Buto Chess")
    parser.add_argument("--basic-training", dest="basic_training", action="store_true",
                        help="runs the 1v1 basic training program")
    parser.add_argument("--reporting", dest="reporting", action="store_true",
                        help="whether or not to show the board and moves whilst playing")
    parser.add_argument("--matches", dest="matches", type=int, choices=list(range(1, 101)), default=1,
                        help="number of matches to play")
    parser.add_argument("board_size", metavar="N", type=int, choices=[4, 8, 16],
                        help="the size of the board in cells NxN, acceptable values of N are 4, 8, and 16")
    args = parser.parse_args()

    if args.basic_training:
        wins = {
            "basic_one": 0,
            "basic_two": 0
        }
        for i in range(args.matches):
            print("match", i + 1)
            g = Game(args.board_size, basic_one=(0, 0), basic_two=(args.board_size-1, args.board_size-1))
            winner = g.play(reporting=args.reporting)
            wins[winner.name] += 1
            for player in g.players + g.dead:
                player.brain.save()
        print("basic_one winrate:", (wins["basic_one"] / args.matches) * 100)
        print("basic_two winrate:", (wins["basic_two"] / args.matches) * 100)
