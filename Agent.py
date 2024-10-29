import random
import threading
import numpy as np
from numpy.linalg import norm
import pickle

class Agent:
    def __init__(self, side, board):
        self.side = side
        self.board = board
        self.moves = []
        self.last_move = None
        self.learning_rate = 0.8
        self.discount_factor = 0.95
        self.exploration_prob = 0.2
        self.exploration_decay = 0.99
        self.goal_reward = 1  # Reward for achieving a checkmate
        self.move_penalty = -0.01  # Small penalty for each move to encourage quicker wins
        self.capture_reward = 0.5  # Reward for capturing an opponent's piece
        self.center_control_reward = 0.05
    def get_qvalue(self, state, action, q_table):
        """Get the Q-value for a given state-action pair, using similarity if an exact match isn't found."""
        state_array = self.fen_to_integer_array(state)
        max_sim_score = 0
        best_match_key = (state, action)
        for state_, action_ in q_table.keys():
            state_array_ = self.fen_to_integer_array(state_)
            sim_score = self.find_similar_states(state_array, state_array_)
            if sim_score > max_sim_score:
                max_sim_score = sim_score
                best_match_key = (state_, action_)
        return q_table.get(best_match_key, 0)

    def fen_to_integer_array(self, fen):
        """Convert a FEN string to an integer array."""
        piece_to_int = {
        'P': 1, 'N': 2, 'B': 3, 'R': 4, 'Q': 5, 'K': 6,
        'p': -1, 'n': -2, 'b': -3, 'r': -4, 'q': -5, 'k': -6
        }

        board = np.zeros((8,8), dtype=int)
        fen_rows= fen.split(' ')[0].split('/')
        for i, row in enumerate(fen_rows):
            j = 0
            for char in row:
                if char.isdigit():
                    j += int(char)
                elif char in piece_to_int:
                    board[i, j] = piece_to_int[char]
                    j += 1
        return board
    def find_similar_states(self, fen1_array,fen2_array):
        """Find all states similar between  2 given state."""
        norm1= norm(fen1_array)
        norm2= norm(fen2_array)
        if norm1 == 0 or norm2 == 0:
            return 0
        cosine_similarity= np.dot(fen1_array.flatten(), fen2_array.flatten()) / (norm(fen1_array) * norm(fen2_array))
        similarity_score = (cosine_similarity + 1) / 2
        return similarity_score

        
    def update_qvalue(self, state, action, reward, next_state,q_table):
        """Update the Q-value for a given state-action pair."""
        current_qvalue = self.get_qvalue(state, action,q_table)
        legal_moves = list(self.board.legal_moves)
        if not legal_moves:
            return
        best_next_action = max(self.get_qvalue(next_state, next_action.uci(), q_table) for next_action in legal_moves)
        new_qvalue = current_qvalue + self.learning_rate * (reward + self.discount_factor * best_next_action - current_qvalue)
        q_table[(state, action)] = new_qvalue

    def get_bestmove(self,q_table):
        """Generate a random legal move for the player."""
        legal_moves = list(self.board.legal_moves)
        if legal_moves:
            self.exploration_prob *= self.exploration_decay
            if (random.random() < self.exploration_prob):
                self.last_move = random.choice(legal_moves)
                return self.last_move
            else :
                state= self.board.fen()
                q_values = [self.get_qvalue(state, move.uci(), q_table) for move in legal_moves]
                max_q_value = max(q_values)
                best_moves = [move for move, q_val in zip(legal_moves, q_values) if q_val == max_q_value]
                capture_moves = [move for move in best_moves if self.board.is_capture(move)]
                check_moves = [move for move in best_moves if self.board.gives_check(move)]
                self.last_move = (capture_moves or check_moves or best_moves)[0]
                return self.last_move
            
        return None
    def play(self,q_table):
        player_move = self.get_bestmove(q_table)
        if player_move:
                self.board.push(player_move)
        else:
                print("No legal moves available for the player.")
