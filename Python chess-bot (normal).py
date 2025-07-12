
import tkinter as tk
from tkinter import messagebox
import chess
import chess.engine
import os

# Set your Stockfish path here
STOCKFISH_PATH = r"C:\Users\hp\OneDrive\Desktop\Chess bot\stockfish-windows-x86-64-avx2.exe"

SQUARE_SIZE = 60
BOARD_COLOR_1 = "#B58863"
BOARD_COLOR_2 = "#F0D9B5"

class ChessGUI:
    def undo_pair_move(self, event=None):
        # Undo last two moves (player and engine)
        moves_undone = 0
        for _ in range(2):
            if len(self.board.move_stack) > 0:
                self.board.pop()
                moves_undone += 1
        if moves_undone > 0:
            self.status.set(f"Undid last {moves_undone} move(s).")
            self.draw_board()
        else:
            self.status.set("No moves to undo.")
    # Store legal moves for the currently dragged piece
    legal_moves_for_drag = None
    def __init__(self, root):
        import os
        from tkinter import ttk
        self.root = root
        self.root.title("ChessBoard: Stockfish GUI")
        self.board = chess.Board()
        self.selected_square = None
        self.squares = {}

        # --- Evaluation bar ---
        self.eval_bar_height = 8 * SQUARE_SIZE
        self.eval_bar_width = 30
        self.eval_bar = tk.Canvas(self.root, width=self.eval_bar_width, height=self.eval_bar_height, bg="#222")
        self.eval_bar.pack(side=tk.LEFT, fill=tk.Y)
        self.eval_score = 0  # centipawns, positive = white is better

        # Menu bar
        self.menu = tk.Menu(self.root)
        self.root.config(menu=self.menu)
        self._add_menus()

        # Toolbar
        self.toolbar = tk.Frame(self.root, bd=1, relief=tk.RAISED)
        self._add_toolbar_buttons()
        self.flipped = False
        btn_white = tk.Button(self.toolbar, text="Play White vs Engine", command=self.play_white)
        btn_white.pack(side=tk.LEFT, padx=2, pady=2)
        btn_black = tk.Button(self.toolbar, text="Play Black vs Engine", command=self.play_black)
        btn_black.pack(side=tk.LEFT, padx=2, pady=2)
        btn_flip = tk.Button(self.toolbar, text="Flip Board", command=self.flip_board)
        btn_flip.pack(side=tk.LEFT, padx=2, pady=2)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        # Canvas with space for coordinates
        canvas_size = 8 * SQUARE_SIZE + 40
        self.canvas = tk.Canvas(self.root, width=canvas_size, height=canvas_size)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<ButtonPress-1>", self.on_drag_start)
        self.canvas.bind("<B1-Motion>", self.on_drag_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_drag_release)
        self.drag_data = {"piece": None, "start_square": None, "image_id": None}

        # Status bar
        self.status = tk.StringVar()
        self.status.set("Welcome to ChessBoard!")
        self.statusbar = tk.Label(self.root, textvariable=self.status, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Load piece images
        self.piece_images = {}
        piece_folder = os.path.join(os.path.dirname(__file__), "pieces")
        piece_map = {
            'P': 'wP.png', 'N': 'wN.png', 'B': 'wB.png', 'R': 'wR.png', 'Q': 'wQ.png', 'K': 'wK.png',
            'p': 'bP.png', 'n': 'bN.png', 'b': 'bB.png', 'r': 'bR.png', 'q': 'bQ.png', 'k': 'bK.png',
        }
        for symbol, filename in piece_map.items():
            path = os.path.join(piece_folder, filename)
            try:
                img = tk.PhotoImage(file=path)
                self.piece_images[symbol] = img
            except Exception as e:
                self.piece_images[symbol] = None

        self.engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        self.draw_board()
        # Bind left arrow key to undo_pair_move
        self.root.bind('<Left>', self.undo_pair_move)

    # --- Evaluation bar drawing ---
    def update_eval_bar(self):
        self.eval_bar.delete("all")
        bar_h = self.eval_bar_height
        bar_w = self.eval_bar_width

        # If mate is present, fill bar accordingly
        if hasattr(self, "mate_in") and self.mate_in is not None:
            if self.eval_score > 0:
                # White is mating: bar is all white
                white_h = bar_h
                black_h = 0
            else:
                # Black is mating: bar is all black
                white_h = 0
                black_h = bar_h
        else:

            # Clamp eval between -10 and +10 pawns for display
            eval_cp = max(min(self.eval_score, 1000), -1000)
            # Convert to 0..1 (1 = white winning, 0 = black winning)
            if eval_cp >= 1000:
                percent = 1.0
            elif eval_cp <= -1000:
                percent = 0.0
            else:
                percent = 0.5 + eval_cp / 2000.0

            white_h = int(bar_h * percent)
            black_h = bar_h - white_h

        # Draw white part (top)
        self.eval_bar.create_rectangle(0, 0, bar_w, white_h, fill="#fff", outline="")
        # Draw black part (bottom)
        self.eval_bar.create_rectangle(0, white_h, bar_w, bar_h, fill="#222", outline="")

        # Draw score text
        if hasattr(self, "mate_in") and self.mate_in is not None:
            # Mate
            text = f"M{self.mate_in}"
            color = "#f00"
        else:
            text = f"{self.eval_score/100:.2f}"
            color = "#000" if percent > 0.5 else "#fff"
        self.eval_bar.create_text(bar_w//2, bar_h//2, text=text, fill=color, font=("Arial", 12, "bold"))

    # --- Evaluate position and update bar ---
    def evaluate_position(self):
        # Use Stockfish to evaluate the current position
        info = self.engine.analyse(self.board, chess.engine.Limit(time=0.1))
        if info["score"].is_mate():
            # Use large value for mate, sign indicates who is winning
            mate = info["score"].relative.mate()
            if mate is not None:
                self.eval_score = 10000 if mate > 0 else -100000
                self.mate_in = abs(mate)
            else:
                self.eval.score = 0
                self.mate_in = None
        else:
            self.eval_score = info["score"].white().score(mate_score=10000)
            self.mate_in = None
        self.update_eval_bar()

    def play_white(self):
        self.board.reset()
        self.selected_square = None
        self.status.set("You play White. Your move.")
        self.draw_board()
        self.evaluate_position()

    def play_black(self):
        self.board.reset()
        self.selected_square = None
        self.status.set("You play Black. Engine thinking...")
        self.draw_board()
        self.evaluate_position()
        self.root.after(100, self.engine_move)
        

       
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Load piece images
        self.piece_images = {}
        piece_folder = os.path.join(os.path.dirname(__file__), "pieces")
        piece_map = {
            'P': 'wP.png', 'N': 'wN.png', 'B': 'wB.png', 'R': 'wR.png', 'Q': 'wQ.png', 'K': 'wK.png',
            'p': 'bP.png', 'n': 'bN.png', 'b': 'bB.png', 'r': 'bR.png', 'q': 'bQ.png', 'k': 'bK.png',
        }
        for symbol, filename in piece_map.items():
            path = os.path.join(piece_folder, filename)
            try:
                img = tk.PhotoImage(file=path)
                self.piece_images[symbol] = img
            except Exception as e:
                self.piece_images[symbol] = None

        self.draw_board()

    def flip_board(self):
        # Prevent multiple canvas/statusbar/image/engine re-initializations
        self.flipped = not self.flipped
        self.draw_board()



        # Canvas, status bar, images, and engine should only be initialized ONCE in __init__
    def on_drag_start(self, event):
        offset = 20
        x, y = event.x - offset, event.y - offset
        if x < 0 or y < 0 or x >= 8 * SQUARE_SIZE or y >= 8 * SQUARE_SIZE:
            return
        if self.flipped:
            file = 7 - (x // SQUARE_SIZE)
            rank = y // SQUARE_SIZE
        else:
            file = x // SQUARE_SIZE
            rank = 7 - (y // SQUARE_SIZE)
        square = chess.square(file, rank)
        piece = self.board.piece_at(square)
        if piece and piece.color == self.board.turn:
            self.drag_data["piece"] = piece.symbol()
            self.drag_data["start_square"] = square
            # Highlight legal moves for this piece
            self.legal_moves_for_drag = [move.to_square for move in self.board.legal_moves if move.from_square == square]
            # Draw floating image
            img = self.piece_images.get(piece.symbol())
            if img:
                self.drag_data["image_id"] = self.canvas.create_image(event.x, event.y, image=img, anchor="c", tags="drag")
            else:
                self.drag_data["image_id"] = self.canvas.create_text(event.x, event.y, text=piece.symbol().upper(), fill="black", font=("Arial", 32, "bold"), tags="drag")
        else:
            self.drag_data = {"piece": None, "start_square": None, "image_id": None}
            self.legal_moves_for_drag = None

    def on_drag_motion(self, event):
        # Redraw the board to clear the original piece from its square
        self.draw_board()
        # Draw the floating image at the new position
        if self.drag_data["piece"]:
            img = self.piece_images.get(self.drag_data["piece"])
            if img:
                self.drag_data["image_id"] = self.canvas.create_image(event.x, event.y, image=img, anchor="c", tags="drag")
            else:
                self.drag_data["image_id"] = self.canvas.create_text(event.x, event.y, text=self.drag_data["piece"].upper(), fill="black", font=("Arial", 32, "bold"), tags="drag")

    def on_drag_release(self, event):
        if self.drag_data["piece"] is None or self.drag_data["start_square"] is None:
            self._clear_drag()
            return
        offset = 20
        x, y = event.x - offset, event.y - offset
        if x < 0 or y < 0 or x >= 8 * SQUARE_SIZE or y >= 8 * SQUARE_SIZE:
            self._clear_drag()
            return
        if self.flipped:
            file = 7 - (x // SQUARE_SIZE)
            rank = y // SQUARE_SIZE
        else:
            file = x // SQUARE_SIZE
            rank = 7 - (y // SQUARE_SIZE)
        target_square = chess.square(file, rank)
        move = chess.Move(self.drag_data["start_square"], target_square)
        if move in self.board.legal_moves:
            san = self.board.san(move)
            self.board.push(move)
            self.selected_square = None
            self.status.set(f"Move played: {san}")
            self.draw_board()
            self.evaluate_position()
            self.root.after(100, self.engine_move)
        else:
            self.status.set("Illegal move.")
        self._clear_drag()
        self.legal_moves_for_drag = None
        self.draw_board()

    def _clear_drag(self):
        if self.drag_data["image_id"]:
            self.canvas.delete(self.drag_data["image_id"])
        self.drag_data = {"piece": None, "start_square": None, "image_id": None}
        self.legal_moves_for_drag = None

    def _add_menus(self):
        # Add menu categories and some placeholder commands
        file_menu = tk.Menu(self.menu, tearoff=0)
        file_menu.add_command(label="New Game", command=self.new_game)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        self.menu.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(self.menu, tearoff=0)
        edit_menu.add_command(label="Undo", command=self.undo_move)
        edit_menu.add_command(label="Redo", command=self.redo_move)
        self.menu.add_cascade(label="Edit", menu=edit_menu)

        self.menu.add_cascade(label="Search", menu=tk.Menu(self.menu, tearoff=0))
        self.menu.add_cascade(label="Moves", menu=tk.Menu(self.menu, tearoff=0))
        self.menu.add_cascade(label="Options", menu=tk.Menu(self.menu, tearoff=0))
        self.menu.add_cascade(label="Engine", menu=tk.Menu(self.menu, tearoff=0))
        self.menu.add_cascade(label="Help", menu=tk.Menu(self.menu, tearoff=0))
        self.menu.add_cascade(label="Developer", menu=tk.Menu(self.menu, tearoff=0))

    def _add_toolbar_buttons(self):
        # Add toolbar buttons (text only for now, can be replaced with icons)
        btn_new = tk.Button(self.toolbar, text="New", command=self.new_game)
        btn_new.pack(side=tk.LEFT, padx=2, pady=2)
        btn_undo = tk.Button(self.toolbar, text="Undo", command=self.undo_move)
        btn_undo.pack(side=tk.LEFT, padx=2, pady=2)
        btn_redo = tk.Button(self.toolbar, text="Redo", command=self.redo_move)
        btn_redo.pack(side=tk.LEFT, padx=2, pady=2)

    def new_game(self):
        self.board.reset()
        self.selected_square = None
        self.status.set("New game started.")
        self.draw_board()
        self.evaluate_position()

    def undo_move(self):
        if len(self.board.move_stack) > 0:
            self.board.pop()
            self.status.set("Move undone.")
            self.draw_board()
            self.evaluate_position()
        else:
            self.status.set("No move to undo.")

    def redo_move(self):
        # Placeholder: Redo not implemented
        self.status.set("Redo not implemented.")

    def draw_board(self):
        self.canvas.delete("all")
        offset = 20
        # Draw coordinates
        for i in range(8):
            # Files (a-h) at top only
            file_chr = chr(ord('a') + i)
            if self.flipped:
                file_chr = chr(ord('a') + (7 - i))
            self.canvas.create_text(offset + i * SQUARE_SIZE + SQUARE_SIZE // 2, offset // 2, text=file_chr, font=("Arial", 12))
            # Ranks (1-8) at left only
            rank_num = str(i + 1)
            if self.flipped:
                rank_num = str(8 - i)
            self.canvas.create_text(offset // 2, offset + (7 - i) * SQUARE_SIZE + SQUARE_SIZE // 2, text=rank_num, font=("Arial", 12))

        # Draw squares and pieces
        for rank in range(8):
            for file in range(8):
                draw_file = 7 - file if self.flipped else file
                draw_rank = rank if not self.flipped else 7 - rank
                x1 = offset + file * SQUARE_SIZE
                y1 = offset + (7 - rank) * SQUARE_SIZE
                x2 = x1 + SQUARE_SIZE
                y2 = y1 + SQUARE_SIZE
                color = BOARD_COLOR_1 if (draw_rank + draw_file) % 2 == 0 else BOARD_COLOR_2
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
                square = chess.square(draw_file, draw_rank)
                # Highlight legal moves for the dragged piece
                if self.legal_moves_for_drag and square in self.legal_moves_for_drag:
                    # Draw a light grey oval in the center of the square
                    cx = x1 + SQUARE_SIZE // 2
                    cy = y1 + SQUARE_SIZE // 2
                    r = SQUARE_SIZE // 7
                    self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#cccccc", outline="")
                # --- Hide the piece if it's being dragged ---
                if (
                    self.drag_data.get("piece") is not None and
                    self.drag_data.get("start_square") == square
                ):
                    continue  # Skip drawing the piece on its original square while dragging
                piece = self.board.piece_at(square)
                if piece:
                    self.draw_piece(x1, y1, piece.symbol())
        if self.selected_square is not None:
            file, rank = chess.square_file(self.selected_square), chess.square_rank(self.selected_square)
            if self.flipped:
                file = 7 - file
                rank = 7 - rank
            x1 = offset + file * SQUARE_SIZE
            y1 = offset + (7 - rank) * SQUARE_SIZE
            x2 = x1 + SQUARE_SIZE
            y2 = y1 + SQUARE_SIZE
            self.canvas.create_rectangle(x1, y1, x2, y2, outline="red", width=3)

    def draw_piece(self, x, y, symbol):
        img = self.piece_images.get(symbol)
        if img:
            self.canvas.create_image(
                x + SQUARE_SIZE // 2, y + SQUARE_SIZE // 2,
                image=img, anchor="c"
            )
        else:
            # fallback to text if image not found
            color = "black" if symbol.islower() else "white"
            self.canvas.create_text(
                x + SQUARE_SIZE // 2, y + SQUARE_SIZE // 2,
                text=symbol.upper(), fill=color, font=("Arial", 32, "bold")
            )

    def on_click(self, event):
        # Disable click-to-move if drag-and-drop is used
        pass

    def engine_move(self):
        if not self.board.is_game_over():
            result = self.engine.play(self.board, chess.engine.Limit(time=1.0))
            san = self.board.san(result.move)
            self.board.push(result.move)
            self.status.set(f"Engine move: {san}")
            self.draw_board()
            self.evaluate_position()
            if self.board.is_game_over():
                messagebox.showinfo("Game Over", self.board.result())
                self.status.set(f"Game Over: {self.board.result()}")

    def on_closing(self):
        self.engine.quit()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    gui = ChessGUI(root)
    root.protocol("WM_DELETE_WINDOW", gui.on_closing)
    root.mainloop()