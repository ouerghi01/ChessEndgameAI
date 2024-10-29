from packages import *
class ChessGame(threading.Thread):
    def __init__(self, lock, fen):
        threading.Thread.__init__(self)
        self.engine_path = r"C:\Users\wergh\Downloads\stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe"
        self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path) #stockfish bot
        self.engine.configure({'Threads': 4})  # Use 4 threads for analysis
        self.engine.configure({'Skill Level': 20})  # Skill level from 0 to 20
        self.board = chess.Board(fen)
        self.move_number = 0
        self.lock = lock  # Lock for file access during SVG saving
        self.agent = Agent("Black",self.board)
    def save_board_as_svg(self, filename="static/board.svg"):
        """Save the current board state as an SVG file in the static directory."""
        absolute_path = os.path.abspath(filename)
        with self.lock:
            try:
                with open(absolute_path, "w") as f:
                    f.write(chess.svg.board(board=self.board))
            except Exception as e:
                print(f"Error saving SVG: {e}")  # Print the error message

    def analysis(self):
        analysis=self.engine.analyse(self.board, chess.engine.Limit(time=0.1))
        score = analysis.get("score")
        best_move = analysis.get("pv")
        if (score and best_move): return score.relative.score(),best_move
        return 0,None
    def check_game_result(self):
        """Check the game result and return a message."""
        if self.board.is_checkmate():
            winner = "White" if self.board.turn == chess.BLACK else "Black"
            return f"{winner} wins by checkmate."
        elif self.board.is_stalemate():
            return "Stalemate! The game is a draw."
        else:
        
            return "Draw"
    def run(self):
        """Run the chess game in a separate thread."""
        global legal_moves_queue
        global legal_moves_lock
        global play_resulta
        global human_exist
        global human_exist_lock
        global engine_exist
        global engine_exist_lock
        global analyse_data
        if engine_exist:
            while not self.board.is_game_over():
                current_state = get_board_key(self.board)
                is_player_turn = (self.board.turn and self.agent.side == "White") or \
                                (not self.board.turn and self.agent.side == "Black")
                reward = 0
                if is_player_turn:
                    self.agent.play(q_table)
                    if self.agent.last_move is not None:
                        with analyse_data_lock:
                            analyse_data=self.analysis()
                            if(analyse_data[0]!=None and analyse_data[0] > 0):
                                reward=analyse_data[0] / 100
                        reward+= self.agent.move_penalty
                        if self.board.is_checkmate():
                            reward =reward+ self.agent.goal_reward
                        if self.agent.last_move != None and self.board.is_capture(self.agent.last_move):
                            reward = reward+ self.agent.capture_reward
                        if self.board.is_check():
                            reward = reward+self.agent.move_penalty * 2
                        if self.board.is_stalemate():
                            reward = reward+self.agent.move_penalty / 2
                        if self.board.fen().count(' ') < 10:
                                reward += self.agent.center_control_reward
                        next_state = get_board_key(self.board)
                        self.agent.update_qvalue(current_state, self.agent.last_move.uci(), reward,
                        next_state,q_table)
                        save_q_table(q_table)
                        self.save_board_as_svg()
                        self.analysis()
                        with legal_moves_lock:
                            legal_moves_queue = [
                            move.uci() for move in self.board.legal_moves
                            if self.board.piece_at(move.from_square) and self.board.piece_at(move.from_square).color == chess.WHITE
                            ]
                else:
                    
                        result = self.engine.play(self.board, chess.engine.Limit(time=4))
                        self.board.push(result.move)
                        self.save_board_as_svg()
                        with analyse_data_lock:
                            analyse_data=self.analysis()
                        self.move_number += 1
                        print(f"Stockfish move {self.move_number}: {result.move}")
                self.save_board_as_svg()
        else:
            self.human_vs_agent()
        with result_lock:
            play_resulta = PlayResult(self.board.result(),self.check_game_result()).to_dict()
        self.save_board_as_svg(filename="static/board.svg")
        self.engine.quit()
    def human_vs_agent(self):
        """Play a game between a human and the agent."""
        global legal_moves_queue
        self.board=chess.Board("8/8/8/8/8/5k2/8/5BKN w - - 0 1")
        self.agent.board=self.board
        self.save_board_as_svg()
        while not self.board.is_game_over():
            current_state = get_board_key(self.board)
            is_player_turn = (self.board.turn and self.agent.side == "White") or \
                                (not self.board.turn and self.agent.side == "Black")
            global board
            board = self.board
            reward = 0
            if is_player_turn:
                self.agent.play(q_table)
                if self.agent.last_move is not None:
                    if self.board.is_checkmate():
                        reward = reward+self.agent.goal_reward
                    elif self.agent.last_move != None and self.board.is_capture(self.agent.last_move):
                        reward = reward+self.agent.capture_reward
                    elif self.board.is_check():
                        reward = reward+self.agent.move_penalty * 2
                    elif self.board.is_stalemate():
                        reward = reward+self.agent.move_penalty / 2
                    else:
                        reward = reward+self.agent.move_penalty
                    next_state = get_board_key(self.board)
                    self.agent.update_qvalue(current_state, self.agent.last_move.uci(), reward, next_state,q_table)
                    self.save_board_as_svg()
                    with legal_moves_lock:
                        legal_moves_queue = [
                            move.uci() for move in self.board.legal_moves
                            if self.board.piece_at(move.from_square) and self.board.piece_at(move.from_square).color == chess.WHITE
                        ]
                    with board_lock:
                        board =self.board
                    human_move_event.clear()
            else:
                global human_move
                with legal_moves_lock:
                    legal_moves_queue = [
                            move.uci() for move in self.board.legal_moves
                            if self.board.piece_at(move.from_square) and self.board.piece_at(move.from_square).color == chess.WHITE
                        ]
                print("Waiting for human to play...")
                human_move_event.wait()
                self.board.push(human_move)
                self.save_board_as_svg()
                human_move = None
                human_move_event.clear()
                with human_exist_lock:
                    human_exist = False

class WebServer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.app = Flask(__name__)
        self.get_endgame_fen_thread = None
        self.lock = threading.Lock()  # Lock for file access
        self.fen_queue = Queue()
        self.condition = threading.Condition()
        self.game_thread = None  # Store the game thread instance
        self.cors = CORS(self.app)
        self.app.config['CORS_HEADERS'] = 'Content-Type'

        @self.app.route("/")
        def main():
            return render_template("index.html")  # Render the main page

        @self.app.route("/board")
        def board():
            return send_file("static/board.svg", mimetype="image/svg+xml")

        @self.app.route("/moves")
        def get_legal_moves():
            with legal_moves_lock:
                current_legal_moves = legal_moves_queue
            return jsonify({"legal_moves": current_legal_moves})
        
        @self.app.route("/result")
        def get_result():
            with result_lock:
                if play_resulta == {}:
                    current_result = PlayResult("x-x", "The game is still ongoing").to_dict()
                else:
                    current_result = play_resulta
            return jsonify(current_result)
        
        @self.app.post("/play")
        def play():
            global human_exist
            global engine_exist
            with human_exist_lock:
                human_exist = True
            with engine_exist_lock:
                engine_exist = False
            self.start_game_threads()

            return jsonify({"status": "Human Playing"})

        @self.app.post("/stockfish")
        def stockfish():
            global human_exist
            global engine_exist
            with human_exist_lock:
                human_exist = False
            with engine_exist_lock:
                engine_exist = True
            self.start_game_threads()  # Start the game threads
            return jsonify({"status": "Stockfish Playing"})
        @self.app.post("/move_piece")
        def execute_human_move():
            """Receive a move from the human and release the agent from waiting."""
            try:
                data = request.get_json()
                if not data or 'move' not in data:
                    return jsonify({"status": "Invalid request, 'move' field is missing"}), 400
                move = data['move']
                if self.receive_human_move(move):
                    return jsonify({"status": "Move received"}), 200
                else:
                    return jsonify({"status": "Invalid move"}), 400
            except Exception as e:
                return jsonify({"status": f"An error occurred: {str(e)}"}), 500
    def receive_human_move(self, move):
            """Receive a move from the human and release the agent from waiting."""
            global human_move
            if board.is_legal(chess.Move.from_uci(move)):
                with human_move_lock:
                    human_move = chess.Move.from_uci(move)
                human_move_event.set()  # Allow the agent to proceed
                return True
            return False
    def start_game_threads(self):
        """Start the game threads only if they are not running."""
        # Ensure that no other game is running
        if self.game_thread is None or not self.game_thread.is_alive():
            # Start a new game thread
            self.game_thread = threading.Thread(target=self.start_game_logic)
            self.game_thread.start()
        else:
            print("A game is already running. Please wait for it to finish.")

    def start_game_logic(self):
        """Logic for running the game in a thread."""
        self.get_endgame_fen_thread = threading.Thread(target=get_endgame_fen, args=(self.fen_queue, self.condition))
        self.consumer_thread = threading.Thread(target=process_fen, args=(self.lock, self.fen_queue, legal_moves_queue, self.condition))

        self.get_endgame_fen_thread.start()
        self.consumer_thread.start()

        self.get_endgame_fen_thread.join()
        self.consumer_thread.join()
        for game in threading.enumerate():
            if game != threading.current_thread():
                game.join(timeout=5)


    def run(self):
        """Run the Flask web server in a separate thread without using the reloader."""
        self.app.run(debug=False, use_reloader=False)  # Disable the reloader and debug mode

def get_endgame_fen(fen_queue, condition):
    """Extracts the FEN of endgame positions from a PGN file."""
    pgn_file_path = "static/lichess_db_standard_rated_2013-06.pgn"
    with open(pgn_file_path) as pgn_file:
        game = chess.pgn.read_game(pgn_file)
        while game is not None:
            board = game.board()
            for move in game.mainline_moves():
                board.push(move)
            if len(board.piece_map()) <= 12:
                with condition:
                    fen_queue.put(board.fen())
                    print(f"Generated: {board.fen()}")
                    condition.notify()
            game = chess.pgn.read_game(pgn_file)
    with condition:
        fen_queue.put(None)
        condition.notify()

def process_fen(lock, fen_queue,legal_moves_queue, condition):
    while True:
        with condition:
            while fen_queue.empty():
                condition.wait()
            fen = fen_queue.get()
            if fen is None:
                break
            game = ChessGame(lock, fen)
            game.start()
            game.join()

def start_app():
    webserver = WebServer()
    webserver.start()
    webserver.join()

if __name__ == "__main__":
    start_app()