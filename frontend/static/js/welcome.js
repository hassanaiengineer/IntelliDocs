// Enhanced RAG - Welcome Page JavaScript

class WelcomeManager {
    constructor() {
        this.usernameInput = document.getElementById('username');
        this.continueBtn = document.getElementById('continueBtn');
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.animateOnLoad();
        
        // Check for existing session
        const existingSession = sessionStorage.getItem('rag_session_id');
        const existingUsername = sessionStorage.getItem('rag_username');
        
        if (existingSession && existingUsername) {
            this.usernameInput.value = existingUsername;
            this.validateInput();
            this.showReturningUserMessage();
        }
    }

    setupEventListeners() {
        // Username input validation
        this.usernameInput.addEventListener('input', (e) => {
            this.validateInput();
            this.updateInputState();
        });

        // Enter key support
        this.usernameInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !this.continueBtn.disabled) {
                this.proceedToAuth();
            }
        });

        // Continue button
        this.continueBtn.addEventListener('click', () => {
            this.proceedToAuth();
        });

        // Auto-focus username input after animations
        setTimeout(() => {
            this.usernameInput.focus();
        }, 1000);
    }

    validateInput() {
        const username = this.usernameInput.value.trim();
        const isValid = username.length >= 2 && username.length <= 50;
        
        this.continueBtn.disabled = !isValid;
        
        return isValid;
    }

    updateInputState() {
        const username = this.usernameInput.value.trim();
        const input = this.usernameInput;
        
        // Remove existing state classes
        input.classList.remove('border-red-400', 'border-amber', 'border-green-400');
        
        if (username.length === 0) {
            // Default state
            return;
        } else if (username.length < 2) {
            // Invalid state
            input.classList.add('border-red-400');
        } else if (username.length > 50) {
            // Too long
            input.classList.add('border-red-400');
        } else {
            // Valid state
            input.classList.add('border-green-400');
        }
    }

    animateOnLoad() {
        // Add reveal animation to elements
        const revealElements = document.querySelectorAll('.reveal-animation');
        
        revealElements.forEach((element, index) => {
            element.style.animationDelay = `${0.2 + (index * 0.2)}s`;
        });

        // Add typing effect to subtitle
        this.addTypingEffect();
    }

    addTypingEffect() {
        const subtitle = document.querySelector('p.text-xl');
        const originalText = subtitle.textContent;
        subtitle.textContent = '';
        
        let index = 0;
        const typeWriter = () => {
            if (index < originalText.length) {
                subtitle.textContent += originalText.charAt(index);
                index++;
                setTimeout(typeWriter, 50);
            }
        };
        
        // Start typing effect after main title animation
        setTimeout(typeWriter, 800);
    }

    showReturningUserMessage() {
        // Create a subtle notification for returning users
        const notification = document.createElement('div');
        notification.className = 'fixed top-4 right-4 bg-amber text-obsidian px-4 py-2 rounded-lg font-mono text-sm z-50 opacity-0 transition-opacity duration-300';
        notification.textContent = 'Welcome back!';
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => notification.classList.remove('opacity-0'), 100);
        
        // Animate out
        setTimeout(() => {
            notification.classList.add('opacity-0');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    async proceedToAuth() {
        if (!this.validateInput()) {
            this.showError('Please enter a valid name (2-50 characters)');
            return;
        }

        const username = this.usernameInput.value.trim();
        
        try {
            // Show loading state
            this.setLoadingState(true);
            
            // Create session
            const response = await fetch('/api/auth/create-session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to create session');
            }
            
            const data = await response.json();
            
            // Store session information
            sessionStorage.setItem('rag_session_id', data.session_id);
            sessionStorage.setItem('rag_username', username);
            
            // Animate transition
            this.animateTransition(() => {
                window.location.href = '/auth';
            });
            
        } catch (error) {
            console.error('Error creating session:', error);
            this.showError(error.message || 'Failed to create session. Please try again.');
            this.setLoadingState(false);
        }
    }

    setLoadingState(loading) {
        if (loading) {
            this.continueBtn.disabled = true;
            this.continueBtn.innerHTML = `
                <div class="flex items-center justify-center">
                    <svg class="animate-spin -ml-1 mr-3 h-4 w-4 text-pearl" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span class="font-mono text-sm font-medium tracking-wider">Creating Session...</span>
                </div>
            `;
        } else {
            this.continueBtn.disabled = !this.validateInput();
            this.continueBtn.innerHTML = `
                <span class="font-mono text-sm font-medium tracking-wider">Continue to Setup</span>
                <svg class="w-4 h-4 ml-2 transform transition-transform group-hover:translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"></path>
                </svg>
            `;
        }
    }

    animateTransition(callback) {
        const mainContainer = document.querySelector('.glass-morphism');
        
        mainContainer.style.transition = 'all 0.5s ease-out';
        mainContainer.style.transform = 'translateY(-20px) scale(0.95)';
        mainContainer.style.opacity = '0';
        
        setTimeout(callback, 500);
    }

    showError(message) {
        // Remove existing error messages
        const existingError = document.querySelector('.error-message');
        if (existingError) existingError.remove();
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message fixed top-4 left-1/2 transform -translate-x-1/2 bg-red-500 text-white px-6 py-3 rounded-lg font-mono text-sm z-50 shadow-lg';
        errorDiv.textContent = message;
        
        document.body.appendChild(errorDiv);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            errorDiv.style.opacity = '0';
            errorDiv.style.transform = 'translate(-50%, -100%)';
            setTimeout(() => errorDiv.remove(), 300);
        }, 5000);
    }
}

// Initialize welcome manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new WelcomeManager();
});

// Global function for backward compatibility
function proceedToAuth() {
    if (window.welcomeManager) {
        window.welcomeManager.proceedToAuth();
    }
}

// Add some extra interactive features
document.addEventListener('mousemove', (e) => {
    const orbs = document.querySelectorAll('.floating-orb');
    const mouseX = e.clientX / window.innerWidth;
    const mouseY = e.clientY / window.innerHeight;
    
    orbs.forEach((orb, index) => {
        const speed = 0.5 + (index * 0.2);
        const xOffset = (mouseX - 0.5) * speed * 20;
        const yOffset = (mouseY - 0.5) * speed * 20;
        
        orb.style.transform = `translate(${xOffset}px, ${yOffset}px)`;
    });
});

// Add keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Escape to clear input
    if (e.key === 'Escape') {
        document.getElementById('username').value = '';
        document.getElementById('username').focus();
    }
});

// Add visual feedback for form interactions
document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('username');
    
    input.addEventListener('focus', () => {
        input.closest('.glass-morphism').classList.add('ring-1', 'ring-amber/50');
    });
    
    input.addEventListener('blur', () => {
        input.closest('.glass-morphism').classList.remove('ring-1', 'ring-amber/50');
    });
});
