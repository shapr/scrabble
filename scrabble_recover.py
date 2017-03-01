'''
scrabble_recover.py -- contains functions that recover a game's moves given
                       final board and score list

Usage:
    ./scrabble_recover [INPUT_FILENAME]

    See sample_input_files/ for examples of correctly formatted input files
'''
import itertools
import json
import sys

import config
import scrabble_board
import scrabble_game

scrabble_game.input = lambda x: 'N'

def get_combinations(input_iterable):
    combination_set = set()

    for column_letter in config.BOARD_CODE_DICT:
        column_tile_set = frozenset((tile, location)
                                    for tile, location in input_iterable
                                    if location[0] == column_letter)

        for i in range(1, config.PLAYER_RACK_SIZE + 1):
            for this_set in itertools.combinations(column_tile_set, i):
                combination_set.add(this_set)

    for row_number in range(1, config.BOARD_NUM_ROWS + 1):
        row_tile_set = frozenset((tile, location)
                                 for tile, location in input_iterable
                                 if location[1] == row_number)

        for i in range(1, config.PLAYER_RACK_SIZE + 1):
            for this_set in itertools.combinations(row_tile_set, i):
                combination_set.add(this_set)

    return combination_set

def load_file(input_filename):
    with open(input_filename, 'r') as filehandle:
        input_str = filehandle.read()

    input_dict = json.loads(input_str)
    board_character_array = input_dict['board']
    player_score_list_list = input_dict['scores']

    return board_character_array, player_score_list_list

def read_input_file(input_filename):
    board_character_array, player_score_list_list = load_file(input_filename)

    num_players = len(player_score_list_list)
    game = scrabble_game.ScrabbleGame(num_players)
    game.player_score_list_list = player_score_list_list
    game.player_rack_list = [[] for _ in range(num_players)]
    game.tile_bag = []
    game.move_number = sum(1 for player_score_list in player_score_list_list
                             for _ in player_score_list)

    for row_number, row in enumerate(board_character_array):
        for column_number, letter in enumerate(row):
            if letter:
                column_letter = chr(ord('a') + column_number)
                this_location = (column_letter, row_number + 1)
                game.board[this_location] = scrabble_board.ScrabbleTile(letter)

    return game

def get_all_board_tiles(game):
    return set((square_tuple[1].tile, square_tuple[0])  # tile then location
               for square_tuple in game.board.board_square_dict.items()
               if square_tuple[1].tile)

def move_is_board_subset(move_set, board):
    for tile, location in move_set:
        move_letter = tile.letter
        board_tile = board[location]
        if not board_tile or board_tile.letter != move_letter:
            return False

    return True

def boards_are_equivalent(board_1, board_2):
    return str(board_1) == str(board_2)

def get_all_possible_moves_set(new_game, reference_game):
    game_tile_location_set = get_all_board_tiles(new_game)
    reference_tile_location_set = get_all_board_tiles(reference_game)

    search_set = set()
    for reference_tile, reference_location in reference_tile_location_set:
        flag = True
        for game_tile, game_location in game_tile_location_set:
            if (game_tile.letter == reference_tile.letter and
                    game_location == reference_location):
                flag = False

        if flag:
            search_set.add((reference_tile, reference_location))

    return get_combinations(search_set)

def copy_board(input_board):
    input_square_dict = input_board.board_square_dict

    new_board = scrabble_board.ScrabbleBoard()
    new_square_dict = new_board.board_square_dict

    for location, square in input_square_dict.items():
        if square.tile:
            new_board_square = new_square_dict[location]
            new_board_square.letter_multiplier = square.letter_multiplier
            new_board_square.word_multiplier = square.word_multiplier
            new_board_square.tile = scrabble_board.ScrabbleTile(
                square.tile.letter
            )

    return new_board

def copy_game(input_game):
    new_game = scrabble_game.ScrabbleGame(len(input_game.player_rack_list))
    new_game.board = copy_board(input_game.board)
    new_game.move_number = input_game.move_number
    new_game.player_score_list_list = [
        input_player_score_list[:]
        for input_player_score_list in input_game.player_score_list_list
    ]

    return new_game

def get_legal_move_set(new_game, reference_game):
    all_possible_moves_set = get_all_possible_moves_set(new_game,
                                                        reference_game)

    legal_move_set = set()
    for move_set in all_possible_moves_set:
        if (move_is_board_subset(move_set, reference_game.board) and
                scrabble_game.move_is_legal(new_game.board,
                                            new_game.move_number,
                                            move_set)):
            temp_board = copy_board(new_game.board)
            for tile, location in move_set:
                temp_board[location] = tile

            legal_move_set.add(
                (scrabble_game.score_move(move_set, temp_board), move_set)
            )

    return legal_move_set

def get_best_move(game):
    player_to_move_id = game.move_number % len(game.player_rack_list)
    player_rack = game.player_rack_list[player_to_move_id]

    player_letter_list = [tile.letter for tile in player_rack]
    word_list = get_combinations(player_letter_list)

    high_score = 0
    best_move = None
    for location in game.board.board_square_dict:
        for word in word_list:
            for is_vertical in [True, False]:
                temp_game = copy_game(game)
                temp_game.place_word(word, location, is_vertical)
                word_score = (
                    temp_game.player_score_list_list[player_to_move_id][-1]
                )

                if word_score > high_score:
                    best_move = (location, word, is_vertical)
                    high_score = word_score

    return best_move, high_score

def get_move_set_generator(new_game, reference_game, move_list):
    legal_move_set = get_legal_move_set(new_game, reference_game)

    player_to_move_id = new_game.move_number % len(new_game.player_rack_list)
    player_score_list = reference_game.player_score_list_list[player_to_move_id]
    player_move_number = new_game.move_number // len(new_game.player_rack_list)
    target_score = player_score_list[player_move_number]

    next_move_set = set(
        frozenset((tile.letter, location) for tile, location in move_set)
        for score, move_set in legal_move_set
        if score == target_score
    )

    for next_move in next_move_set:
        new_game_copy = copy_game(new_game)
        move_list_copy = move_list[:]

        player_to_move_id = (
            new_game_copy.move_number % len(new_game_copy.player_rack_list)
        )

        next_move_str = ''.join(letter for letter, location in next_move)
        new_game_copy.cheat_create_rack_word(next_move_str, player_to_move_id)
        new_game_copy.next_player_move(next_move)
        move_list_copy.append(next_move)

        if new_game_copy.move_number == reference_game.move_number:
            if boards_are_equivalent(reference_game.board, new_game_copy.board):
                yield move_list_copy

        else:
            yield from get_move_set_generator(new_game_copy,
                                              reference_game,
                                              move_list_copy)

def get_move_set_notation(move_set, reference_game):
    new_game = scrabble_game.ScrabbleGame(len(reference_game.player_rack_list))
    word_notation_list_list = [
        [] for _ in range(len(reference_game.player_rack_list))
    ]

    for move in move_set:
        player_to_move_id = new_game.move_number % len(new_game.player_rack_list)
        move_location_set = set(location for _, location in move)
        rack_word = ''.join([letter for letter, _ in move])
        new_game.cheat_create_rack_word(rack_word, player_to_move_id)

        player_words_notation_list = (
            word_notation_list_list[player_to_move_id]
        )

        notation_word_list = []
        new_game.next_player_move(move)
        word_set = scrabble_game.get_word_set(new_game.board, move_location_set)
        for word_location_set in word_set:
            if word_location_set:
                move_word = ''
                word_location_list = sorted(word_location_set)
                notation_location = word_location_list[0]
                parens_flag = False

                for location in word_location_list:
                    tile = new_game.board[location]
                    if tile:
                        if location not in move_location_set:
                            if not parens_flag:
                                move_word += '('
                                parens_flag = True
                        else:
                            if parens_flag:
                                move_word += ')'
                                parens_flag = False

                        move_word += tile.letter

                if parens_flag:
                    move_word += ')'

                notation_word_list.append((notation_location, move_word))

        player_words_notation_list.append(notation_word_list)

    return word_notation_list_list

def main():
    if len(sys.argv) == 2:
        reference_game = read_input_file(sys.argv[1])
        new_game = scrabble_game.ScrabbleGame(
            len(reference_game.player_rack_list)
        )

        move_set_generator = get_move_set_generator(new_game,
                                                    reference_game,
                                                    [])

        for move_set in move_set_generator:
            print(get_move_set_notation(move_set, reference_game))
            print()
    else:
        print('Usage: ./scrabble_recover [INPUT_FILENAME]')

if __name__ == '__main__':
    main()
