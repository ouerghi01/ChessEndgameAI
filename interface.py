
import pickle
import os
class PlayResult:
    def __init__(self, result,reason):
        self.result = result
        self.reason = reason
    def to_dict(self):
        return {
            "resulta": self.result,
            "reason": self.reason
        }
def get_board_key(board) :
    """Convert board position to a hashable state representation."""
    return board.fen()
def save_q_table(q_table, filename="static/q_table.pkl"):
    """Save the Q-table to a file using pickle, updating existing data without flushing it."""
    if os.path.exists(filename):
        with open(filename, "rb") as f:
            try:
                existing_q_table = pickle.load(f)
            except EOFError:
                existing_q_table = {}
    else:
        existing_q_table = {}
    existing_q_table.update(q_table)
    with open(filename, "wb") as f:
        pickle.dump(existing_q_table, f)
def load_q_table(filename="static/q_table.pkl"):
    """Load the Q-table from a file using pickle."""
    try:
        with open(filename, "rb") as f:
            q_table = pickle.load(f)
        return q_table
    except FileNotFoundError:
        return {}