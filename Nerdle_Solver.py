import random
from collections import Counter
import tkinter as tk
from tkinter import messagebox


START_GUESS = "3*4+5=17" 
"""
Solver uses a hardcoded starting guess
This is the starter I use when I solve the puzzles, so I figured it's a pretty good starter
main thing is you don't have repeating symbols and numbers in the starter so you can extract as much informaton as possible form the first guess
"""


def startup(filename="NerdleClassicRestricted.txt"):
    """
    Loads the list of all valid Nerdle equations from a text file.
    Returns them as a list of strings.
    """
    answers = []

    try:
        with open(filename, "r") as f:
            for line in f:
                eq = line.strip()
                if eq:
                    answers.append(eq)
    except FileNotFoundError:
        print(f"Error: Could not find file '{filename}'.")
        return []

    return answers

def form_key(eq):
    """
    Return a 'form key' that describes the structural shape of an equation,
    ignoring which specific digits are used.

    Example:
        '12+3=15' -> 'DD+D=DD'
        '9*8=72'  -> 'D*D=DD'

    D = digit
    + - * / and = are kept as-is.
    """
    key_chars = []
    for ch in eq:
        if ch.isdigit():
            key_chars.append('D')
        else:
            key_chars.append(ch)
    return "".join(key_chars)



def compute_feedback(secret, guess):
    """
    Computes Nerdle-style feedback for a given secret and guess.

    Feedback rules:
      G = Green  (correct character in the correct position)
      P = Purple (character appears in the secret but in a different position)
      B = Black  (character does not appear enough times to be matched; 
                  this includes true absence AND overuse of duplicates)

    This function exactly mirrors Wordle/Nerdle logic:
      1. First mark all greens.
      2. Then mark purples only if an unmatched copy of that character exists.
      3. All remaining positions stay black.
    """

    length = len(secret)

    # Start by assuming all positions are black.
    # We'll overwrite entries with 'G' or 'P' as we find matches.
    result = ["B"] * length

    # Convert strings to lists for easier index-based access.
    secret_chars = list(secret)
    guess_chars = list(guess)

    # Track whether positions in secret/guess have already been matched.
    secret_used = [False] * length
    guess_used  = [False] * length

    # -------------------------------------------------------------
    # PASS 1: Mark all GREENS (correct char, correct position)
    # -------------------------------------------------------------
    for i in range(length):
        if guess_chars[i] == secret_chars[i]:
            result[i] = "G"        # Mark green
            secret_used[i] = True  # Secret char at this position is taken
            guess_used[i]  = True  # Guess char at this position is matched

    # -------------------------------------------------------------
    # PASS 2: Mark PURPLES (correct char, wrong position)
    # -------------------------------------------------------------
    # For each unmatched guess position, try to pair it with any
    # unmatched matching character in the secret.
    for i in range(length):

        # Skip positions that were already matched as green
        if guess_used[i]:
            continue

        gch = guess_chars[i]  # character from the guess at position i

        # Look for an unused matching character in the secret
        for j in range(length):

            # We can only match secret positions that:
            #   1. Haven't been used yet
            #   2. Contain the same character
            if not secret_used[j] and secret_chars[j] == gch:
                result[i] = "P"        # Mark purple
                secret_used[j] = True  # This secret char is now matched
                guess_used[i]  = True  # This guess char is now matched
                break
        # If no match was found, result[i] simply stays "B".

    # Convert list back to string
    return "".join(result)


def filter_candidates(candidates, guess, feedback_str):
    """
    Given a list of candidate equations, a guess, and the feedback pattern
    (G/P/B string), return the subset of candidates that would produce
    exactly the same feedback if they were the secret.
    """
    new_candidates = []
    for secret in candidates:
        fb = compute_feedback(secret, guess)
        if fb == feedback_str:
            new_candidates.append(secret)
    return new_candidates


def get_feedback_from_user():
    """
    Ask the user to type an 8-character string of G/P/B (green, purple, black)
    and validate it.
    """
    while True:
        fb = input("Enter feedback (8 letters using G, P, B): ").strip().upper()
        if len(fb) == 8 and all(c in "GPB" for c in fb):
            return fb
        print("Invalid feedback. Please enter exactly 8 characters of G, P, or B.")


def choose_guess(candidates, turn_number, seen_symbols):
    """
    Choose the next guess.

    Heuristic:
      - Turn 1: use a fixed starting guess if it's in the candidate list.
      - While the candidate set is large:
          * prefer guesses whose "form" is common among remaining candidates
            (i.e., likely equation shape),
          * AND that use many symbols we haven't seen yet,
          * AND that have good overall variety (distinct symbols).
      - When the candidate set is small:
          * stop being fancy and just pick randomly among candidates.
            At that point, all remaining forms are very similar anyway.
    """

    # -------------------------------
    # First move: use your hard-coded start if possible.
    # -------------------------------
    if turn_number == 1:
        if START_GUESS in candidates:
            return START_GUESS
        # Fall back to a random candidate if START_GUESS isn't valid.
        return random.choice(candidates)

    # -------------------------------
    # Late-game: when few candidates remain, just guess among them.
    # -------------------------------
    if len(candidates) <= 10:
        return random.choice(candidates)

    # -------------------------------
    # Early / mid-game: 
    #
    # 1. Compute how frequent each "form" is in the remaining candidates.
    # 2. For each candidate, compute:
    #       - form_prob  = how common its form is
    #       - new_symbols = how many symbols we haven't seen before
    #       - distinct    = how many distinct symbols it uses total
    # 3. Combine these into a score and pick a max-scoring candidate.
    # -------------------------------
    total = len(candidates)
    form_counts = Counter(form_key(eq) for eq in candidates)  # form_key -> count

    best_score = float("-inf")
    best_eqs = []

    for eq in candidates:
        chars = set(eq)
        distinct = len(chars)

        # Symbols in this equation that have not appeared in any previous guesses.
        new_symbols = len(chars - seen_symbols)

        # How likely is this equation "shape" among remaining candidates?
        fk = form_key(eq)
        form_prob = form_counts[fk] / total  # between 0 and 1

        # Weighting:
        #   - form_prob: favor likely equation layouts (shape)
        #   - new_symbols: favor testing unseen symbols (information gain)
        #   - distinct: favor overall variety
        score = 3.0 * form_prob + 2.0 * new_symbols + 1.0 * distinct

        if score > best_score:
            best_score = score
            best_eqs = [eq]
        elif score == best_score:
            best_eqs.append(eq)

    # Break ties randomly among the best-scoring equations.
    return random.choice(best_eqs) if best_eqs else random.choice(candidates)



def solve_puzzle(all_answers):
    """
    Interactive solve mode.

    The user plays Nerdle in the browser, and after each guess,
    manually enters the feedback (G/P/B). The solver maintains
    a set of candidate equations consistent with all feedback
    seen so far and proposes the next guess.
    """

    # Start with the full answer list as possible candidates.
    # This list will shrink after each guess based on feedback.
    candidates = all_answers[:]

    # Guess counter (1-based, like the actual game)
    turn = 1

    # Set of all symbols (digits/operators/=) that have appeared
    # in previous guesses. Used by the heuristic to reward
    # guesses that introduce new information.
    seen_symbols = set()

    print("\nStarting a new Nerdle solve...")
    print(f"Initial candidate count: {len(candidates)}")

    while True:
        # If no candidates remain, the feedback entered by the user
        # must have been inconsistent with Nerdle rules.
        if not candidates:
            print("No candidates remain. Something went wrong with the feedback.")
            return

        # Choose the next guess using the heuristic
        guess = choose_guess(candidates, turn, seen_symbols)

        print(f"\nGuess {turn}: {guess}")
        print("Type this into Nerdle, then enter the feedback here:")

        # Record symbols used in this guess so future guesses
        # can prioritize unseen symbols.
        seen_symbols |= set(guess)

        # User enters the Nerdle feedback (G/P/B pattern)
        feedback_str = get_feedback_from_user()

        # If all positions are green, the puzzle is solved
        if feedback_str == "G" * len(guess):
            print(f"Solved in {turn} guesses! 🎉")
            return

        # Filter the candidate list to only equations that would
        # produce the same feedback pattern for this guess.
        candidates = filter_candidates(candidates, guess, feedback_str)

        print(f"Remaining candidate count: {len(candidates)}")

        # Move on to the next guess
        turn += 1


def simulate_single_game(secret, all_answers, verbose=False):
    """
    Simulate solving a single Nerdle puzzle automatically.

    - `secret` is the true answer.
    - No user input is required.
    - Feedback is computed internally using compute_feedback().
    - Returns the number of guesses needed to solve the puzzle,
      or None if something goes wrong.
    """

    # Start with all answers as possible candidates
    candidates = all_answers[:]
    turn = 1

    # Track which symbols have appeared in guesses so far
    seen_symbols = set()

    if verbose:
        print(f"\nSimulating game with secret: {secret}")

    while True:
        # This should never happen if the solver is correct,
        # since the secret is guaranteed to be in all_answers.
        if not candidates:
            if verbose:
                print("Error: no candidates left. Aborting this simulation.")
            return None

        # Choose the next guess
        guess = choose_guess(candidates, turn, seen_symbols)

        # Update seen symbols
        seen_symbols |= set(guess)

        # Compute Nerdle-style feedback automatically
        feedback_str = compute_feedback(secret, guess)

        if verbose:
            print(
                f"Guess {turn}: {guess} -> {feedback_str} "
                f"(candidates left: {len(candidates)})"
            )

        # If solved, return the number of guesses used
        if feedback_str == "G" * len(secret):
            return turn

        # Narrow the candidate list based on feedback
        candidates = filter_candidates(candidates, guess, feedback_str)

        turn += 1


def simulate_many_games(all_answers, num_games=100):
    """
    Run the solver on a number of randomly chosen secrets.

    This provides a quick estimate of solver performance
    without running a full population-wide simulation.
    """

    if not all_answers:
        print("No answers loaded; cannot run simulation.")
        return

    results = []

    for game_idx in range(1, num_games + 1):
        # Choose a random secret from the answer list
        secret = random.choice(all_answers)

        # Simulate solving it
        guesses = simulate_single_game(secret, all_answers, verbose=False)

        if guesses is None:
            print(f"Game {game_idx}: simulation failed (no candidates).")
            continue

        results.append(guesses)

    if not results:
        print("No successful simulations.")
        return

    # Aggregate statistics
    avg = sum(results) / len(results)
    best = min(results)
    worst = max(results)

    print(f"\nSimulation over {len(results)} random games:")
    print(f"  Average guesses : {avg:.3f}")
    print(f"  Best game       : {best} guesses")
    print(f"  Worst game      : {worst} guesses")


def simulate_all_answers(all_answers):
    """
    Run the solver on EVERY possible answer in the list.

    This computes the exact (not sampled) performance statistics:
    average guesses, best/worst case, and full distribution.
    """

    if not all_answers:
        print("No answers loaded; cannot run full simulation.")
        return

    results = []

    total_games = len(all_answers)
    print(f"\nRunning full simulation on all {total_games} answers...")

    for i, secret in enumerate(all_answers, start=1):
        guesses = simulate_single_game(secret, all_answers, verbose=False)

        if guesses is None:
            print(f"Game {i}: simulation failed for secret {secret}.")
        else:
            results.append(guesses)

        # Periodic progress update so the user knows it's running
        if i % 100 == 0 or i == total_games:
            print(f"  Simulated {i}/{total_games} games...")

    if not results:
        print("No successful simulations.")
        return

    # Aggregate statistics
    avg = sum(results) / len(results)
    best = min(results)
    worst = max(results)

    print("\nFull simulation results:")
    print(f"  Games simulated : {len(results)}")
    print(f"  Average guesses : {avg:.3f}")
    print(f"  Best game       : {best} guesses")
    print(f"  Worst game      : {worst} guesses")

    # Count how many games finished in N guesses
    dist = Counter(results)

    print("\nGuess count distribution:")
    for guesses in sorted(dist.keys()):
        count = dist[guesses]
        pct = 100.0 * count / len(results)
        print(f"  {guesses} guesses: {count} games ({pct:.2f}%)")

class NerdleGUI:
    """
    A simple GUI for the Nerdle solver.

    - Displays a 6x8 grid (6 guesses, 8 characters each).
    - The solver fills each row with the suggested equation.
    - The user clicks cells in the current row to cycle colors:
        Black -> Purple -> Green -> Black -> ...
    - Pressing Enter (or clicking "Submit Feedback") sends the G/P/B pattern
      to the solver, which then filters candidates and chooses the next guess.
    """

    def __init__(self, root, all_answers, switch_flag):
        """
        `switch_flag` is a mutable dict used to signal that the user
        wants to switch to CLI simulation mode: {"value": False/True}
        """
        self.root = root
        self.root.title("Nerdle Solver")

        self.all_answers = all_answers
        self.switch_flag = switch_flag  # shared flag with outer code

        # Solver state
        self.max_rows = 6          # like Nerdle: up to 6 guesses
        self.cols = 8              # 8-character equations
        self.candidates = []
        self.turn = 1              # 1-based guess number
        self.seen_symbols = set()
        self.current_row = 0       # 0-based index into grid rows
        self.current_guess = ""    # equation string for current row
        self.current_feedback = ["B"] * self.cols  # G/P/B for current row

        # GUI elements
        self.cells = []            # 2D list: [row][col] -> tk.Button
        self.info_label = None
        self.candidate_label = None

        self._build_widgets()
        self._start_new_game()

    def _update_window_title(self, extra_message=""):
        """
        Update the window title to show solver state and candidates left.
        This is guaranteed visible.
        """
        cand = len(self.candidates) if self.candidates is not None else 0
        title = f"Nerdle Solver – Candidates left: {cand}"
        if extra_message:
            title += f" – {extra_message}"
        self.root.title(title)

    def _build_widgets(self):
        """
        Create all GUI widgets:

        Row 0 (in the same frame as the tile grid):
          - info label (left)
          - candidate count label (middle)
          - restart button (right)

        Rows 1..max_rows: the 6x8 tile buttons.

        Bottom: Submit + Switch buttons.
        """

        # === One main frame that holds both header and grid ===
        grid_frame = tk.Frame(self.root, bg="gray20")
        grid_frame.pack(padx=10, pady=10)

        # Row 0: header row

        # Status / info label on the left (cols 0-3)
        self.info_label = tk.Label(
            grid_frame,
            text="Nerdle Solver - GUI Mode",
            font=("Helvetica", 12),
            bg="gray20",
            fg="white",
        )
        self.info_label.grid(row=0, column=0, columnspan=4,
                             sticky="w", padx=5, pady=(0, 5))

        # Candidate count in the middle
        self.candidate_label = tk.Label(
            grid_frame,
            text="Candidates left: --",
            font=("Helvetica", 12),
            bg="gray20",
            fg="white",
        )
        self.candidate_label.grid(row=0, column=4, columnspan=3,
                                  sticky="w", padx=5, pady=(0, 5))

        # Restart button on the right 
        restart_btn = tk.Button(
            grid_frame,
            text="Restart",
            font=("Helvetica", 10),
            command=self._start_new_game
        )
        restart_btn.grid(row=0, column=7, sticky="e", padx=5, pady=(0, 5))

        # Row 1..max_rows: the tile buttons
        for r in range(self.max_rows):
            row_cells = []
            grid_row = r + 1  # shift tiles down by one row

            for c in range(self.cols):
                btn = tk.Button(
                    grid_frame,
                    text="",
                    width=4,
                    height=2,
                    font=("Helvetica", 16, "bold"),
                    bg="black",
                    fg="white",
                    relief="raised",
                )
                btn.grid(row=grid_row, column=c, padx=3, pady=3)
                btn.configure(command=lambda rr=r, cc=c: self._on_cell_click(rr, cc))
                row_cells.append(btn)

            self.cells.append(row_cells)

         # === Bottom buttons: submit + switch to CLI ===
        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(pady=10)

        submit_btn = tk.Button(
            bottom_frame,
            text="Submit Feedback",
            font=("Helvetica", 12),
            command=self._on_submit
        )
        submit_btn.grid(row=0, column=0, padx=10)

        switch_btn = tk.Button(
            bottom_frame,
            text="Switch to Simulation Mode (Command Line)",
            font=("Helvetica", 12),
            command=self._switch_to_cli
        )
        switch_btn.grid(row=0, column=1, padx=10)

        # Bind Enter/Return key to submit feedback
        self.root.bind("<Return>", lambda event: self._on_submit())

    def _start_new_game(self):
        self.candidates = self.all_answers[:]
        self.turn = 1
        self.seen_symbols = set()
        self.current_row = 0
        self.current_feedback = ["B"] * self.cols
        self.current_guess = ""

        # Clear grid text and colors
        for r in range(self.max_rows):
            for c in range(self.cols):
                self.cells[r][c]["text"] = ""
                self.cells[r][c]["bg"] = "black"
                self.cells[r][c]["activebackground"] = "black"
                self.cells[r][c]["highlightbackground"] = "black"

        if not self.candidates:
            self.info_label.config(text="No answers loaded.")
            self.candidate_label.config(text="Candidates left: 0")
            self._update_window_title("No answers loaded")
            return

        # Update labels
        self.info_label.config(text="New game started.")
        self.candidate_label.config(
            text=f"Candidates left: {len(self.candidates)}"
        )
        self._update_window_title("New game started")

        # Ask the solver for the first guess
        self._show_next_guess()

    def _show_next_guess(self):
        if not self.candidates:
            self.info_label.config(text="No candidates remain.")
            self.candidate_label.config(text="Candidates left: 0")
            self._update_window_title("No candidates remain")
            return

        # Show current turn and candidate count
        self.info_label.config(
            text=f"Turn {self.turn}: set feedback and submit."
        )
        self.candidate_label.config(
            text=f"Candidates left: {len(self.candidates)}"
        )
        self._update_window_title(f"Turn {self.turn}")

        guess = choose_guess(self.candidates, self.turn, self.seen_symbols)
        self.current_guess = guess
        self.current_feedback = ["B"] * self.cols

        for c, ch in enumerate(guess):
            btn = self.cells[self.current_row][c]
            btn["text"] = f"{ch}⬛"
            btn["bg"] = "black"
            btn["activebackground"] = "black"
            btn["highlightbackground"] = "black"

        self.seen_symbols |= set(guess)

    def _on_cell_click(self, row, col):
        """
        Handle clicks on grid cells.

        Only the current row is editable. Each click cycles color
        for that position: Black -> Purple -> Green -> Black, we show this through colored emoji squares
        """
        # Only allow editing the current guess row
        if row != self.current_row:
            return

        state = self.current_feedback[col]  # 'B', 'P', or 'G'

        if state == "B":
            new_state = "P"
            square = " 🟪"   # purple
        elif state == "P":
            new_state = "G"
            square = " 🟩"   # green
        else:  # 'G'
            new_state = "B"
            square = " ⬛"   # black

        self.current_feedback[col] = new_state

        btn = self.cells[row][col]

        # Extract the original character (first char of text)
        text = btn["text"]
        ch = text[0] if text else ""

        # Show character + colored square
        btn["text"] = f"{ch}{square}"

        btn.configure(
            bg="black",
            activebackground="black",
            highlightbackground="black",
        )

    def _on_submit(self):
        """
        Called when the user presses Enter or clicks "Submit Feedback".
        Converts the current feedback to a string and advances the solver.
        """
        if not self.current_guess:
            return  # No guess shown yet

        feedback_str = "".join(self.current_feedback)

        # If solved, show message and stop
        if feedback_str == "G" * len(self.current_guess):
            message = f"Solved in {self.turn} guesses! 🎉"
            messagebox.showinfo("Solved", message)
            self.info_label.config(text=message)
            self.candidate_label.config(text="Candidates left: 1")
            self._update_window_title(message)
            return

        # Filter candidates based on current guess and feedback
        new_candidates = filter_candidates(
            self.candidates,
            self.current_guess,
            feedback_str
        )

        if not new_candidates:
            messagebox.showwarning(
                "No candidates",
                "No candidates remain. Feedback may be inconsistent."
            )
            self.info_label.config(
                text="No candidates remain."
            )
            self.candidate_label.config(text="Candidates left: 0")
            self._update_window_title("No candidates remain")
            return

        self.candidates = new_candidates

        # Move to the next row / turn
        self.turn += 1
        self.current_row += 1

        if self.current_row >= self.max_rows:
            messagebox.showinfo(
                "Out of rows",
                "Reached maximum number of guesses."
            )
            self.info_label.config(text="Reached maximum number of guesses.")
            self.candidate_label.config(
                text=f"Candidates left: {len(self.candidates)}"
            )
            self._update_window_title("Reached maximum guesses")
            return

        # Show the next guess on the new row (this also refreshes labels)
        self._show_next_guess()

    def _switch_to_cli(self):
        """
        Called when the user clicks the 'Switch to Simulation Mode' button.

        Sets a shared flag so the outer code knows to launch the
        command-line simulation menu after the window closes, then
        destroys the GUI window.
        """
        self.switch_flag["value"] = True
        self.root.destroy()


def run_gui_solver(all_answers):
    if not all_answers:
        print("No answers loaded; cannot launch GUI.")
        return

    switch_flag = {"value": False}

    root = tk.Tk()
    app = NerdleGUI(root, all_answers, switch_flag)
    root.mainloop()

    if switch_flag["value"]:
        cli_simulation_menu(all_answers)


def cli_simulation_menu(all_answers):
    print(f"\nLoaded {len(all_answers)} Nerdle equations.")
    print("\nSimulation Commands:")
    print("  m = run simulation on random secrets")
    print("  a = run full simulation on ALL answers")
    print("  q = quit\n")

    while True:
        cmd = input("Command (m/a/q): ").strip().lower()

        if cmd == "m":
            num = input("How many random games to simulate? (default 100): ").strip()
            if num == "":
                num_games = 100
            else:
                try:
                    num_games = int(num)
                except ValueError:
                    print("Invalid number, defaulting to 100.")
                    num_games = 100
            simulate_many_games(all_answers, num_games=num_games)

        elif cmd == "a":
            simulate_all_answers(all_answers)

        elif cmd == "q":
            print("Exiting simulation mode.")
            break

        else:
            print("Unknown command. Type 'm', 'a', or 'q'.\n")


def main():
    all_answers = startup()

    if not all_answers:
        print("Startup failed — no answers loaded.")
        return

    run_gui_solver(all_answers)


if __name__ == "__main__":
    main()
