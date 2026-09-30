#dont froget to download stock fish and chane the line 21 to the place stock fish is
#made bt Arshiya1932
import os
import requests
import chess
import chess.pgn
import chess.engine
import io
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import time
from PIL import Image, ImageTk, ImageDraw, ImageFont

class ChessAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chess.com Game Analyzer")
        self.root.geometry("1200x750")
        
        self.game_pgns = []
        self.stockfish_path = None
        self.piece_images = {}
        self.square_size = 70
        self.eval_bar_width = 20
        
        # Playback State
        self.game_states = []
        self.current_idx = -1
        self.auto_play_active = False
        self.auto_play_speed = 0.5
        self.analyzing_complete = False
        
        # Simulation State
        self.simulating = False
        
        # --- UI LAYOUT ---
        left_frame = ttk.Frame(root, padding="10")
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        top_input_frame = ttk.Frame(left_frame)
        top_input_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(top_input_frame, text="Chess.com Username:").grid(row=0, column=0, padx=5, pady=5)
        self.username_entry = ttk.Entry(top_input_frame, width=20)
        self.username_entry.grid(row=0, column=1, padx=5, pady=5)
        self.username_entry.insert(0, "hikaru")
        
        self.fetch_btn = ttk.Button(top_input_frame, text="Fetch Games", command=self.start_fetch_thread)
        self.fetch_btn.grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(left_frame, text="Games (Newest at top):").pack(anchor=tk.W, pady=(10, 0))
        
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.game_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=("Consolas", 10), width=55, height=15)
        self.game_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.game_listbox.yview)
        
        self.game_listbox.bind('<Double-1>', self.start_analysis_thread)
        
        self.analyze_btn = ttk.Button(left_frame, text="Analyze Selected Game", command=self.start_analysis_thread)
        self.analyze_btn.pack(pady=10)
        
        # Right Panel
        right_frame = ttk.Frame(root, padding="10")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # --- TAB 1: Output ---
        output_tab = ttk.Frame(self.notebook)
        self.notebook.add(output_tab, text="Analysis Output")
        
        top_output_frame = ttk.Frame(output_tab)
        top_output_frame.pack(fill=tk.X, pady=5)
        
        self.engine_status = ttk.Label(top_output_frame, text="Stockfish: Searching Arshiya folder...")
        self.engine_status.pack(side=tk.LEFT)
        
        self.browse_btn = ttk.Button(top_output_frame, text="Browse for Stockfish...", command=self.browse_stockfish)
        self.browse_btn.pack(side=tk.RIGHT)
        
        self.output_text = tk.Text(output_tab, state=tk.DISABLED, bg="#f0f0f0", font=("Consolas", 10))
        self.output_text.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # --- TAB 2: Board ---
        board_tab = ttk.Frame(self.notebook)
        self.notebook.add(board_tab, text="Chess Board")
        
        controls = ttk.Frame(board_tab)
        controls.pack(fill=tk.X, pady=5)
        
        self.btn_restart = ttk.Button(controls, text="Restart Game", command=self.restart_game)
        self.btn_restart.pack(side=tk.LEFT, padx=5)
        
        self.btn_last = ttk.Button(controls, text="<< Last", command=self.last_move)
        self.btn_last.pack(side=tk.LEFT, padx=5)
        
        self.btn_next = ttk.Button(controls, text="Next >>", command=self.next_move)
        self.btn_next.pack(side=tk.LEFT, padx=5)
        
        self.btn_show_best = ttk.Button(controls, text="Show Best", command=self.show_best_move)
        self.btn_show_best.pack(side=tk.LEFT, padx=5)
        
        self.btn_what_if = ttk.Button(controls, text="What If Best?", command=self.toggle_what_if)
        self.btn_what_if.pack(side=tk.LEFT, padx=5)
        
        # NEW RETURN BUTTON
        self.btn_return = ttk.Button(controls, text="Return to Game", command=self.return_to_game)
        self.btn_return.pack(side=tk.LEFT, padx=5)
        
        self.auto_play_var = tk.BooleanVar(value=False)
        self.btn_auto = ttk.Checkbutton(controls, text="Auto Play", variable=self.auto_play_var, command=self.toggle_auto_play, style="Toolbutton")
        self.btn_auto.pack(side=tk.LEFT, padx=5)
        
        self.btn_settings = ttk.Button(controls, text="Settings", command=self.open_settings)
        self.btn_settings.pack(side=tk.RIGHT, padx=5)
        
        self.lbl_move_info = ttk.Label(board_tab, text="Select a game to analyze.", font=("Arial", 11))
        self.lbl_move_info.pack(pady=5)
        
        board_container = ttk.Frame(board_tab)
        board_container.pack(pady=10)
        
        self.eval_canvas = tk.Canvas(board_container, width=self.eval_bar_width, height=self.square_size*8, bg="#313131", highlightthickness=0)
        self.eval_canvas.pack(side=tk.LEFT, fill=tk.Y)
        
        self.canvas = tk.Canvas(board_container, width=self.square_size*8, height=self.square_size*8, bg="#4a4a4a", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT)
        
        threading.Thread(target=self.load_custom_pieces, daemon=True).start()
        threading.Thread(target=self.auto_find_stockfish, daemon=True).start()

    def log(self, message):
        self.root.after(0, lambda: self._update_log(message))

    def _update_log(self, message):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)

    def generate_fallback_piece(self, color, piece):
        img = Image.new("RGBA", (self.square_size, self.square_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        bg_color = (240, 240, 240) if color == 'w' else (30, 30, 30)
        txt_color = (0, 0, 0) if color == 'w' else (255, 255, 255)
        draw.ellipse([5, 5, self.square_size-5, self.square_size-5], fill=bg_color, outline=(100, 100, 100), width=2)
        try: font = ImageFont.truetype("arial.ttf", int(self.square_size * 0.5))
        except: font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), piece, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text(((self.square_size-w)/2, (self.square_size-h)/2 - 3), piece, fill=txt_color, font=font)
        return img

    def find_file_in_arshiya(self, filename):
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        arshiya_folder = os.path.join(desktop_path, "Arshiya")
        filename_lower = filename.lower()
        if os.path.exists(arshiya_folder):
            for root, dirs, files in os.walk(arshiya_folder):
                for file in files:
                    if file.lower() == filename_lower:
                        return os.path.join(root, file)
        return None

    def load_custom_pieces(self):
        pieces = ['P', 'N', 'B', 'R', 'Q', 'K']
        colors = ['w', 'b']
        found_count = 0
        for color in colors:
            for piece in pieces:
                filename = f"{color}{piece}.png"
                filepath = self.find_file_in_arshiya(filename)
                try:
                    if filepath:
                        img = Image.open(filepath).convert("RGBA")
                        img = img.resize((self.square_size, self.square_size), Image.Resampling.LANCZOS)
                        self.piece_images[f"{color}{piece}"] = ImageTk.PhotoImage(img)
                        found_count += 1
                    else:
                        img = self.generate_fallback_piece(color, piece)
                        self.piece_images[f"{color}{piece}"] = ImageTk.PhotoImage(img)
                except Exception:
                    img = self.generate_fallback_piece(color, piece)
                    self.piece_images[f"{color}{piece}"] = ImageTk.PhotoImage(img)
        self.log(f"Loaded {found_count}/12 custom pieces from Arshiya folder.")

    def draw_eval_bar(self, eval_score):
        self.eval_canvas.delete("all")
        h = self.square_size * 8
        clamped_eval = max(-10.0, min(10.0, eval_score))
        white_prob = (clamped_eval + 10.0) / 20.0
        white_height = h * white_prob
        black_height = h - white_height
        self.eval_canvas.create_rectangle(0, 0, self.eval_bar_width, black_height, fill="#313131", outline="")
        self.eval_canvas.create_rectangle(0, black_height, self.eval_bar_width, h, fill="#ffffff", outline="")
        if abs(eval_score) >= 10:
            eval_str = f"M{abs(int(eval_score))}"
        else:
            eval_str = f"{eval_score:+.1f}"
        text_y = max(10, min(h-10, black_height))
        text_color = "black" if white_prob > 0.5 else "white"
        self.eval_canvas.create_text(self.eval_bar_width/2, text_y, text=eval_str, fill=text_color, font=("Arial", 8, "bold"))

    def draw_board(self, state, draw_arrow_for_move=None):
        board = state["board"]
        self.canvas.delete("all")
        light_color = "#EBECD0"
        dark_color = "#739552"
        
        for rank in range(8):
            for file in range(8):
                x1 = file * self.square_size
                y1 = (7 - rank) * self.square_size
                x2 = x1 + self.square_size
                y2 = y1 + self.square_size
                color = light_color if (file + rank) % 2 == 0 else dark_color
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline=color)
                
        last_move = state.get("last_move")
        if last_move:
            self.highlight_square(last_move.from_square, "#f5ec42")
            self.highlight_square(last_move.to_square, "#f5ec42")
            
        for rank in range(8):
            for file in range(8):
                piece = board.piece_at(chess.square(file, rank))
                if piece:
                    piece_key = ("w" if piece.color == chess.WHITE else "b") + piece.symbol().upper()
                    img = self.piece_images.get(piece_key)
                    if img:
                        x1 = file * self.square_size
                        y1 = (7 - rank) * self.square_size
                        self.canvas.create_image(x1, y1, image=img, anchor=tk.NW)
                        
        class_color = state.get("class_color")
        class_text = state.get("class_text")
        if last_move and class_color and class_text:
            to_sq = last_move.to_square
            file = chess.square_file(to_sq)
            rank = chess.square_rank(to_sq)
            x1 = file * self.square_size
            y1 = (7 - rank) * self.square_size
            r = 16
            cx = x1 + self.square_size - r - 4
            cy = y1 + self.square_size - r - 4
            self.canvas.create_oval(cx, cy, cx+r, cy+r, fill=class_color, outline="black", width=1)
            self.canvas.create_text(cx+r/2, cy+r/2, text=class_text, fill="white", font=("Arial", 9, "bold"))
            
        if draw_arrow_for_move:
            self.draw_arrow(draw_arrow_for_move.from_square, draw_arrow_for_move.to_square, "#1e8e3e")

    def draw_arrow(self, from_sq, to_sq, color="#1e8e3e"):
        f_file = chess.square_file(from_sq)
        f_rank = chess.square_rank(from_sq)
        t_file = chess.square_file(to_sq)
        t_rank = chess.square_rank(to_sq)
        x1 = f_file * self.square_size + self.square_size / 2
        y1 = (7 - f_rank) * self.square_size + self.square_size / 2
        x2 = t_file * self.square_size + self.square_size / 2
        y2 = (7 - t_rank) * self.square_size + self.square_size / 2
        self.canvas.create_line(x1, y1, x2, y2, arrow=tk.LAST, width=6, fill=color, arrowshape=(15, 15, 10))

    def highlight_square(self, square, color):
        file = chess.square_file(square)
        rank = chess.square_rank(square)
        x1 = file * self.square_size
        y1 = (7 - rank) * self.square_size
        x2 = x1 + self.square_size
        y2 = y1 + self.square_size
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")

    def update_board_ui(self):
        if 0 <= self.current_idx < len(self.game_states):
            state = self.game_states[self.current_idx]
            self.draw_board(state)
            self.draw_eval_bar(state["eval"])
            self.lbl_move_info.config(text=state["msg"])
            
    def stop_all_playback(self):
        self.auto_play_active = False
        self.auto_play_var.set(False)
        self.stop_simulation()
        
    def stop_simulation(self):
        if self.simulating:
            self.simulating = False
            self.btn_what_if.config(text="What If Best?")

    def return_to_game(self):
        """Stops simulation and draws the board back to the actual game position."""
        self.stop_all_playback()
        self.update_board_ui()

    def restart_game(self):
        self.stop_all_playback()
        if len(self.game_states) > 0:
            self.current_idx = 0
            self.update_board_ui()
            
    def next_move(self):
        self.stop_all_playback()
        if self.current_idx < len(self.game_states) - 1:
            self.current_idx += 1
            self.update_board_ui()

    def last_move(self):
        self.stop_all_playback()
        if self.current_idx > 0:
            self.current_idx -= 1
            self.update_board_ui()

    def toggle_auto_play(self):
        self.stop_simulation()
        self.auto_play_active = self.auto_play_var.get()
        if self.auto_play_active:
            self.run_auto_play()

    def run_auto_play(self):
        if self.auto_play_active:
            if self.current_idx < len(self.game_states) - 1:
                self.current_idx += 1
                self.update_board_ui()
                self.root.after(int(self.auto_play_speed * 1000), self.run_auto_play)
            elif not self.analyzing_complete:
                self.root.after(500, self.run_auto_play)
            else:
                self.auto_play_active = False
                self.auto_play_var.set(False)

    def show_best_move(self):
        self.stop_all_playback()
        if 0 <= self.current_idx < len(self.game_states):
            state = self.game_states[self.current_idx]
            best_move = state.get("best_move")
            if best_move:
                self.draw_board(state, draw_arrow_for_move=best_move)
                san = state["board"].san(best_move)
                self.lbl_move_info.config(text=f"Engine suggests: {san}")
            else:
                self.lbl_move_info.config(text="No best move found for this position.")

    def toggle_what_if(self):
        if not self.simulating:
            if 0 <= self.current_idx < len(self.game_states):
                self.auto_play_active = False
                self.auto_play_var.set(False)
                
                self.simulating = True
                self.btn_what_if.config(text="Pause Sim")
                threading.Thread(target=self.run_simulation, daemon=True).start()
        else:
            self.stop_simulation()

    def run_simulation(self):
        if not self.stockfish_path: return
        try:
            sim_engine = chess.engine.SimpleEngine.popen_uci(self.stockfish_path)
        except:
            self.log("Failed to start engine for simulation.")
            self.stop_simulation()
            return
            
        sim_board = self.game_states[self.current_idx]["board"].copy()
        
        while self.simulating:
            if sim_board.is_game_over():
                break
                
            info = sim_engine.analyse(sim_board, chess.engine.Limit(depth=12))
            best_move = info.get("pv", [None])[0]
            if not best_move:
                break
            
            # FIX: Get SAN BEFORE pushing the move to the board
            san = sim_board.san(best_move)
            sim_board.push(best_move)
            
            eval_score = info["score"].white()
            if eval_score.is_mate():
                eval_val = 10.0 if eval_score.mate() > 0 else -10.0
            else:
                eval_val = eval_score.score(mate_score=10000) / 100.0
                
            sim_state = {
                "board": sim_board.copy(),
                "eval": eval_val,
                "msg": f"Simulating Best: {san}",
                "last_move": best_move,
                "class_color": "#1e8e3e",
                "class_text": "!"
            }
            
            self.root.after(0, lambda s=sim_state: self.draw_board(s))
            self.root.after(0, lambda v=eval_val: self.draw_eval_bar(v))
            self.root.after(0, lambda m=sim_state["msg"]: self.lbl_move_info.config(text=m))
            
            time.sleep(1.0)
            
        sim_engine.quit()
        self.stop_simulation()

    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Auto-Play Settings")
        win.geometry("300x150")
        win.transient(self.root)
        ttk.Label(win, text="Auto Play Speed (seconds per move):").pack(pady=10)
        self.speed_var = tk.DoubleVar(value=self.auto_play_speed)
        scale = ttk.Scale(win, from_=0.1, to=2.0, variable=self.speed_var, orient=tk.HORIZONTAL)
        scale.pack(fill=tk.X, padx=20)
        val_label = ttk.Label(win, text=f"{self.auto_play_speed:.1f}s")
        val_label.pack()
        def update_val(*args): val_label.config(text=f"{self.speed_var.get():.1f}s")
        self.speed_var.trace_add("write", update_val)
        def save():
            self.auto_play_speed = self.speed_var.get()
            win.destroy()
        ttk.Button(win, text="Save", command=save).pack(pady=10)

    def auto_find_stockfish(self):
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        arshiya_folder = os.path.join(desktop_path, "Arshiya")
        if os.path.exists(arshiya_folder):
            for root, dirs, files in os.walk(arshiya_folder):
                for file in files:
                    if "stockfish" in file.lower() and not file.endswith((".txt", ".md", ".pdf", ".zip", ".png")):
                        self.stockfish_path = os.path.join(root, file)
                        self.root.after(0, lambda: self.engine_status.config(text=f"Stockfish: {self.stockfish_path}", foreground="green"))
                        self.log("Automatically found Stockfish!")
                        return
        self.root.after(0, lambda: self.engine_status.config(text="Stockfish: Not found. Click Browse.", foreground="red"))

    def browse_stockfish(self):
        filepath = filedialog.askopenfilename(title="Select Stockfish Executable", filetypes=[("All Files", "*.*"), ("Executables", "*.exe")])
        if filepath:
            self.stockfish_path = filepath
            self.engine_status.config(text=f"Stockfish: {filepath}", foreground="green")
            self.log("Stockfish path set manually.")

    def start_fetch_thread(self):
        self.fetch_btn.config(state=tk.DISABLED)
        self.game_listbox.delete(0, tk.END)
        self.game_pgns.clear()
        self.notebook.select(0)
        self.log("Fetching latest games from Chess.com...")
        threading.Thread(target=self.fetch_games, daemon=True).start()

    def fetch_games(self):
        username = self.username_entry.get().strip().lower()
        if not username:
            messagebox.showerror("Error", "Please enter a username.")
            self.fetch_btn.config(state=tk.NORMAL)
            return
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        archive_url = f"https://api.chess.com/pub/player/{username}/games/archives"
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.log(f"Attempting to connect to Chess.com (Attempt {attempt + 1})...")
                res = requests.get(archive_url, headers=headers, timeout=15)
                break
            except requests.exceptions.ConnectionError:
                self.log("Connection dropped. Retrying in 3 seconds...")
                time.sleep(3)
        else:
            self.log("Failed to connect to Chess.com.")
            self.fetch_btn.config(state=tk.NORMAL)
            return
        if res.status_code != 200:
            self.log(f"Failed to find user '{username}'.")
            self.fetch_btn.config(state=tk.NORMAL)
            return
        archives = res.json().get("archives", [])
        if not archives:
            self.log(f"No games found for user '{username}'.")
            self.fetch_btn.config(state=tk.NORMAL)
            return
        latest_url = archives[-1]
        self.log("Found games. Fetching latest month...")
        try:
            games_res = requests.get(latest_url, headers=headers, timeout=15)
            games = games_res.json().get("games", [])
        except Exception as e:
            self.log(f"Error downloading games: {e}")
            self.fetch_btn.config(state=tk.NORMAL)
            return
        if not games:
            self.log("No games found.")
            self.fetch_btn.config(state=tk.NORMAL)
            return
        processed_games = []
        for game in games:
            pgn = game.get("pgn")
            if not pgn: continue
            pgn_io = io.StringIO(pgn)
            pgn_game = chess.pgn.read_game(pgn_io)
            if not pgn_game: continue
            headers_pgn = pgn_game.headers
            white = headers_pgn.get("White", "?")
            black = headers_pgn.get("Black", "?")
            result = headers_pgn.get("Result", "*")
            date_str = headers_pgn.get("Date", "????.??.??")
            time_str = headers_pgn.get("StartTime", "??:??:??")
            time_class = game.get("time_class", "?").capitalize()
            outcome = "Draw"
            if result == "1-0":
                if white.lower() == username: outcome = "Won"
                else: outcome = "Lost"
            elif result == "0-1":
                if black.lower() == username: outcome = "Won"
                else: outcome = "Lost"
            elif result == "1/2-1/2":
                outcome = "Draw"
            else:
                outcome = "Unfinished"
            sort_key = f"{date_str} {time_str}"
            clean_date = date_str.replace(".", "-")
            clean_time = time_str.split(".")[0]
            white_fmt = f"{white[:15]:<15}"
            black_fmt = f"{black[:15]:<15}"
            display_text = f"[{outcome:^4}] [{time_class:^6}] {clean_date} {clean_time} | W: {white_fmt} | B: {black_fmt}"
            processed_games.append((sort_key, pgn, display_text))
        processed_games.sort(key=lambda x: x[0], reverse=True)
        for sort_key, pgn, display_text in processed_games:
            self.game_pgns.append(pgn)
            self.root.after(0, lambda dt=display_text: self.game_listbox.insert(tk.END, dt))
        self.log(f"Loaded {len(self.game_pgns)} games. Double-click one to analyze!")
        self.fetch_btn.config(state=tk.NORMAL)

    def start_analysis_thread(self, event=None):
        if not self.stockfish_path:
            messagebox.showerror("Error", "Stockfish not found! Let it auto-search or click Browse.")
            return
        selection = self.game_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a game from the list first.")
            return
        idx = selection[0]
        pgn_string = self.game_pgns[idx]
        self.analyze_btn.config(state=tk.DISABLED)
        self.notebook.select(1)
        self.stop_all_playback()
        self.log("\n--- Starting Analysis ---")
        threading.Thread(target=self.analyze_game, args=(pgn_string,), daemon=True).start()

    def analyze_game(self, pgn_string):
        pgn_io = io.StringIO(pgn_string)
        game = chess.pgn.read_game(pgn_io)
        if game is None:
            self.log("Could not parse PGN.")
            self.analyze_btn.config(state=tk.NORMAL)
            return
        board = game.board()
        white = game.headers.get("White", "?")
        black = game.headers.get("Black", "?")
        self.log(f"Analyzing: {white} vs {black}")
        self.game_states = []
        self.analyzing_complete = False
        
        try:
            engine = chess.engine.SimpleEngine.popen_uci(self.stockfish_path)
        except Exception as e:
            self.log(f"Failed to start Stockfish. Error: {e}")
            self.analyze_btn.config(state=tk.NORMAL)
            return
            
        # Analyze Initial Position
        info_start = engine.analyse(board, chess.engine.Limit(depth=12))
        best_move_start = info_start.get("pv", [None])[0]
        eval_start = info_start["score"].white()
        start_eval_val = eval_start.score(mate_score=10000) / 100.0 if not eval_start.is_mate() else (10.0 if eval_start.mate() > 0 else -10.0)
        
        start_state = {
            "board": board.copy(), 
            "eval": start_eval_val, 
            "msg": "Game Start", 
            "last_move": None, 
            "class_color": None, 
            "class_text": None, 
            "best_move": best_move_start
        }
        self.game_states.append(start_state)
        self.current_idx = 0
        self.root.after(0, lambda: self.update_board_ui())
        
        move_number = 1
        
        for move in game.mainline_moves():
            info = engine.analyse(board, chess.engine.Limit(depth=12))
            eval_before = info["score"].white()
            best_move = info.get("pv", [None])[0]
            
            is_white_turn = board.turn == chess.WHITE
            mover = "White" if is_white_turn else "Black"
            played_san = board.san(move)
            best_san = board.san(best_move) if best_move else "N/A"
            
            board.push(move)
            
            info_after = engine.analyse(board, chess.engine.Limit(depth=12))
            eval_after = info_after["score"].white()
            new_best_move = info_after.get("pv", [None])[0] # Best move for the NEW board
            
            if eval_after.is_mate():
                score_val = 10.0 if eval_after.mate() > 0 else -10.0
            else:
                score_val = eval_after.score(mate_score=10000) / 100.0
                
            if is_white_turn: 
                eval_drop = eval_before.score(mate_score=10000) - eval_after.score(mate_score=10000)
            else: 
                eval_drop = eval_after.score(mate_score=10000) - eval_before.score(mate_score=10000)
                
            class_color = None
            class_text = None
            class_name = "Good"
            
            if move_number <= 8 and abs(eval_before.score(mate_score=10000)) < 50 and eval_drop < 30:
                class_color = "#a0a0a0"
                class_text = ""
                class_name = "Book"
            elif move == best_move:
                class_color = "#1e8e3e"
                class_text = "!"
                class_name = "Best"
            elif eval_drop < 40:
                class_color = "#5cb85c"
                class_text = "!"
                class_name = "Excellent"
            elif eval_drop < 90:
                class_color = "#96c896"
                class_text = ""
                class_name = "Good"
            elif eval_drop < 150:
                class_color = "#ffcc00"
                class_text = "?!"
                class_name = "Inaccuracy"
            elif eval_drop < 350:
                class_color = "#ff9900"
                class_text = "?"
                class_name = "Mistake"
            else:
                class_color = "#ff3333"
                class_text = "??"
                class_name = "Blunder"
                
            msg = f"Move {move_number} ({mover}): {played_san} ({class_name})"
            if class_name not in ["Best", "Book"] and best_san != "N/A":
                msg += f" -> Engine: {best_san}"
                
            state = {
                "board": board.copy(),
                "eval": score_val,
                "msg": msg,
                "last_move": move,
                "class_color": class_color,
                "class_text": class_text,
                "best_move": new_best_move  # Store the correct best move for this state!
            }
            self.game_states.append(state)
            self.log(msg)
            
            if self.current_idx == len(self.game_states) - 2:
                self.current_idx += 1
                self.root.after(0, lambda: self.update_board_ui())
                
            if is_white_turn:
                move_number += 1
                
        engine.quit()
        self.analyzing_complete = True
        self.log("--- Analysis Complete ---")
        self.analyze_btn.config(state=tk.NORMAL)


if __name__ == "__main__":
    root = tk.Tk()
    app = ChessAnalyzerApp(root)
    root.mainloop()
