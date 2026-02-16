// Enhanced RAG - Authentication Page JavaScript

class AuthManager {
    constructor() {
        this.sessionId = sessionStorage.getItem('rag_session_id');
        this.username = sessionStorage.getItem('rag_username');
        this.selectedProvider = null;
        this.apiKey = '';
        this.isValidated = false;
        
        this.providerCards = document.querySelectorAll('.provider-card');
        this.apiKeyInput = document.getElementById('apiKey');
        this.toggleBtn = document.getElementById('toggleApiKey');
        this.testBtn = document.getElementById('testBtn');
        this.proceedBtn = document.getElementById('proceedBtn');
        this.statusMessage = document.getElementById('statusMessage');
        this.providerLabel = document.getElementById('providerLabel');
        this.providerLink = document.getElementById('providerLink');
        
        this.init();
    }

    init() {
        this.checkSession();
        this.setupEventListeners();
        this.loadProviders();
        this.displayWelcomeMessage();
    }

    checkSession() {
        if (!this.sessionId || !this.username) {
            window.location.href = '/';
            return;
        }
    }

    displayWelcomeMessage() {
        const welcomeElement = document.getElementById('welcomeUser');
        if (welcomeElement) {
            welcomeElement.textContent = `Welcome, ${this.username}!`;
        }
    }

    setupEventListeners() {
        // Provider selection
        this.providerCards.forEach(card => {
            card.addEventListener('click', () => {
                this.selectProvider(card.dataset.provider);
            });
            
            // Keyboard support
            card.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.selectProvider(card.dataset.provider);
                }
            });
        });

        // API key input
        this.apiKeyInput.addEventListener('input', () => {
            this.validateInput();
        });

        this.apiKeyInput.addEventListener('paste', () => {
            // Small delay to allow paste to complete
            setTimeout(() => this.validateInput(), 50);
        });

        // Toggle API key visibility
        this.toggleBtn.addEventListener('click', () => {
            this.toggleApiKeyVisibility();
        });

        // Test connection
        this.testBtn.addEventListener('click', () => {
            this.testConnection();
        });

        // Proceed button
        this.proceedBtn.addEventListener('click', () => {
            this.proceedToChat();
        });

        // Enter key support
        this.apiKeyInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                if (this.testBtn.disabled === false) {
                    this.testConnection();
                } else if (this.proceedBtn.disabled === false) {
                    this.proceedToChat();
                }
            }
        });
    }

    async loadProviders() {
        try {
            const response = await fetch('/api/auth/providers');
            const data = await response.json();
            
            // Update provider links based on API response
            this.updateProviderLinks(data.providers);
            
        } catch (error) {
            console.error('Error loading providers:', error);
        }
    }

    updateProviderLinks(providers) {
        const providerMap = {
            'openai': 'https://platform.openai.com/api-keys',
            'anthropic': 'https://console.anthropic.com/',
            'gemini': 'https://makersuite.google.com/app/apikey'
        };

        providers.forEach(provider => {
            const card = document.querySelector(`[data-provider="${provider.id}"]`);
            if (card) {
                const link = providerMap[provider.id];
                if (link) {
                    card.dataset.link = link;
                }
            }
        });
    }

    selectProvider(providerId) {
        // Remove active state from all cards
        this.providerCards.forEach(card => {
            card.classList.remove('active');
            card.setAttribute('aria-selected', 'false');
        });

        // Add active state to selected card
        const selectedCard = document.querySelector(`[data-provider="${providerId}"]`);
        selectedCard.classList.add('active');
        selectedCard.setAttribute('aria-selected', 'true');

        this.selectedProvider = providerId;
        this.updateUI();
        this.validateInput();

        // Focus API key input
        this.apiKeyInput.focus();
    }

    updateUI() {
        if (!this.selectedProvider) return;

        const providerNames = {
            'openai': 'OpenAI API Key',
            'anthropic': 'Anthropic API Key', 
            'gemini': 'Google Gemini API Key'
        };

        const providerLinks = {
            'openai': 'https://platform.openai.com/api-keys',
            'anthropic': 'https://console.anthropic.com/',
            'gemini': 'https://makersuite.google.com/app/apikey'
        };

        this.providerLabel.textContent = providerNames[this.selectedProvider] || 'API Key';
        this.providerLink.href = providerLinks[this.selectedProvider] || '#';

        // Update placeholder
        const placeholders = {
            'openai': 'sk-...',
            'anthropic': 'sk-ant-...',
            'gemini': 'AI...'
        };
        this.apiKeyInput.placeholder = `Enter your ${placeholders[this.selectedProvider] || 'API'} key`;
    }

    validateInput() {
        this.apiKey = this.apiKeyInput.value.trim();
        
        const hasProvider = !!this.selectedProvider;
        const hasApiKey = this.apiKey.length > 0;
        const isValidFormat = this.validateApiKeyFormat();

        // Enable/disable buttons
        this.testBtn.disabled = !(hasProvider && hasApiKey && isValidFormat);
        
        // Only enable proceed if validated
        this.proceedBtn.disabled = !this.isValidated;

        // Update input state
        this.updateInputState(isValidFormat);
    }

    validateApiKeyFormat() {
        if (!this.apiKey || !this.selectedProvider) return false;

        const patterns = {
            'openai': /^sk-[A-Za-z0-9]{20,}$/,
            'anthropic': /^sk-ant-[A-Za-z0-9\-_]{20,}$/,
            'gemini': /^AI[A-Za-z0-9\-_]{35,}$/
        };

        const pattern = patterns[this.selectedProvider];
        return pattern ? pattern.test(this.apiKey) : this.apiKey.length > 10;
    }

    updateInputState(isValid) {
        const input = this.apiKeyInput;
        
        // Remove existing state classes
        input.classList.remove('border-red-400', 'border-green-400', 'border-amber');
        
        if (this.apiKey.length === 0) {
            // Default state
            return;
        } else if (!isValid) {
            // Invalid format
            input.classList.add('border-red-400');
        } else if (this.isValidated) {
            // Validated state
            input.classList.add('border-green-400');
        } else {
            // Valid format but not tested
            input.classList.add('border-amber');
        }
    }

    toggleApiKeyVisibility() {
        const input = this.apiKeyInput;
        const showText = this.toggleBtn.querySelector('.show-text');
        const hideText = this.toggleBtn.querySelector('.hide-text');
        
        if (input.type === 'password') {
            input.type = 'text';
            showText.classList.add('hidden');
            hideText.classList.remove('hidden');
        } else {
            input.type = 'password';
            showText.classList.remove('hidden');
            hideText.classList.add('hidden');
        }
    }

    async testConnection() {
        if (!this.selectedProvider || !this.apiKey) return;

        this.setLoadingState(this.testBtn, true, 'Testing...');
        this.hideStatusMessage();

        try {
            const response = await fetch('/api/auth/validate-credentials', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    provider: this.selectedProvider,
                    api_key: this.apiKey
                })
            });

            const data = await response.json();

            if (response.ok) {
                this.isValidated = true;
                this.showStatusMessage('success', 'Connection successful! API key validated and saved.');
                
                // Update progress bar
                document.querySelector('.progress-fill').style.width = '100%';
                
                // Enable proceed button
                this.proceedBtn.disabled = false;
                this.validateInput();
                
            } else {
                this.isValidated = false;
                this.showStatusMessage('error', data.detail || 'API key validation failed');
                this.proceedBtn.disabled = true;
            }

        } catch (error) {
            this.isValidated = false;
            this.showStatusMessage('error', 'Network error during validation. Please try again.');
            this.proceedBtn.disabled = true;
        } finally {
            this.setLoadingState(this.testBtn, false, 'Test Connection');
        }
    }

    async proceedToChat() {
        if (!this.isValidated) {
            this.showStatusMessage('warning', 'Please test your API key first');
            return;
        }

        this.setLoadingState(this.proceedBtn, true, 'Preparing...');

        try {
            // Test that session is properly configured
            const response = await fetch(`/api/auth/session/${this.sessionId}`);
            
            if (response.ok) {
                const sessionData = await response.json();
                
                if (sessionData.has_api_key && sessionData.provider) {

                // 🔥 Store provider & API key for Chat UI
                sessionStorage.setItem("rag_api_key", this.apiKey);
                sessionStorage.setItem("rag_provider", this.selectedProvider);

                // Animate transition
                this.animateTransition(() => {
                    window.location.href = '/chat';
                });
                } else {
                    throw new Error('Session not properly configured');
                }
            } else {
                throw new Error('Session validation failed');
            }

        } catch (error) {
            this.showStatusMessage('error', 'Failed to proceed to chat. Please try again.');
            this.setLoadingState(this.proceedBtn, false, 'Continue to Chat');
        }
    }

    setLoadingState(button, loading, defaultText) {
        if (loading) {
            button.disabled = true;
            button.innerHTML = `
                <svg class="animate-spin -ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Testing...</span>
            `;
        } else {
            button.disabled = !this.isValidated;
            button.innerHTML = defaultText.includes('Test') ? `
                <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <span>${defaultText}</span>
            ` : `
                <span>${defaultText}</span>
                <svg class="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"></path>
                </svg>
            `;
        }
    }

    showStatusMessage(type, message) {
        this.statusMessage.className = `rounded-lg p-4 font-mono text-sm status-${type}`;
        this.statusMessage.innerHTML = `
            <div class="flex items-start space-x-2">
                ${this.getStatusIcon(type)}
                <div class="flex-1">
                    <p>${message}</p>
                </div>
            </div>
        `;
        this.statusMessage.classList.remove('hidden');
    }

    hideStatusMessage() {
        this.statusMessage.classList.add('hidden');
    }

    getStatusIcon(type) {
        const icons = {
            'success': `
                <svg class="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
            `,
            'error': `
                <svg class="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
            `,
            'warning': `
                <svg class="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
                </svg>
            `,
            'info': `
                <svg class="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
            `
        };
        return icons[type] || icons['info'];
    }

    animateTransition(callback) {
        const mainContainer = document.querySelector('.glass-morphism');
        
        mainContainer.style.transition = 'all 0.5s ease-out';
        mainContainer.style.transform = 'translateY(-20px) scale(0.95)';
        mainContainer.style.opacity = '0';
        
        setTimeout(callback, 500);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new AuthManager();
});

// Handle browser back/forward navigation
window.addEventListener('popstate', () => {
    const sessionId = sessionStorage.getItem('rag_session_id');
    if (!sessionId) {
        window.location.href = '/';
    }
});

// Add keyboard navigation for provider cards
document.addEventListener('keydown', (e) => {
    const providerCards = document.querySelectorAll('.provider-card');
    const currentActive = document.querySelector('.provider-card.active');
    
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
        e.preventDefault();
        
        let currentIndex = Array.from(providerCards).indexOf(currentActive);
        let newIndex;
        
        if (e.key === 'ArrowRight') {
            newIndex = (currentIndex + 1) % providerCards.length;
        } else {
            newIndex = currentIndex <= 0 ? providerCards.length - 1 : currentIndex - 1;
        }
        
        providerCards[newIndex].click();
        providerCards[newIndex].focus();
    }
});
