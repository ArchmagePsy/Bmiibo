import argparse
import json

from chess import Game, choose_positions

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="play Bmiibo Buto Chess")
    parser.add_argument("--basic-training", dest="basic_training", action="store_true",
                        help="runs the 1v1 basic training program")
    parser.add_argument("--reporting", dest="reporting", action="store_true",
                        help="whether or not to show the board and moves whilst playing")
    parser.add_argument("--discord", dest="train_discord_bmiibos", action="store_true",
                        help="runs the training program for 100 matches of the bmiibos that judy has put in the training queue")
    parser.add_argument("--matches", dest="matches", type=int, choices=list(range(1, 101)), default=1,
                        help="number of matches to play")
    parser.add_argument("board_size", metavar="N", type=int, choices=[4, 8, 16],
                        help="the size of the board in cells NxN, acceptable values of N are 4, 8, and 16")
    parser.add_argument("--match-file", type=str, default=None, action="store",
                        help="the name of the file to write matches to")
    parser.add_argument("--bmiibo-names", dest="names", type=str, nargs="+", action="extend",
                        help="the Bmiibos that will take part in these matches")
    args = parser.parse_args()

    if args.basic_training:
        wins = {
            "basic_one": 0,
            "basic_two": 0
        }
        if args.match_file:
            output = open(args.match_file, "w")
        else:
            output = None
        for i in range(args.matches):
            print("match", i + 1)
            game = Game(args.board_size, basic_one=(0, 0), basic_two=(args.board_size - 1, args.board_size - 1))
            winner = game.play(reporting=args.reporting, file=output)
            wins[winner.name] += 1
            for player in game.players + game.dead:
                player.brain.save()
        if output:
            output.close()
        print("basic_one winrate:", (wins["basic_one"] / args.matches) * 100)
        print("basic_two winrate:", (wins["basic_two"] / args.matches) * 100)
    elif args.train_discord_bmiibos:
        if args.match_file:
            output = open(args.match_file, "w")
        else:
            output = None
        with open("training.json", "r") as training_file:
            training = json.load(training_file)
        for i in range(100):
            game = Game(args.board_size, **{name: pos for name, pos in zip(training, choose_positions(len(training), args.board_size))})
            game.play(reporting=args.reporting, file=output)
            for player in game.players + game.dead:
                player.brain.save()
        if output:
            output.close()
    else:
        if args.match_file:
            output = open(args.match_file, "w")
        else:
            output = None
        for i in range(args.matches):
            game = Game(args.board_size, **{name: pos for name, pos in zip(args.names, choose_positions(len(args.names), args.board_size))})
            game.play(reporting=args.reporting, file=output)
            for player in game.players + game.dead:
                player.brain.save()
        if output:
            output.close()
