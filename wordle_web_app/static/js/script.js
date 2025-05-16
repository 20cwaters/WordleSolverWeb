document.addEventListener('DOMContentLoaded', () => {
    const suggestedGuessEl = document.getElementById('suggestedGuess');
    const userGuessInput = document.getElementById('userGuess');
    const feedbackBoxesContainer = document.getElementById('feedbackBoxes');
    const submitFeedbackBtn = document.getElementById('submitFeedbackBtn');
    const resetGameBtn = document.getElementById('resetGameBtn');

    const possibleWordsCountEl = document.getElementById('possibleWordsCount');
    const possibleWordsSampleEl = document.getElementById('possibleWordsSample');
    const guessNumberEl = document.getElementById('guessNumber');
    const knownLettersDisplayEl = document.getElementById('knownLettersDisplay');
    const presentLettersDisplayEl = document.getElementById('presentLettersDisplay');
    const absentLettersDisplayEl = document.getElementById('absentLettersDisplay');
    const messageAreaEl = document.getElementById('messageArea');

    // New elements for settings
    const excludePastWordsCheckbox = document.getElementById('excludePastWordsCheckbox');
    const wordListInfoEl = document.getElementById('wordListInfo');


    let currentFeedback = ['X', 'X', 'X', 'X', 'X'];
    let feedbackBoxElements = [];

    function createFeedbackBoxes(guessLength = 5) {
        feedbackBoxesContainer.innerHTML = '';
        feedbackBoxElements = [];
        currentFeedback = Array(guessLength).fill('X');

        for (let i = 0; i < guessLength; i++) {
            const box = document.createElement('div');
            box.classList.add('feedback-box', 'gray'); // Start with gray class
            box.dataset.index = i;
            box.textContent = '';

            box.addEventListener('click', () => {
                if (!userGuessInput.value || userGuessInput.value.length !== 5) {
                    showMessage("Enter a 5-letter guess first.");
                    return;
                }
                const index = parseInt(box.dataset.index);
                let newColorChar;
                let newClassName;

                // Cycle X -> G -> Y -> X
                if (currentFeedback[index] === 'X') {
                    newColorChar = 'G'; newClassName = 'green';
                } else if (currentFeedback[index] === 'G') {
                    newColorChar = 'Y'; newClassName = 'yellow';
                } else { // Was 'Y'
                    newColorChar = 'X'; newClassName = 'gray';
                }
                currentFeedback[index] = newColorChar;
                box.className = 'feedback-box ' + newClassName; // Update class for color
            });
            feedbackBoxesContainer.appendChild(box);
            feedbackBoxElements.push(box);
        }
    }

    // No need for getColorHex if using CSS classes directly for background

    userGuessInput.addEventListener('input', () => {
        const guess = userGuessInput.value.toUpperCase();
        userGuessInput.value = guess.substring(0, 5); // Ensure only 5 chars

        for (let i = 0; i < 5; i++) {
            if (feedbackBoxElements[i]) {
                feedbackBoxElements[i].textContent = guess[i] || '';
                if (!guess[i]) {
                    currentFeedback[i] = 'X';
                    feedbackBoxElements[i].className = 'feedback-box gray';
                }
            }
        }
    });


    submitFeedbackBtn.addEventListener('click', async () => {
        const guess = userGuessInput.value.toLowerCase();
        const feedbackString = currentFeedback.join('');

        if (guess.length !== 5 || !guess.match(/^[a-z]+$/i)) {
            showMessage("Please enter a valid 5-letter guess.");
            return;
        }

        showMessage("Processing...");
        try {
            const response = await fetch('/submit_guess', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ guess: guess, feedback: feedbackString })
            });
            const data = await response.json(); // Always expect JSON

            if (data.error) {
                showMessage(data.error);
                if(data.game_over){
                    submitFeedbackBtn.disabled = true;
                }
            } else {
                 updateUI(data); // This will handle solved/game_over states too
            }

            // UpdateUI should handle enabling/disabling submitBtn based on game_over/solved
            if (data.solved || data.game_over) {
                submitFeedbackBtn.disabled = true;
                if (data.solved) {
                    showMessage(`Solved! Word: ${data.final_guess || guess.toUpperCase()}`);
                } else if (data.game_over && !data.solved) { // Make sure it's game over and not solved
                    showMessage("Game Over. No more guesses.");
                }
            } else {
                 userGuessInput.value = '';
                 createFeedbackBoxes(); // Reset feedback boxes visually
                 submitFeedbackBtn.disabled = false; // Ensure it's enabled if game is ongoing
            }


        } catch (error) {
            showMessage("Error communicating with server: " + error);
            console.error("Fetch error:", error);
        }
    });

    resetGameBtn.addEventListener('click', async () => {
        if (!confirm("Are you sure you want to start a new game? This will apply current settings.")) return;
        
        const excludePast = excludePastWordsCheckbox.checked;
        showMessage("Resetting game...");

        try {
            const response = await fetch('/reset_game', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ exclude_past_words: excludePast }) // Send the setting
            });
            const data = await response.json();
            
            if (data.error) {
                showMessage(data.error);
                return;
            }
            
            updateUI(data);
            userGuessInput.value = '';
            createFeedbackBoxes(); // Reset feedback boxes visually
            submitFeedbackBtn.disabled = false; // Re-enable for new game
            showMessage(data.message || "Game reset. New settings applied.");

        } catch (error) {
            showMessage("Error resetting game: " + error);
            console.error("Reset error:", error);
        }
    });

    excludePastWordsCheckbox.addEventListener('change', () => {
        // Inform user that they need to start a new game for the setting to take effect.
        showMessage("Word list setting changed. Click 'New Game' to apply this setting.");
    });

    function updateUI(data) {
        if (data.suggested_guess) suggestedGuessEl.textContent = data.suggested_guess;
        if (data.possible_words_count !== undefined) possibleWordsCountEl.textContent = data.possible_words_count;
        if (data.guess_number) guessNumberEl.textContent = data.guess_number;

        if (data.known_letters_display) knownLettersDisplayEl.textContent = data.known_letters_display;
        if (data.present_letters_display) presentLettersDisplayEl.textContent = data.present_letters_display;
        if (data.absent_letters_display) absentLettersDisplayEl.textContent = data.absent_letters_display;

        if (data.possible_words_sample) {
            possibleWordsSampleEl.innerHTML = ''; // Clear previous
            data.possible_words_sample.forEach(word => {
                const span = document.createElement('span');
                span.textContent = word;
                possibleWordsSampleEl.appendChild(span);
            });
        }
        if (data.message && !(data.solved || data.game_over)) { // Don't overwrite solved/game over message immediately
            showMessage(data.message);
        }

        // Update settings display from server response
        if (data.hasOwnProperty('exclude_past_words_setting')) {
            excludePastWordsCheckbox.checked = data.exclude_past_words_setting;
        }
        if (data.word_list_info) {
            wordListInfoEl.textContent = data.word_list_info;
        }
    }

    function showMessage(msg) {
        messageAreaEl.textContent = msg;
    }

    // Initial setup
    createFeedbackBoxes();
    // The initial state of excludePastWordsCheckbox is set by Flask templating.
    // The initial wordListInfo is also set by Flask templating.
});