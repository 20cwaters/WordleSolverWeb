from flask import Flask, render_template, request, jsonify, session
# Import your solver functions from solver_logic.py
from solver_logic import (
    load_past_words as solver_load_past_words,
    load_words as solver_load_words,
    filter_words as solver_filter_words,
    suggest_next_guess as solver_suggest_next_guess
)
import random # If still needed for initial suggestions

app = Flask(__name__)
app.secret_key = 'your_very_secret_key' # Important for session management!

# --- Helper function to initialize or get game state ---
def get_game_state():
    if 'possible_words' not in session:
        # Initialize
        session['past_words_loaded'] = list(solver_load_past_words()) # Store as list for JSON
        all_available_words = solver_load_words(past_words_to_exclude=set(session['past_words_loaded']))        
        session['all_words'] = all_available_words
        session['possible_words'] = list(all_available_words) # Store as list
        session['known_letters'] = [None] * 5
        session['present_letters'] = [] # Store set as list for JSON
        session['absent_letters'] = []  # Store set as list for JSON
        session['yellow_misplaced'] = [[] for _ in range(5)] # Store list of sets as list of lists
        session['guess_number'] = 1
        session['game_over'] = False
        session['solved'] = False
    # Convert lists back to sets where needed for solver logic
    present_letters_set = set(session['present_letters'])
    absent_letters_set = set(session['absent_letters'])
    yellow_misplaced_sets = [set(pos_list) for pos_list in session['yellow_misplaced']]

    return (
        session['possible_words'],
        session['known_letters'],
        present_letters_set,
        absent_letters_set,
        yellow_misplaced_sets,
        session['guess_number'],
        session['game_over'],
        session['solved']
    )

def update_session_state(possible_words, known_letters, present_letters_set, absent_letters_set, yellow_misplaced_sets, guess_number, game_over, solved):
    session['possible_words'] = possible_words
    session['known_letters'] = known_letters
    session['present_letters'] = sorted(list(present_letters_set)) # Store sorted list
    session['absent_letters'] = sorted(list(absent_letters_set))   # Store sorted list
    session['yellow_misplaced'] = [sorted(list(pos_set)) for pos_set in yellow_misplaced_sets]
    session['guess_number'] = guess_number
    session['game_over'] = game_over
    session['solved'] = solved
    session.modified = True # Ensure session is saved


@app.route('/')
def index():
    # Initialize or reset game state for a new visit to the main page
    session.clear() # Start fresh
    possible_words, known_letters, present_letters, absent_letters, yellow_misplaced, guess_number, game_over, solved = get_game_state()

    # Get initial suggestion
    # You might want to refine this starter logic
    starters = ["crane", "slate", "soare", "adieu", "trace"]
    valid_starters = [s for s in starters if s in possible_words]
    if valid_starters:
        suggested = random.choice(valid_starters)
    elif possible_words:
        suggested = solver_suggest_next_guess(possible_words)
    else:
        suggested = "N/A"

    initial_data = {
        "suggested_guess": suggested.upper() if suggested else "N/A",
        "possible_words_count": len(possible_words),
        "possible_words_sample": sorted(possible_words[:200]), # Send a sample
        "guess_number": guess_number,
        "known_letters_display": "".join([l.upper() if l else "_" for l in known_letters]),
        "present_letters_display": ", ".join(sorted([l.upper() for l in present_letters])) if present_letters else "None",
        "absent_letters_display": ", ".join(sorted([l.upper() for l in absent_letters])) if absent_letters else "None",
        "game_over": game_over,
        "solved": solved
    }
    return render_template('index.html', **initial_data)

@app.route('/submit_guess', methods=['POST'])
def submit_guess_route():
    data = request.get_json()
    user_guess = data.get('guess', '').lower()
    feedback_colors = data.get('feedback', '') # e.g., "GYXXY"

    possible_words, known_letters, present_letters, absent_letters, yellow_misplaced, guess_number, game_over, solved = get_game_state()

    if game_over or solved:
        return jsonify({
            "error": "Game is over.",
            "game_over": game_over,
            "solved": solved
        })

    if not user_guess or len(user_guess) != 5 or not user_guess.isalpha():
        return jsonify({"error": "Invalid guess."})
    if not feedback_colors or len(feedback_colors) != 5 or not all(c in "GYX" for c in feedback_colors):
        return jsonify({"error": "Invalid feedback string."})

    if feedback_colors == "GGGGG":
        solved = True
        game_over = True
        update_session_state(possible_words, known_letters, present_letters, absent_letters, yellow_misplaced, guess_number, game_over, solved)
        return jsonify({
            "message": f"Congratulations! You found the word: {user_guess.upper()}",
            "solved": True,
            "game_over": True,
            "final_guess": user_guess.upper()
        })

    # Call your existing filter_words logic
    # Make sure your solver_filter_words can accept the state and modify it or return new state
    # The filter_words function in your wordle_solver.py modifies lists/sets in place.
    # For web, it's often cleaner if functions return new state, but modifying session variables works too.

    new_possible_words = solver_filter_words(
        list(possible_words), # Pass a copy
        user_guess,
        feedback_colors,
        list(known_letters), # Pass a copy
        set(present_letters), # Pass a copy
        set(absent_letters), # Pass a copy
        [set(ym) for ym in yellow_misplaced] # Pass a copy
    )

    next_suggested_guess = solver_suggest_next_guess(new_possible_words)
    guess_number += 1

    if guess_number > 6 and not solved:
        game_over = True

    # Update session state with new values
    update_session_state(new_possible_words, known_letters, present_letters, absent_letters, yellow_misplaced, guess_number, game_over, solved)

    return jsonify({
        "suggested_guess": next_suggested_guess.upper() if next_suggested_guess else "N/A",
        "possible_words_count": len(new_possible_words),
        "possible_words_sample": sorted(new_possible_words[:200]), # Send a sample
        "guess_number": guess_number,
        "known_letters_display": "".join([l.upper() if l else "_" for l in known_letters]),
        "present_letters_display": ", ".join(sorted([l.upper() for l in present_letters])) if present_letters else "None",
        "absent_letters_display": ", ".join(sorted([l.upper() for l in absent_letters])) if absent_letters else "None",
        "game_over": game_over,
        "solved": solved,
        "error": "No possible words left. Check feedback or word not in list." if not new_possible_words and not solved else None
    })

@app.route('/reset_game', methods=['POST'])
def reset_game_route():
    session.clear() # Clear the session to reset the game
    # Optionally, you could call a function here to get the very first suggested word
    # and send it back, similar to the index route, or let the client reload the page.
    return jsonify({"message": "Game reset successfully. Reload the page or make a new request to '/' for initial state."})


if __name__ == '__main__':
    # Important: Load words once globally if they don't change per session,
    # or ensure load_words handles being called multiple times efficiently.
    # For simplicity here, we load them when session starts.
    app.run(debug=True)