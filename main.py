import chess
import chess.svg
import chess.engine
import chess.pgn
from queue import Queue
import random
from flask import Flask, render_template
import threading
import time
import os
def get_piece_val(piece):
    if piece is None:
        return 0
    
    piece_values = {
        "P": 10, "p": 10,  # Pawn
        "N": 30, "n": 30,  # Knight
        "B": 30, "b": 30,  # Bishop
        "R": 50, "r": 50,  # Rook
        "Q": 90, "q": 90,  # Queen
        "K": 900, "k": 900  # King
    }
    
    return piece_values.get(piece, 0)

def is_favorable_move(board: chess.Board, move: chess.Move) -> bool:
    if move.promotion is not None:
        return True  # Promotion is always favorable

    if board.is_capture(move) and not board.is_en_passant(move):
        captured_piece = board.piece_type_at(move.to_square)
        attacking_piece = board.piece_type_at(move.from_square)
        
        # Favorable if capturing a higher value piece
        if get_piece_val(attacking_piece) < get_piece_val(captured_piece):
            return True
        
        # More attackers than defenders on the target square
        if len(board.attackers(board.turn, move.to_square)) > len(board.attackers(not board.turn, move.to_square)):
            return True
    
    return False


pgn_file_path = "static/lichess_db_standard_rated_2013-06.pgn"  # Update to your PGN file path
def get_board_key(board) :
    """Convert board position to a hashable state representation."""
    return board.fen()
class Agent:
    def __init__(self, side, board):
        self.side = side
        self.board = board
        self.moves = []
        self.last_move = None
        self.qtable = {}  # Use a dictionary to store Q-values for each board state and action pair
        self.learning_rate = 0.8
        self.discount_factor = 0.95
        self.exploration_prob = 0.2
        self.epochs = 1000  # Number of training epochs
        self.goal_reward = 1  # Reward for achieving a checkmate
        self.move_penalty = -0.01  # Small penalty for each move to encourage quicker wins
        self.capture_reward = 0.5  # Reward for capturing an opponent's piece
    def get_qvalue(self, state, action):
        """Get the Q-value for a given state-action pair."""
        return self.qtable.get((state, action), 0)
    def update_qvalue(self, state, action, reward, next_state):
        """Update the Q-value for a given state-action pair."""
        current_qvalue = self.get_qvalue(state, action)
        legal_moves = list(self.board.legal_moves)
        if not legal_moves:
            return  # Skip if no legal moves
        best_next_action = max(self.get_qvalue(next_state, next_action.uci()) for next_action in legal_moves)
        new_qvalue = current_qvalue + self.learning_rate * (reward + self.discount_factor * best_next_action - current_qvalue)
        self.qtable[(state, action)] = new_qvalue

    def get_bestmove(self):
        """Generate a random legal move for the player."""
        legal_moves = list(self.board.legal_moves)
        favorable_moves = [move for move in legal_moves if is_favorable_move(self.board, move)]
        for l in legal_moves:
            print(is_favorable_move(self.board, l))
        
        if legal_moves:
            if (random.random() < self.exploration_prob):
                self.last_move = random.choice(legal_moves)
                print("Random move: from the agent ", self.last_move)
                
                return self.last_move
            else :
                print("Exploitation move")
                state= get_board_key(self.board)
                q_values = [self.get_qvalue(state, move.uci()) for move in legal_moves]
                self.last_move = legal_moves[q_values.index(max(q_values))]
                return self.last_move
            
        return None
    def play(self):
        player_move = self.get_bestmove()
        if player_move:
                self.board.push(player_move)
        else:
                print("No legal moves available for the player.")
                

        


    
class ChessGame(threading.Thread):
    def __init__(self, lock, fen):
        threading.Thread.__init__(self)
        self.engine_path = r"C:\Users\wergh\Downloads\stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe"
        self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path) #stockfish bot
        
        self.board = chess.Board(fen)
        self.move_number = 0
        self.lock = lock  # Lock for file access during SVG saving
        self.agent = Agent("Black",self.board)

    def save_board_as_svg(self, filename="static/board.svg"):
        """Save the current board state as an SVG file in the static directory."""
        absolute_path = os.path.abspath(filename)  # Get absolute path
        with self.lock:  # Acquire the lock to prevent simultaneous writes
            try:
                with open(absolute_path, "w") as f:
                    f.write(chess.svg.board(board=self.board))
            except Exception as e:
                print(f"Error saving SVG: {e}")  # Print the error message

    def get_random_move(self):
        """Generate a random legal move for the player."""
        legal_moves = list(self.board.legal_moves)
        if legal_moves:
            return random.choice(legal_moves)
        return None
    def set_agent_side(self):
        """Set the agent's side based on the initial board position."""
        if self.board.turn: # Check if it's White's turn
            return  "White"
        else:
            return "Black"

    def analysis(self):
        analysis=self.engine.analyse(self.board, chess.engine.Limit(time=0.1))
        score = analysis.get("score")
        best_move = analysis.get("pv")
        if (score and best_move): return score.relative.score(),best_move
        return 0,None

    def run(self):
        """Run the chess game in a separate thread."""
        while not self.board.is_game_over():
                # Get a random move for the human player
                current_state = get_board_key(self.board)
                is_player_turn = (self.board.turn and self.agent.side == "White") or \
                                (not self.board.turn and self.agent.side == "Black")
                global reward
                if is_player_turn:  # Check if it's White's turn
                    print(self.agent.side + " to move")
                    self.agent.play()
                    if self.agent.last_move is not None:
                        reward = self.analysis()[0]
                        next_state = get_board_key(self.board)
                        if self.board.is_checkmate():
                            reward = self.agent.goal_reward
                        elif self.agent.last_move != None and self.board.is_capture(self.agent.last_move):
                            reward = self.agent.capture_reward
                        elif self.board.is_check():
                            reward = self.agent.move_penalty * 2
                        elif self.board.is_stalemate():
                            reward = self.agent.move_penalty / 2
                        else:
                            reward = self.agent.move_penalty

                        self.agent.update_qvalue(current_state, self.agent.last_move.uci(), reward, next_state)
                        self.save_board_as_svg()
                        self.analysis()
                else:
                    
                        print("Stockfish to move")
                        result = self.engine.play(self.board, chess.engine.Limit(time=2))
                        self.board.push(result.move)
                        self.analysis()
                        self.move_number += 1
                        print(f"Stockfish move {self.move_number}: {result.move}")

                # Save the board after Stockfish's move
                self.save_board_as_svg()
                print(self.agent.qtable)

        # Save final board position
        result = self.board.result()
        print("Game over:", result)
        self.save_board_as_svg(filename="static/board.svg")
        self.engine.quit()  # Close the engine when done


class WebServer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.app = Flask(__name__)

        @self.app.route("/")
        def main():
            return render_template("index.html")  # Render the main page

    def run(self):
        """Run the Flask web server in a separate thread without using the reloader."""
        self.app.run(debug=False, use_reloader=False)  # Disable the reloader and debug mode

def get_endgame_fen(fen_queue):
    """Extracts the FEN of endgame positions from a PGN file."""
    with open(pgn_file_path) as pgn_file:
        game = chess.pgn.read_game(pgn_file)
        while game is not None:
            board = game.board()
            for move in game.mainline_moves():
                board.push(move)
            if len(board.piece_map()) <= 12:
                fen_queue.put(board.fen())  # Put the FEN string into the queue
            game = chess.pgn.read_game(pgn_file)

    # Signal completion by putting a sentinel value
    fen_queue.put(None)  # Use None as a signal that extraction is complete

def main():
    lock = threading.Lock()  # Create a lock for file access
    fen_queue = Queue()

    # Start a thread to extract endgame FENs
    get_endgame_fen_thread = threading.Thread(target=get_endgame_fen, args=(fen_queue,))
    get_endgame_fen_thread.start()

    # Start the Flask web server in a separate thread
    webserver = WebServer()
    webserver.start()


    while True:
        fen = fen_queue.get()  # This will block until a new FEN is available
        if fen is None:  # Check for completion signal
            break  # Exit the loop if extraction is complete
        game = ChessGame(lock, fen)  # Pass the lock and fen to the game
        game.start()
        game.join()


    # Wait for the web server to finish
    webserver.join()
    get_endgame_fen_thread.join()  # Ensure the FEN extraction thread has completed

    for game in threading.enumerate():
        if game != threading.current_thread():
            game.join(timeout=5)
if __name__ == "__main__":
    main()

