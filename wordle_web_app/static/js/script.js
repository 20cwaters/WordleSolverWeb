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


    let currentFeedback = ['X', 'X', 'X', 'X', 'X']; // G, Y, X
    let feedbackBoxElements = [];

    function createFeedbackBoxes(guessLength = 5) {
        feedbackBoxesContainer.innerHTML = ''; // Clear previous
        feedbackBoxElements = [];
        currentFeedback = Array(guessLength).fill('X');

        for (let i = 0; i < guessLength; i++) {
            const box = document.createElement('div');
            box.classList.add('feedback-box');
            box.dataset.index = i;
            box.textContent = ''; // Will be filled by guess input
            box.style.backgroundColor = getColorHex('X'); // Default Gray

            box.addEventListener('click', () => {
                if (!userGuessInput.value || userGuessInput.value.length !== 5) {
                    showMessage("Enter a 5-letter guess first.");
                    return;
                }
                const index = parseInt(box.dataset.index);
                switch (currentFeedback[index]) {
                    case 'X': currentFeedback[index] = 'G'; break;
                    case 'G': currentFeedback[index] = 'Y'; break;
                    case 'Y': currentFeedback[index] = 'X'; break;
                }
                box.style.backgroundColor = getColorHex(currentFeedback[index]);
                box.className = 'feedback-box ' + currentFeedback[index].toLowerCase();
            });
            feedbackBoxesContainer.appendChild(box);
            feedbackBoxElements.push(box);
        }
    }

    function getColorHex(colorChar) {
        if (colorChar === 'G') return '#6aaa64'; // Green
        if (colorChar === 'Y') return '#c9b458'; // Yellow
        return '#787c7e'; // Gray (X)
    }

    userGuessInput.addEventListener('input', () => {
        const guess = userGuessInput.value.toUpperCase();
        if (guess.length > 5) {
            userGuessInput.value = guess.substring(0, 5);
        }
        for (let i = 0; i < 5; i++) {
            if (feedbackBoxElements[i]) {
                feedbackBoxElements[i].textContent = guess[i] || '';
                if (!guess[i]) { // Reset color if letter is removed
                     currentFeedback[i] = 'X';
                     feedbackBoxElements[i].style.backgroundColor = getColorHex('X');
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
            const data = await response.json();

            if (data.error) {
                showMessage(data.error);
                if(data.game_over){
                    //disable further submissions
                    submitFeedbackBtn.disabled = true;
                }
                return;
            }

            updateUI(data);

            if (data.solved || data.game_over) {
                submitFeedbackBtn.disabled = true;
                if (data.solved) {
                    showMessage(`Solved! Word: ${data.final_guess || guess.toUpperCase()}`);
                } else {
                    showMessage("Game Over. No more guesses.");
                }
            } else {
                 userGuessInput.value = ''; // Clear input for next guess
                 createFeedbackBoxes(); // Reset feedback boxes
            }

        } catch (error) {
            showMessage("Error communicating with server: " + error);
            console.error("Fetch error:", error);
        }
    });

    resetGameBtn.addEventListener('click', async () => {
         if (!confirm("Are you sure you want to start a new game?")) return;
        try {
            await fetch('/reset_game', { method: 'POST' });
            // Reload the page to get fresh initial state from server
            window.location.reload();
        } catch (error) {
            showMessage("Error resetting game: " + error);
        }
    });

    function updateUI(data) {
        if (data.suggested_guess) suggestedGuessEl.textContent = data.suggested_guess;
        if (data.possible_words_count !== undefined) possibleWordsCountEl.textContent = data.possible_words_count;
        if (data.guess_number) guessNumberEl.textContent = data.guess_number;

        if (data.known_letters_display) knownLettersDisplayEl.textContent = data.known_letters_display;
        if (data.present_letters_display) presentLettersDisplayEl.textContent = data.present_letters_display;
        if (data.absent_letters_display) absentLettersDisplayEl.textContent = data.absent_letters_display;

        if (data.possible_words_sample) {
            possibleWordsSampleEl.innerHTML = '';
            data.possible_words_sample.forEach(word => {
                const span = document.createElement('span');
                span.textContent = word;
                possibleWordsSampleEl.appendChild(span);
            });
        }
        if(data.message) showMessage(data.message);
    }

    function showMessage(msg) {
        messageAreaEl.textContent = msg;
    }

    // Initial setup
    createFeedbackBoxes();
    submitFeedbackBtn.disabled = false; // Enable on load assuming first guess
});