# tictactoe_online_client.py
import tkinter as tk
from tkinter import messagebox
import socket
import threading
import json
import queue
import random
import time

SERVER_PORT = 7777

# reuse previous game logic helpers
WINS = [
    (0,1,2),(3,4,5),(6,7,8),
    (0,3,6),(1,4,7),(2,5,8),
    (0,4,8),(2,4,6)
]

def check_winner_local(board):
    for a,b,c in WINS:
        if board[a] != " " and board[a] == board[b] == board[c]:
            return board[a], (a,b,c)
    if " " not in board:
        return "Tie", ()
    return None, ()

# ------- Network helper (client) -------
class NetClient:
    def __init__(self):
        self.sock = None
        self.listener_thread = None
        self.recv_queue = queue.Queue()
        self.running = False

    def connect(self, host, port=SERVER_PORT):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        self.sock.connect((host, port))
        self.sock.settimeout(None)
        self.running = True
        self.listener_thread = threading.Thread(target=self._listen, daemon=True)
        self.listener_thread.start()

    def _listen(self):
        buf = b""
        try:
            while self.running:
                data = self.sock.recv(4096)
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    try:
                        msg = json.loads(line.decode("utf-8"))
                        self.recv_queue.put(msg)
                    except:
                        pass
        except Exception as e:
            print("Net listen error:", e)
        finally:
            self.running = False
            try:
                self.sock.close()
            except:
                pass
            self.recv_queue.put({"type":"disconnected"})

    def send(self, obj):
        try:
            self.sock.sendall((json.dumps(obj) + "\n").encode("utf-8"))
        except Exception:
            pass

    def close(self):
        self.running = False
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
        except:
            pass

# ------- GUI -------
class OnlineTicTacToe:
    def __init__(self, root):
        self.root = root
        self.root.title("TicTacToe Online (Season 1 & 2)")
        self.root.geometry("420x520")
        self.root.configure(bg="#0f1724")

        self.board = [" "] * 9
        self.buttons = []
        self.current = "X"
        self.is_online_game = False
        self.my_symbol = None
        self.opponent = None

        # network
        self.net = NetClient()

        # UI
        self.create_top()
        self.create_board()
        self.status = tk.Label(self.root, text="Offline", bg="#0f1724", fg="#a5b4fc", font=("Segoe UI", 12))
        self.status.pack(pady=6)
        # create online control frame
        self.create_online_panel()

        # polling network queue into UI
        self.root.after(100, self.process_network)

    def create_top(self):
        top = tk.Frame(self.root, bg="#0f1724")
        top.pack(pady=8)
        tk.Label(top, text="TicTacToe Online", fg="white", bg="#0f1724", font=("Segoe UI", 18, "bold")).pack()

    def create_board(self):
        frame = tk.Frame(self.root, bg="#0f1724")
        frame.pack(pady=10)
        for i in range(9):
            btn = tk.Button(frame, text=" ", font=("Segoe UI", 28, "bold"),
                            width=4, height=2, bg="#0b1220", fg="white", relief="flat",
                            command=lambda i=i: self.local_click(i))
            btn.grid(row=i//3, column=i%3, padx=6, pady=6)
            self.buttons.append(btn)

    def create_online_panel(self):
        panel = tk.Frame(self.root, bg="#0f1724")
        panel.pack(pady=8)
        tk.Label(panel, text="Server IP:", bg="#0f1724", fg="#c7d2fe").grid(row=0, column=0, sticky="e")
        self.entry_ip = tk.Entry(panel)
        self.entry_ip.grid(row=0, column=1, padx=5)
        self.entry_ip.insert(0, "127.0.0.1")

        tk.Label(panel, text="Username:", bg="#0f1724", fg="#c7d2fe").grid(row=1, column=0, sticky="e")
        self.entry_user = tk.Entry(panel)
        self.entry_user.grid(row=1, column=1, padx=5)
        self.entry_user.insert(0, f"user{random.randint(1000,9999)}")

        tk.Label(panel, text="Season:", bg="#0f1724", fg="#c7d2fe").grid(row=2, column=0, sticky="e")
        self.season_var = tk.StringVar(value="season1")
        tk.OptionMenu(panel, self.season_var, "season1", "season2").grid(row=2, column=1, sticky="w")

        btn_frame = tk.Frame(panel, bg="#0f1724")
        btn_frame.grid(row=3, column=0, columnspan=2, pady=6)
        self.btn_connect = tk.Button(btn_frame, text="Connect", command=self.on_connect, bg="#60a5fa")
        self.btn_connect.pack(side="left", padx=4)
        self.btn_find = tk.Button(btn_frame, text="Find Match", command=self.on_find_match, bg="#34d399", state="disabled")
        self.btn_find.pack(side="left", padx=4)
        self.btn_disconnect = tk.Button(btn_frame, text="Disconnect", command=self.on_disconnect, bg="#f87171", state="disabled")
        self.btn_disconnect.pack(side="left", padx=4)

        # Battle pass display
        self.bp_label = tk.Label(self.root, text="Battle Pass: XP 0", bg="#0f1724", fg="#facc15", font=("Segoe UI", 11))
        self.bp_label.pack(pady=4)

    def local_click(self, i):
        if self.is_online_game:
            # if it's our turn, send move to server
            if self.my_symbol and self.my_symbol == self.current:
                self.net.send({"type":"move", "index": i})
            else:
                # not our turn
                pass
        else:
            # local play: toggle
            if self.board[i] != " ":
                return
            self.board[i] = self.current
            self.buttons[i].config(text=self.current, fg="#60a5fa" if self.current=="X" else "#fb7185")
            winner, combo = check_winner_local(self.board)
            if winner:
                self.end_local_game(winner, combo)
            else:
                self.current = "O" if self.current == "X" else "X"
                self.status.config(text=f"{self.current}'s turn (local)")

    def end_local_game(self, winner, combo):
        if winner == "Tie":
            messagebox.showinfo("Game Over", "Tie")
        else:
            for c in combo:
                self.buttons[c].config(bg="#fde68a")
            messagebox.showinfo("Game Over", f"{winner} wins!")
        self.disable_board()

    def disable_board(self):
        for b in self.buttons:
            b.config(state="disabled")

    def enable_board(self):
        for b in self.buttons:
            b.config(state="normal", text=" ", bg="#0b1220", fg="white")
        self.board = [" "] * 9
        self.current = "X"

    # ---- Networking UI actions ----
    def on_connect(self):
        ip = self.entry_ip.get().strip()
        user = self.entry_user.get().strip()
        if not ip or not user:
            messagebox.showwarning("Input", "Enter server IP and username")
            return
        try:
            self.net.connect(ip, SERVER_PORT)
        except Exception as e:
            messagebox.showerror("Connect failed", str(e))
            return
        # send join message
        self.net.send({"type":"join","username": user, "season": self.season_var.get()})
        self.btn_connect.config(state="disabled")
        self.btn_disconnect.config(state="normal")
        self.status.config(text="Connected (awaiting server)...")
        self.root.after(100, self.process_network)

    def on_find_match(self):
        self.net.send({"type":"queue"})
        self.status.config(text="Queued for match...")

    def on_disconnect(self):
        try:
            self.net.send({"type":"leave"})
            self.net.close()
        except:
            pass
        self.btn_connect.config(state="normal")
        self.btn_disconnect.config(state="disabled")
        self.btn_find.config(state="disabled")
        self.is_online_game = False
        self.status.config(text="Disconnected")
        self.bp_label.config(text="Battle Pass: XP 0")

    # ---- Network message processing ----
    def process_network(self):
        while not self.net.recv_queue.empty():
            msg = self.net.recv_queue.get()
            self.handle_net_msg(msg)
        self.root.after(100, self.process_network)

    def handle_net_msg(self, msg):
        t = msg.get("type")
        if t == "joined":
            self.status.config(text=f"Joined as {msg.get('username')} (XP {msg.get('xp',0)})")
            self.btn_find.config(state="normal")
            self.bp_label.config(text=f"Battle Pass: XP {msg.get('xp',0)}")
        elif t == "queued":
            self.status.config(text="Queued for match...")
        elif t == "matched":
            # start online game
            self.is_online_game = True
            self.enable_board()
            self.my_symbol = msg.get("you")
            self.opponent = msg.get("opponent")
            self.current = "X"  # server sets X first
            self.status.config(text=f"Matched vs {self.opponent}. You are {self.my_symbol}")
            # disable find button while in game
            self.btn_find.config(state="disabled")
        elif t == "board_update":
            board = msg.get("board", [])
            for i, val in enumerate(board):
                if val != " ":
                    self.buttons[i].config(text=val, fg="#60a5fa" if val=="X" else "#fb7185", state="disabled", bg="#0b1220")
                    self.board[i] = val
            winner = msg.get("winner")
            combo = msg.get("combo", [])
            if winner:
                if winner == "Tie":
                    messagebox.showinfo("Game Over", "Tie")
                else:
                    for c in combo:
                        self.buttons[c].config(bg="#fde68a")
                    messagebox.showinfo("Game Over", f"{winner} wins!")
                self.is_online_game = False
                self.btn_find.config(state="normal")
            else:
                # update who's turn it is
                next_turn = msg.get("next_turn")
                if next_turn == self.entry_user.get().strip():
                    self.current = self.my_symbol
                    self.status.config(text="Your turn (online)")
                else:
                    self.current = "O" if self.my_symbol == "X" else "X"
                    self.status.config(text=f"{next_turn}'s turn")
        elif t == "xp_award":
            amount = msg.get("amount",0)
            total = msg.get("total",0)
            reason = msg.get("reason","")
            messagebox.showinfo("Battle Pass", f"XP +{amount} ({reason}). Total XP: {total}")
            self.bp_label.config(text=f"Battle Pass: XP {total}")
        elif t == "xp":
            self.bp_label.config(text=f"Battle Pass: XP {msg.get('xp',0)}")
        elif t == "opponent_left":
            messagebox.showinfo("Match", "Opponent left the match")
            self.is_online_game = False
            self.btn_find.config(state="normal")
        elif t == "disconnected":
            messagebox.showwarning("Network", "Disconnected from server")
            self.on_disconnect()
        elif t == "error":
            messagebox.showerror("Server error", msg.get("message",""))
        else:
            # unknown / debug
            # print("Net msg:", msg)
            pass

if __name__ == "__main__":
    root = tk.Tk()
    app = OnlineTicTacToe(root)
    root.mainloop()
