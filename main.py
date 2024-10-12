import chess
import chess.svg
import chess.engine
import random
from flask import Flask, render_template
import threading
import time
import os

class ChessGame(threading.Thread):
    def __init__(self, lock, fen):
        threading.Thread.__init__(self)
        self.engine_path = r"C:\Users\wergh\Downloads\stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe"
        self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
        self.board = chess.Board()
        self.board.set_fen(fen)
        self.move_number = 0
        self.lock = lock  # Lock for file access

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

    def run(self):
        """Run the chess game in a separate thread."""
        while not self.board.is_game_over():
            # Get a random move for the human player
            player_move = self.get_random_move()
            if player_move:
                self.board.push(player_move)
                self.move_number += 1
                print(f"Player move {self.move_number}: {player_move}")
            else:
                print("No legal moves available for the player.")
                break

            self.save_board_as_svg()

            # Use Stockfish to get the best move
            result = self.engine.play(self.board, chess.engine.Limit(time=2))
            self.board.push(result.move)
            self.move_number += 1
            print(f"Stockfish move {self.move_number}: {result.move}")

            # Save the board after Stockfish's move
            self.save_board_as_svg()
            time.sleep(2)  # Add a slight delay for viewing

        # Save final board position
        result = self.board.result()
        print("Game over:", result)
        self.save_board_as_svg(filename="static/final_position.svg")
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


def main():
    fen = "8/5k2/8/8/5Q2/8/8/7K w - - 0 1"
    lock = threading.Lock()  # Create a lock for file access
    game = ChessGame(lock, fen)  # Pass the lock and fen to the game
    game.start()  # Start the ChessGame thread (runs the `run` method)

    # Start the Flask web server in a separate thread
    webserver = WebServer()
    webserver.start()

    # Keep the main thread running, so the game and server can run concurrently
    webserver.join()
    game.join()


if __name__ == "__main__":
    main()
