import random

# In solver_logic.py

# Keep your global WORD_LIST and PAST_WORDS if other functions in solver_logic.py rely on them being global
WORD_LIST = []
PAST_WORDS = set() # This will be populated by load_past_words

def load_past_words(filename="past_used_words.txt"):
    """Loads past used Wordle words that should be excluded."""
    global PAST_WORDS # Modifies the global PAST_WORDS
    try:
        with open(filename, 'r') as file:
            content = file.read()
            words = [word.strip().lower() for word in content.split('|')]
            PAST_WORDS = set(words) # Set the global
        print(f"Loaded {len(PAST_WORDS)} past used Wordle words to exclude (global set)")
    except FileNotFoundError:
        print(f"Warning: {filename} not found. No past words will be excluded (global set).")
        PAST_WORDS = set()
    return PAST_WORDS # Return it as well, as app.py uses the returned value for the session

# MODIFIED load_words function:
def load_words(filename="words.txt", past_words_to_exclude=None): # Added past_words_to_exclude
    """
    Loads words from a file.
    Optionally filters out words from the provided past_words_to_exclude set.
    """
    global WORD_LIST # Still sets the global WORD_LIST for other potential uses
    
    # Use an empty set if no specific set is passed for exclusion in this call
    if past_words_to_exclude is None:
        past_words_to_exclude = set() # Default to empty set if not provided

    try:
        with open(filename, 'r') as file:
            all_loaded_words = [word.strip().lower() for word in file if len(word.strip()) == 5 and word.strip().isalpha()]
            
        # Filter out past used words using the provided argument
        if past_words_to_exclude:
            initial_count = len(all_loaded_words)
            # The main list for the app will be the filtered one
            current_word_list = [word for word in all_loaded_words if word not in past_words_to_exclude]
            excluded_count = initial_count - len(current_word_list)
            print(f"Excluded {excluded_count} words based on argument for this load.")
        else:
            current_word_list = all_loaded_words
            print("No past words provided for exclusion in this load, using all loaded words.")
            
        WORD_LIST = list(current_word_list) # Update the global WORD_LIST as well
            
        print(f"Successfully loaded {len(current_word_list)} words from {filename} for current operation.")
        return current_word_list # Return the list for immediate use by app.py
        
    except FileNotFoundError:
        print(f"Warning: {filename} not found. Using small sample list instead.")
        sample_words = [
            "crane", "slate", "audio", "adieu", "trace", "roate", "raise", "soare", 
            "alert", "alter", "later", "table", "ratio", "stare", "arise", "irate",
            "learn", "noble", "media", "ocean", "ideal", "radio", "steam", "dream"
        ]
        # Filter sample words too if past_words_to_exclude is provided
        current_word_list = [word.lower() for word in sample_words if len(word) == 5 and word.isalpha() and word not in past_words_to_exclude]
        WORD_LIST = list(current_word_list)
        return current_word_list

def get_guess_and_feedback():
    """Gets the user's guess and Wordle's feedback."""
    print("\nAfter playing your guess in the Wordle game:")
    
    while True:
        guess = input("Enter your 5-letter guess: ").lower().strip()
        if not guess:
            print("Please enter a guess.")
            continue
            
        if len(guess) != 5:
            print("Guess must be exactly 5 letters.")
            continue
            
        if not guess.isalpha():
            print("Guess must contain only letters.")
            continue
            
        break

    print("\nEnter the color feedback from Wordle:")
    print("G = Green (correct letter, correct position)")
    print("Y = Yellow (correct letter, wrong position)")
    print("X = Gray/Black (letter not in the word)")
    
    while True:
        feedback_str = input("Feedback (GGYXX format): ").upper().strip()
        if not feedback_str:
            print("Please enter feedback.")
            continue
            
        if len(feedback_str) != 5:
            print("Feedback must be exactly 5 characters.")
            continue
            
        if not all(c in "GYX" for c in feedback_str):
            print("Invalid feedback. Use only G, Y, or X for each position.")
            continue
            
        break
        
    # Display what the user entered
    feedback_display = []
    for i, (letter, fb) in enumerate(zip(guess, feedback_str)):
        if fb == 'G':
            feedback_display.append(f"{letter.upper()}(G)")
        elif fb == 'Y':
            feedback_display.append(f"{letter.upper()}(Y)")
        else:
            feedback_display.append(f"{letter.upper()}(X)")
    
    print(f"Recorded: {' '.join(feedback_display)}")
    
    return guess, feedback_str

def filter_words(possible_words, guess, feedback, known_letters, present_letters, absent_letters, yellow_misplaced):
    """Filters the word list based on the feedback."""
    new_possible_words = []

    # Update knowledge based on feedback
    for i, (letter, fb) in enumerate(zip(guess, feedback)):
        if fb == 'G':
            known_letters[i] = letter
            if letter in present_letters: # If it was yellow before, now it's green
                present_letters.discard(letter)
            # A letter can be green and also previously yellow in another spot,
            # so don't add to absent_letters if it's green.
        elif fb == 'Y':
            present_letters.add(letter)
            yellow_misplaced[i].add(letter)
        elif fb == 'X':
            # Only add to absent_letters if not known or present from this guess or previous
            # This handles words with duplicate letters where one is G/Y and other is X
            is_letter_green_or_yellow_in_guess = False
            for j, (g_letter, g_fb) in enumerate(zip(guess, feedback)):
                if g_letter == letter and (g_fb == 'G' or g_fb == 'Y'):
                    is_letter_green_or_yellow_in_guess = True
                    break
            
            if not is_letter_green_or_yellow_in_guess and letter not in known_letters:
                 absent_letters.add(letter)


    for word in possible_words:
        valid = True
        temp_present_letters = set(present_letters) # Copy for local check

        # 1. Green Check: Check for letters in known positions
        for i, known_letter in enumerate(known_letters):
            if known_letter and word[i] != known_letter:
                valid = False
                break
        if not valid:
            continue

        # 2. Yellow Check (misplaced letters)
        for i, yellow_set_at_pos in enumerate(yellow_misplaced):
            if word[i] in yellow_set_at_pos: # Letter is in a known yellow position
                valid = False
                break
        if not valid:
            continue
        
        # Count letters in the current word to handle duplicates correctly for yellow/gray
        word_letter_counts = {}
        for char_in_word in word:
            word_letter_counts[char_in_word] = word_letter_counts.get(char_in_word, 0) + 1
        
        # Combined Yellow & Gray check (more robust for duplicates)
        for i, char_in_word in enumerate(word):
            # Gray check part 1: if a letter is truly absent
            if char_in_word in absent_letters and known_letters[i] != char_in_word and char_in_word not in present_letters:
                valid = False
                break
            
            # Track if present letters are actually found
            if char_in_word in temp_present_letters:
                temp_present_letters.remove(char_in_word) # Mark as found
        
        if not valid:
            continue

        # Yellow check part 2: All present_letters must be in the word
        if len(temp_present_letters) > 0: # Some yellow letters were not found
            valid = False
            continue

        # Edge case for gray letters with duplicates in guess vs solution
        # e.g., guess 'SPOON', feedback 'XXXYX', answer 'BLOCK' (O is absent)
        # e.g., guess 'APPLE', feedback 'YXXXG', answer 'PLATE' (one P is present, not at pos 0, E is at pos 4)
        # The absent_letters logic already handles cases like "SPEED" (E is gray) vs "TREES" (E is green).
        # What needs more care: if 'P' in 'APPLE' is Gray, but the word is 'PAPER' (one P)
        # current absent_letters logic: adds to absent if not G/Y *in current guess*.
        # This is mostly handled by ensuring that a letter isn't added to absent_letters if it's also G/Y.
        # The more complex part is when a guessed letter (e.g. 'P' in "APPLE") has one instance 'Y' and another 'X'.
        # This implies exactly one 'P'.
        
        # Count occurrences of letters from the guess in the current `word`
        # to compare against non-gray occurrences in the `guess`.
        guess_letter_counts = {}
        non_gray_guess_letters = []
        for gl, gf in zip(guess, feedback):
            if gf != 'X':
                non_gray_guess_letters.append(gl)
                guess_letter_counts[gl] = guess_letter_counts.get(gl, 0) + 1

        for letter_to_check_count in guess_letter_counts:
            count_in_word = word.count(letter_to_check_count)
            # If a letter was guessed (e.g., two 'P's in 'APPLE') and one 'P' is gray,
            # it means the count of that letter in the solution is *exactly* the number of non-gray P's.
            # Check if any letter from the guess was marked gray
            gray_instances_of_letter_in_guess = 0
            non_gray_instances_of_letter_in_guess = 0
            for gl, gf in zip(guess, feedback):
                if gl == letter_to_check_count:
                    if gf == 'X':
                        gray_instances_of_letter_in_guess +=1
                    else:
                        non_gray_instances_of_letter_in_guess +=1
            
            if gray_instances_of_letter_in_guess > 0: # This letter appeared as gray in the guess
                if count_in_word != non_gray_instances_of_letter_in_guess:
                    valid = False
                    break
            else: # This letter only appeared as G/Y in the guess
                if count_in_word < non_gray_instances_of_letter_in_guess:
                    valid = False # Word must contain at least as many as non-gray guess instances
                    break
        if not valid:
            continue


        if valid:
            new_possible_words.append(word)
            
    return new_possible_words

def suggest_next_guess(possible_words, tried_letters=None):
    """Suggests a next guess from the list of possible words."""
    if not possible_words:
        return None
    
    if len(possible_words) == 1:
        return possible_words[0]  # Only one word left, must be the answer
        
    if len(possible_words) <= 2:
        return random.choice(possible_words)  # With just 2 options, either is a good guess
    
    # Use letter frequency to determine best guess
    letter_freq = {}
    position_freq = [{} for _ in range(5)]  # For each position, track the frequency of each letter
    
    # Count letter frequencies in remaining possible words
    for word in possible_words:
        # Track unique letters in this word to avoid double counting
        seen_letters = set()
        for i, letter in enumerate(word):
            # Add to position-specific frequency
            position_freq[i][letter] = position_freq[i].get(letter, 0) + 1
            
            # Only count each unique letter once per word for overall frequency
            if letter not in seen_letters:
                letter_freq[letter] = letter_freq.get(letter, 0) + 1
                seen_letters.add(letter)
    
    # Score words based on letter frequency and uniqueness
    word_scores = {}
    for word in possible_words:
        score = 0
        seen_letters = set()  # To avoid counting duplicate letters
        
        for i, letter in enumerate(word):
            # Position score: higher for letters that appear often in this position
            position_score = position_freq[i].get(letter, 0) / len(possible_words)
            
            # Only count letter frequency score once per letter in the word
            if letter not in seen_letters:
                # Letter frequency score: higher for common letters
                freq_score = letter_freq.get(letter, 0) / len(possible_words)
                score += freq_score
                seen_letters.add(letter)
            
            score += position_score
            
        # Unique letters bonus: prefer words with unique letters
        unique_letters_count = len(set(word))
        score += unique_letters_count * 0.2  # Weight for uniqueness
        
        word_scores[word] = score
    
    # Sort by score (highest first)
    sorted_words = sorted(word_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Return the highest scoring word
    best_word = sorted_words[0][0]
    
    # If we have many options, consider alternative strategies
    if len(possible_words) > 10:
        # For early guesses with many possibilities, it's often good to pick a word
        # with lots of common letters to gain information, even if it's not a possible answer
        
        # Get top 3 words as candidates to add randomness to suggestions
        top_candidates = [word for word, score in sorted_words[:3]]
        return random.choice(top_candidates)
    
    return best_word

def main():
    """Main function to run the Wordle solver."""
    # First load past used words to exclude them
    load_past_words()
    
    # Then load the main word list
    all_words = load_words()
    if not all_words:
        print("Word list is empty. Please provide a words.txt file or check load_words function.")
        return

    possible_words = list(all_words)
    
    # Data to track across guesses
    known_letters = [None] * 5  # Letters in correct position (Green)
    present_letters = set()     # Letters in word, wrong position (Yellow)
    absent_letters = set()      # Letters not in word (Gray)
    # For each position, a set of letters that were yellow in that specific position
    yellow_misplaced = [set() for _ in range(5)]
    
    # Track all tried letters
    tried_letters = set()

    print("\n===== Welcome to Wordle Solver! =====")
    print(f"Loaded {len(all_words)} possible words.")
    print("(Excluding words already used in past Wordle puzzles)")
    print("\nHow to use:")
    print("1. Make a guess in your Wordle game")
    print("2. Enter your guess when prompted")
    print("3. Enter the feedback using:")
    print("   G - Green (correct letter, correct position)")
    print("   Y - Yellow (correct letter, wrong position)")
    print("   X - Gray (letter not in the word)")
    print("\nExample: If you guessed 'CRANE' and got Green, Yellow, Gray, Gray, Yellow")
    print("You would enter: GYXXY\n")

    for guess_num in range(1, 7): # Max 6 guesses
        print(f"\n--- Guess {guess_num}/6 ---")
        
        if not possible_words:
            print("No possible words left. Something went wrong or the word is not in the list.")
            break

        print(f"Number of possible words: {len(possible_words)}")
        if len(possible_words) < 20:
            print(f"Possible words: {', '.join(possible_words)}")
        
        # Show current knowledge
        if guess_num > 1:
            known_str = ['_'] * 5
            for i, letter in enumerate(known_letters):
                if letter:
                    known_str[i] = letter.upper()
            
            print(f"Known positions (Green): {' '.join(known_str)}")
            if present_letters:
                print(f"Present letters (Yellow): {', '.join(sorted(present_letters)).upper()}")
            if absent_letters:
                print(f"Absent letters (Gray): {', '.join(sorted(absent_letters)).upper()}")

        suggested_guess = suggest_next_guess(possible_words, tried_letters)
        if guess_num == 1: # For the first guess, suggest a common starter
            # Common high-information starting words. Could also use a more sophisticated strategy.
            starters = ["crane", "slate", "soare", "adieu", "trace"]
            # Ensure starter is in the word list if possible
            valid_starters = [s for s in starters if s in possible_words]
            if valid_starters:
                suggested_guess = random.choice(valid_starters)
            elif possible_words: # Fallback if no preferred starters are in the (potentially small) list
                 suggested_guess = random.choice(possible_words)
            else: # No words left, should not happen here
                print("No words left to suggest.")
                break


        if suggested_guess:
            print(f"Suggested guess: {suggested_guess.upper()}")
        else:
            # This case should ideally be caught by the check at the start of the loop
            print("No words left to suggest. The word might not be in your dictionary or there was contradictory feedback.")
            break

        guess, feedback = get_guess_and_feedback()
        
        # Add to tried letters
        for letter in guess:
            tried_letters.add(letter)

        if feedback == "GGGGG":
            print(f"\nCongratulations! You found the word: {guess.upper()}")
            break

        possible_words = filter_words(possible_words, guess, feedback, known_letters, present_letters, absent_letters, yellow_misplaced)

        if guess_num == 6 and feedback != "GGGGG":
            print("\nGame over! Word not found within 6 guesses.")
            if possible_words:
                print(f"Remaining possible words: {', '.join(possible_words)}")
            else:
                print("No possible words remain according to the feedback.")
    
    # Game ended
    print("\nThanks for using Wordle Solver!")
    print("Run the program again for a new game.")

if __name__ == "__main__":
    main() 