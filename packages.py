import chess
import chess.svg
import chess.engine
from flask_cors import CORS
from flask import jsonify,request
from threading import Event
import pickle
from interface import PlayResult,load_q_table,save_q_table,get_board_key
import signal
import sys
import chess.pgn
from queue import Queue
from flask import send_file
from flask import Flask, render_template
import threading
import os
from Agent import Agent
import matplotlib.pyplot as plt
legal_moves_queue = []
legal_moves_lock = threading.Lock()
result_lock = threading.Lock()
play_resulta ={}
human_exist_lock = threading.Lock()
human_exist =False
engine_exist_lock = threading.Lock()
engine_exist=False
human_move_event = Event()  # Event to wait for human move
human_move_lock = threading.Lock()
human_move = None
board_lock = threading.Lock()
board =None
analyse_data_lock = threading.Lock()
analyse_data=None
q_table = load_q_table()  # Load your Q-table here
