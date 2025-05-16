from flask import Flask, render_template, request, jsonify, session
# Assuming your solver functions are in solver_logic.py
from solver_logic import (
    load_past_words as solver_load_past_words,
    load_words as solver_load_words, # This should accept past_words_to_exclude
    filter_words as solver_filter_words,
    suggest_next_guess as solver_suggest_next_guess
)
import random

app = Flask(__name__)
app.secret_key = 'your_very_secret_key_for_sessions_CHANGE_ME'

# --- Helper to get word list info string ---
def get_word_list_info_text(current_word_list_size, total_raw_word_count, past_words_excluded_count, is_excluding):
    if is_excluding:
        if past_words_excluded_count > 0:
            return f"{current_word_list_size} words (from {total_raw_word_count} total, {past_words_excluded_count} past answers excluded)"
        else:
            return f"{current_word_list_size} words from {total_raw_word_count} (no past answers found in list or to exclude)"
    else:
        return f"{current_word_list_size} words from {total_raw_word_count} (all words included)"

# --- Game State Initialization and Management ---
def initialize_game_session(exclude_past_setting):
    """Initializes or re-initializes the game state in the session."""
    session['exclude_past_words'] = exclude_past_setting
    
    # Load all raw words once to get a base count (if not already done)
    # This assumes solver_load_words with no exclusion returns the full list from words.txt
    all_raw_words_from_file = solver_load_words(filename="words.txt", past_words_to_exclude=set())
    session['total_raw_word_count'] = len(all_raw_words_from_file)

    past_words_to_exclude_set = set()
    if exclude_past_setting:
        past_words_from_file = solver_load_past_words() # This should just return the set
        if past_words_from_file:
            past_words_to_exclude_set = past_words_from_file
    
    session['past_words_loaded_count'] = len(past_words_to_exclude_set)

    # Load the actual game word list based on the setting
    game_word_list = solver_load_words(filename="words.txt", past_words_to_exclude=past_words_to_exclude_set)
    
    session['all_words_for_current_game'] = game_word_list # The active list
    session['possible_words'] = list(game_word_list)
    session['known_letters'] = [None] * 5
    session['present_letters'] = [] 
    session['absent_letters'] = []  
    session['yellow_misplaced'] = [[] for _ in range(5)] 
    session['guess_number'] = 1
    session['game_over'] = False
    session['solved'] = False
    session.modified = True

def get_current_game_data_for_frontend():
    """Prepares data from session to send to the frontend."""
    possible_words = session.get('possible_words', [])
    known_letters = session.get('known_letters', [None]*5)
    present_letters_list = session.get('present_letters', []) # Already stored as sorted list
    absent_letters_list = session.get('absent_letters', [])   # Already stored as sorted list
    
    current_exclude_setting = session.get('exclude_past_words', True)
    total_raw_count = session.get('total_raw_word_count', 0)
    past_loaded_count = session.get('past_words_loaded_count', 0) # Count of words *actually* used for exclusion

    # Calculate effective number of words used for exclusion based on current list
    # This can be tricky if the main list itself is smaller than the past words list.
    # For simplicity, past_loaded_count is the number of words in past_used_words.txt
    
    word_list_info = get_word_list_info_text(
        len(session.get('all_words_for_current_game', [])), # Use the size of the actual list loaded for the game
        total_raw_count,
        past_loaded_count if current_exclude_setting else 0, # Only show excluded count if setting is on
        current_exclude_setting
    )
    
    # Get a suggestion
    starters = ["crane", "slate", "soare", "adieu", "trace"]
    valid_starters = [s for s in starters if s in possible_words] # Suggest from current possible_words
    if session.get('guess_number', 1) == 1:
        if valid_starters:
            suggested = random.choice(valid_starters)
        elif possible_words:
            suggested = solver_suggest_next_guess(possible_words)
        else:
            suggested = "N/A"
    else:
        suggested = solver_suggest_next_guess(possible_words) if possible_words else "N/A"


    return {
        "suggested_guess": suggested.upper() if suggested else "N/A",
        "possible_words_count": len(possible_words),
        "possible_words_sample": sorted(possible_words[:200]),
        "guess_number": session.get('guess_number', 1),
        "known_letters_display": "".join([l.upper() if l else "_" for l in known_letters]),
        "present_letters_display": ", ".join(present_letters_list) if present_letters_list else "None",
        "absent_letters_display": ", ".join(absent_letters_list) if absent_letters_list else "None",
        "game_over": session.get('game_over', False),
        "solved": session.get('solved', False),
        "exclude_past_words_setting": current_exclude_setting,
        "word_list_info": word_list_info
    }

@app.route('/')
def index():
    # Initialize game session if it's a new session or if forced by a flag
    if 'possible_words' not in session: # Simplistic check for new session
        initialize_game_session(session.get('exclude_past_words', True)) # Default to True
    
    # Always get current data to render template
    template_data = get_current_game_data_for_frontend()
    return render_template('index.html', **template_data)

@app.route('/submit_guess', methods=['POST'])
def submit_guess_route():
    if 'possible_words' not in session: # Game not initialized
        initialize_game_session(session.get('exclude_past_words', True))

    data = request.get_json()
    user_guess = data.get('guess', '').lower()
    feedback_colors = data.get('feedback', '')

    current_exclude_setting = session.get('exclude_past_words', True) # Get current setting

    if session.get('game_over', False) or session.get('solved', False):
        return jsonify({
            "error": "Game is over.", "game_over": session['game_over'], "solved": session['solved'],
            **get_current_game_data_for_frontend() # Send current state
        })

    if not user_guess or len(user_guess) != 5 or not user_guess.isalpha():
        return jsonify({"error": "Invalid guess.", **get_current_game_data_for_frontend()})
    if not feedback_colors or len(feedback_colors) != 5 or not all(c in "GYX" for c in feedback_colors):
        return jsonify({"error": "Invalid feedback string.", **get_current_game_data_for_frontend()})

    # Retrieve current game state from session
    possible_words = list(session['possible_words']) # Work with copies for filtering
    known_letters = list(session['known_letters'])
    present_letters_set = set(session['present_letters'])
    absent_letters_set = set(session['absent_letters'])
    yellow_misplaced_sets = [set(ym) for ym in session['yellow_misplaced']]
    guess_number = session['guess_number']

    if feedback_colors == "GGGGG":
        session['solved'] = True
        session['game_over'] = True
        session.modified = True
        response_data = get_current_game_data_for_frontend()
        response_data["message"] = f"Congratulations! You found the word: {user_guess.upper()}"
        response_data["final_guess"] = user_guess.upper()
        return jsonify(response_data)

    # Call your existing filter_words logic
    # Ensure filter_words correctly updates the passed-in lists/sets or returns new ones
    # The provided solver_filter_words modifies them in place.
    new_possible_words = solver_filter_words(
        possible_words, # This is already a copy from session['possible_words']
        user_guess,
        feedback_colors,
        known_letters,      # This is a copy, will be modified
        present_letters_set, # This is a copy, will be modified
        absent_letters_set,  # This is a copy, will be modified
        yellow_misplaced_sets # This is a copy, will be modified
    )
    
    guess_number += 1
    session['guess_number'] = guess_number
    session['possible_words'] = new_possible_words
    session['known_letters'] = known_letters 
    session['present_letters'] = sorted(list(present_letters_set))
    session['absent_letters'] = sorted(list(absent_letters_set))
    session['yellow_misplaced'] = [sorted(list(ym_set)) for ym_set in yellow_misplaced_sets]

    if guess_number > 6 and not session['solved']:
        session['game_over'] = True
    
    session.modified = True
    
    response_data = get_current_game_data_for_frontend()
    if not new_possible_words and not session['solved']:
        response_data["error"] = "No possible words left. Check feedback or word not in list."
    return jsonify(response_data)


@app.route('/reset_game', methods=['POST'])
def reset_game_route():
    data = request.get_json()
    new_exclude_setting = data.get('exclude_past_words', True) # Get from JS
    
    initialize_game_session(new_exclude_setting) # Re-initialize with the new setting
    
    response_data = get_current_game_data_for_frontend()
    response_data["message"] = "Game reset and settings applied."
    return jsonify(response_data)

if __name__ == '__main__':
    app.run(debug=True)