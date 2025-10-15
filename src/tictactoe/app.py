# src/tictactoe_client/app.py
from tictactoe.client import OnlineTicTacToe
import tkinter as tk

def main():
    root = tk.Tk()
    app = OnlineTicTacToe(root)
    root.mainloop()
