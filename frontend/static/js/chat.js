// Enhanced RAG - Chat Interface JavaScript

class ChatManager {
    constructor() {
        this.sessionId = sessionStorage.getItem('rag_session_id');
        this.username = sessionStorage.getItem('rag_username');
        this.uploadedFiles = [];
        this.questionCount = 0;
        this.maxQuestions = 50;
        this.maxFiles = 4;
        this.isTyping = false;
        
        // DOM elements
        this.fileInput = document.getElementById('fileInput');
        this.dropZone = document.getElementById('dropZone');
        this.filesList = document.getElementById('filesList');
        this.emptyState = document.getElementById('emptyState');
        this.chatInput = document.getElementById('chatInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.chatContainer = document.getElementById('chatContainer');
        this.welcomeMessage = document.getElementById('welcomeMessage');
        this.uploadProgress = document.getElementById('uploadProgress');
        this.clearAllBtn = document.getElementById('clearAllBtn');
        
        this.init();
    }

        async init() {
            if (!this.validateSession()) {
                window.location.href = '/';
                return;
            }

            // 🔥 FIX: Load provider & API key from Auth
            this.apiKey = sessionStorage.getItem("rag_api_key");
            this.provider = sessionStorage.getItem("rag_provider");

            await this.loadSessionData();
            this.setupEventListeners();
            this.setupFileUpload();
            this.setupChat();
            this.displayUserInfo();
            await this.loadExistingFiles();
        }


    validateSession() {
        return this.sessionId && this.username;
    }

    async loadSessionData() {
        try {
            const response = await fetch(`/api/auth/session/${this.sessionId}`);
            if (response.ok) {
                const data = await response.json();
                this.questionCount = data.question_count || 0;
                this.updateQuestionCounter();
                
                // Update provider info
                document.getElementById('providerInfo').textContent = 
                    `Provider: ${data.provider || 'Not set'}`;
                document.getElementById('providerDisplay').textContent = 
                    data.provider || 'Unknown';
                
            } else {
                throw new Error('Session validation failed');
            }
        } catch (error) {
            console.error('Error loading session:', error);
            this.showError('Failed to load session data');
        }
    }

    displayUserInfo() {
        const userNameEl = document.getElementById('userName');
        const userInitialEl = document.getElementById('userInitial');
        
        userNameEl.textContent = this.username;
        userInitialEl.textContent = this.username.charAt(0).toUpperCase();
        
        document.getElementById('sessionInfo').textContent = 
            `Session: ${this.sessionId.slice(0, 8)}...`;
        document.getElementById('sessionIdDisplay').textContent = 
            this.sessionId;
    }

    setupEventListeners() {
        // File input change
        this.fileInput.addEventListener('change', (e) => {
            this.handleFileSelection(e.target.files);
        });

        // Clear all files
        this.clearAllBtn.addEventListener('click', () => {
            this.clearAllFiles();
        });

        // Chat input
        this.chatInput.addEventListener('input', () => {
            this.handleChatInput();
        });

        this.chatInput.addEventListener('keydown', (e) => {
            this.handleChatKeydown(e);
        });

        // Send button
        this.sendBtn.addEventListener('click', () => {
            this.sendMessage();
        });

        // Auto-resize textarea
        this.chatInput.addEventListener('input', () => {
            this.autoResizeTextarea();
        });
    }

    setupFileUpload() {
        // Drag and drop functionality
        this.dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.dropZone.classList.add('drag-over');
        });

        this.dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            if (!this.dropZone.contains(e.relatedTarget)) {
                this.dropZone.classList.remove('drag-over');
            }
        });

        this.dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            this.dropZone.classList.remove('drag-over');
            this.handleFileSelection(e.dataTransfer.files);
        });

        // Click to upload
        this.dropZone.addEventListener('click', () => {
            this.fileInput.click();
        });
    }

    setupChat() {
        // Enable chat if files are uploaded
        this.updateChatState();
    }

    async loadExistingFiles() {
        try {
            const response = await fetch(`/api/files/session/${this.sessionId}`);
            if (response.ok) {
                const data = await response.json();
                this.uploadedFiles = data.files || [];
                this.updateFilesList();
                this.updateChatState();
                this.updateFileCounter();
                this.updateSettingsModal();
            }
        } catch (error) {
            console.error('Error loading files:', error);
        }
    }

    async handleFileSelection(files) {
        if (!files || files.length === 0) return;
        
        const fileArray = Array.from(files);
        
        // Check file limits
        if (this.uploadedFiles.length + fileArray.length > this.maxFiles) {
            this.showError(`Cannot upload ${fileArray.length} files. Maximum ${this.maxFiles} files allowed. Currently have ${this.uploadedFiles.length} files.`);
            return;
        }

        // Validate file types and sizes
        const validFiles = [];
        for (const file of fileArray) {
            const validation = this.validateFile(file);
            if (!validation.valid) {
                this.showError(`File "${file.name}": ${validation.error}`);
                continue;
            }
            validFiles.push(file);
        }

        if (validFiles.length === 0) return;

        // Upload files
        await this.uploadFiles(validFiles);
    }

    validateFile(file) {
        const maxSize = 20 * 1024 * 1024; // 20MB
        const allowedTypes = ['.pdf', '.docx', '.doc'];
        
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        
        if (!allowedTypes.includes(ext)) {
            return {
                valid: false,
                error: `Unsupported file type. Allowed: ${allowedTypes.join(', ')}`
            };
        }
        
        if (file.size > maxSize) {
            return {
                valid: false,
                error: `File too large. Maximum size: 20MB`
            };
        }
        
        // Check for duplicate names
        if (this.uploadedFiles.some(f => f.filename === file.name)) {
            return {
                valid: false,
                error: `File with this name already exists`
            };
        }
        
        return { valid: true };
    }

    async uploadFiles(files) {
        const formData = new FormData();
        formData.append('session_id', this.sessionId);
        
        for (const file of files) {
            formData.append('files', file);
        }

        // Show progress
        this.showUploadProgress(true);
        
        // Add temporary file items
        const tempItems = files.map(file => ({
            filename: file.name,
            uploading: true,
            file_size_mb: (file.size / (1024 * 1024)).toFixed(1)
        }));
        
        this.addTempFileItems(tempItems);

        try {
            const response = await fetch('/api/upload/files', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            
            if (response.ok) {
                // Remove temp items
                this.removeTempFileItems();
                
                // Add successful uploads
                this.uploadedFiles = [...this.uploadedFiles, ...data.files_processed];
                this.updateFilesList();
                this.updateChatState();
                this.updateFileCounter();
                this.updateSettingsModal();
                
                this.showSuccess(`Successfully uploaded ${data.successful_uploads} file(s)`);
                
                if (data.failed_uploads > 0) {
                    this.showWarning(`${data.failed_uploads} file(s) failed to upload`);
                }
                
            } else {
                throw new Error(data.detail || 'Upload failed');
            }
            
        } catch (error) {
            console.error('Upload error:', error);
            this.removeTempFileItems();
            this.showError(error.message || 'Failed to upload files');
        } finally {
            this.showUploadProgress(false);
        }
    }

    addTempFileItems(files) {
        files.forEach(file => {
            const item = this.createFileItem({
                ...file,
                temp: true,
                chunks_created: 0,
                total_characters: 0
            });
            this.filesList.appendChild(item);
        });
        
        this.hideEmptyState();
    }

    removeTempFileItems() {
        const tempItems = this.filesList.querySelectorAll('.file-item[data-temp="true"]');
        tempItems.forEach(item => item.remove());
    }

    createFileItem(file) {
        const item = document.createElement('div');
        item.className = 'file-item';
        if (file.temp) {
            item.className += ' uploading';
            item.setAttribute('data-temp', 'true');
        }
        
        const fileExt = file.filename.split('.').pop().toLowerCase();
        const icon = this.getFileIcon(fileExt);
        
        item.innerHTML = `
            <div class="file-header">
                <div class="file-icon">
                    ${icon}
                </div>
                <div class="file-info">
                    <div class="file-name" title="${file.filename}">${file.filename}</div>
                    <div class="file-meta">
                        ${file.chunks_created ? `<span>${file.chunks_created} chunks</span>` : ''}
                        ${file.file_size_mb ? `<span>${file.file_size_mb} MB</span>` : ''}
                        ${file.total_characters ? `<span>${file.total_characters.toLocaleString()} chars</span>` : ''}
                    </div>
                </div>
                ${!file.temp ? `
                    <div class="file-actions">
                        <button 
                            class="file-action-btn" 
                            onclick="chatManager.removeFile('${file.filename}')"
                            title="Remove file"
                        >
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                            </svg>
                        </button>
                    </div>
                ` : ''}
            </div>
        `;
        
        return item;
    }

    getFileIcon(extension) {
        const icons = {
            'pdf': `
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path>
                </svg>
            `,
            'docx': `
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                </svg>
            `,
            'doc': `
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                </svg>
            `
        };
        
        return icons[extension] || icons['pdf'];
    }

    async removeFile(filename) {
        if (!confirm(`Remove "${filename}" from this session?`)) return;
        
        try {
            const response = await fetch(`/api/files/session/${this.sessionId}/file/${encodeURIComponent(filename)}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                this.uploadedFiles = this.uploadedFiles.filter(f => f.filename !== filename);
                this.updateFilesList();
                this.updateChatState();
                this.updateFileCounter();
                this.updateSettingsModal();
                this.showSuccess(`Removed "${filename}"`);
            } else {
                throw new Error('Failed to remove file');
            }
            
        } catch (error) {
            console.error('Error removing file:', error);
            this.showError('Failed to remove file');
        }
    }

    async clearAllFiles() {
        if (!confirm('Remove all files from this session?')) return;
        
        try {
            const response = await fetch(`/api/files/session/${this.sessionId}/clear`, {
                method: 'POST'
            });
            
            if (response.ok) {
                this.uploadedFiles = [];
                this.updateFilesList();
                this.updateChatState();
                this.updateFileCounter();
                this.updateSettingsModal();
                this.showSuccess('All files cleared');
            } else {
                throw new Error('Failed to clear files');
            }
            
        } catch (error) {
            console.error('Error clearing files:', error);
            this.showError('Failed to clear files');
        }
    }

    updateFilesList() {
        // Clear existing files (except temp ones)
        const existingFiles = this.filesList.querySelectorAll('.file-item:not([data-temp="true"])');
        existingFiles.forEach(item => item.remove());
        
        if (this.uploadedFiles.length === 0) {
            this.showEmptyState();
        } else {
            this.hideEmptyState();
            this.uploadedFiles.forEach(file => {
                const item = this.createFileItem(file);
                this.filesList.appendChild(item);
            });
        }
        
        // Update clear button
        this.clearAllBtn.disabled = this.uploadedFiles.length === 0;
    }

    showEmptyState() {
        this.emptyState.classList.remove('hidden');
    }

    hideEmptyState() {
        this.emptyState.classList.add('hidden');
    }

    updateFileCounter() {
        document.getElementById('fileCount').textContent = this.uploadedFiles.length;
    }

    updateChatState() {
        const hasFiles = this.uploadedFiles.length > 0;
        const canAskQuestions = this.questionCount < this.maxQuestions;
        
        this.chatInput.disabled = !hasFiles || !canAskQuestions;
        this.sendBtn.disabled = !hasFiles || !canAskQuestions || this.chatInput.value.trim() === '';
        
        if (!hasFiles) {
            this.chatInput.placeholder = 'Upload documents to start chatting...';
            document.getElementById('inputHint').classList.remove('hidden');
        } else if (!canAskQuestions) {
            this.chatInput.placeholder = 'Question limit reached for this session...';
            document.getElementById('inputHint').classList.add('hidden');
        } else {
            this.chatInput.placeholder = 'Ask a question about your documents...';
            document.getElementById('inputHint').classList.add('hidden');
        }
    }

    updateQuestionCounter() {
        const counter = document.getElementById('questionCount');
        counter.textContent = `${this.questionCount}/${this.maxQuestions} Questions`;
        
        const settingsCounter = document.getElementById('questionsUsed');
        settingsCounter.textContent = `${this.questionCount}/${this.maxQuestions}`;
    }

    updateSettingsModal() {
        document.getElementById('filesUploaded').textContent = 
            `${this.uploadedFiles.length}/${this.maxFiles}`;
    }

    handleChatInput() {
        const text = this.chatInput.value;
        const charCount = text.length;
        const maxChars = 500;
        
        // Update character counter
        document.getElementById('charCounter').textContent = charCount;
        
        // Update send button state
        this.sendBtn.disabled = text.trim() === '' || this.uploadedFiles.length === 0 || 
                                this.questionCount >= this.maxQuestions || this.isTyping;
        
        // Warn if approaching limit
        if (charCount > maxChars * 0.8) {
            document.getElementById('charCounter').style.color = '#e94560';
        } else {
            document.getElementById('charCounter').style.color = 'rgba(245, 245, 245, 0.4)';
        }
    }

    handleChatKeydown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!this.sendBtn.disabled) {
                this.sendMessage();
            }
        }
    }

    autoResizeTextarea() {
        const textarea = this.chatInput;
        textarea.style.height = 'auto';
        const newHeight = Math.min(textarea.scrollHeight, 128); // Max height of 128px
        textarea.style.height = newHeight + 'px';
    }

    async sendMessage() {
        const message = this.chatInput.value.trim();
        if (!message || this.isTyping) return;
        
        // Add user message
        this.addMessage('user', message);
        
        // Clear input
        this.chatInput.value = '';
        this.handleChatInput();
        this.autoResizeTextarea();
        
        // Show typing indicator
        this.showTypingIndicator();
        this.isTyping = true;
        
        try {
            const response = await fetch('/api/rag/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Session-ID': this.sessionId,
                    'X-API-Key': this.apiKey,
                    'X-Provider': this.provider
                },
                body: JSON.stringify({
                    question: message,
                    use_hybrid_search: true,
                    top_k: 5
                })
            });

            
            const data = await response.json();
            
            if (response.ok) {
                this.questionCount = data.question_count;
                this.updateQuestionCounter();
                this.updateChatState();
                
                // Add AI response
                this.addMessage('assistant', data.answer, data.sources);
                
            } else {
                throw new Error(data.detail || 'Failed to get response');
            }
            
        } catch (error) {
            console.error('Chat error:', error);
            this.addMessage('assistant', `Sorry, I encountered an error: ${error.message}`, [], true);
        } finally {
            this.hideTypingIndicator();
            this.isTyping = false;
            this.updateChatState();
        }
    }

    addMessage(type, content, sources = [], isError = false) {
        this.hideWelcomeMessage();
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        const avatar = type === 'user' ? this.username.charAt(0).toUpperCase() : 'AI';
        const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        let sourcesHtml = '';
        if (sources && sources.length > 0 && !isError) {
            const uniqueFiles = [...new Set(sources.map(s => s.filename))];
            sourcesHtml = `
                <div class="sources-info">
                    <div class="sources-title">Sources (${sources.length} chunks from ${uniqueFiles.length} file${uniqueFiles.length > 1 ? 's' : ''})</div>
                    ${uniqueFiles.map(filename => 
                        `<div class="source-item">📄 ${filename}</div>`
                    ).join('')}
                </div>
            `;
        }
        
        messageDiv.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                <div class="message-bubble ${isError ? 'error' : ''}">
                    <div class="message-text">${this.formatMessageContent(content, isError)}</div>
                </div>
                ${sourcesHtml}
                <div class="message-metadata">
                    <span>${timestamp}</span>
                    ${type === 'assistant' && sources && sources.length > 0 ? 
                        `<span>${sources.length} source${sources.length > 1 ? 's' : ''}</span>` : ''
                    }
                </div>
            </div>
        `;
        
        this.chatContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    formatMessageContent(content, isError = false) {
        if (isError) {
            return `<span style="color: #e94560;">${content}</span>`;
        }
        
        // Basic markdown-like formatting
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');
    }

    showTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'message assistant typing-indicator-container';
        indicator.innerHTML = `
            <div class="message-avatar">AI</div>
            <div class="message-content">
                <div class="typing-indicator">
                    <div class="typing-dots">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                    <span class="ml-3 text-pearl/60 text-sm">Thinking...</span>
                </div>
            </div>
        `;
        
        this.chatContainer.appendChild(indicator);
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        const indicator = this.chatContainer.querySelector('.typing-indicator-container');
        if (indicator) {
            indicator.remove();
        }
    }

    hideWelcomeMessage() {
        if (this.welcomeMessage && !this.welcomeMessage.classList.contains('hidden')) {
            this.welcomeMessage.style.opacity = '0';
            this.welcomeMessage.style.transform = 'translateY(-20px)';
            setTimeout(() => {
                this.welcomeMessage.classList.add('hidden');
            }, 300);
        }
    }

    scrollToBottom() {
        setTimeout(() => {
            this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
        }, 100);
    }

    showUploadProgress(show, percentage = 0) {
        if (show) {
            this.uploadProgress.classList.remove('hidden');
            document.getElementById('uploadProgressFill').style.width = percentage + '%';
            document.getElementById('uploadPercentage').textContent = Math.round(percentage) + '%';
        } else {
            this.uploadProgress.classList.add('hidden');
        }
    }

    showSuccess(message) {
        this.showToast(message, 'success');
    }

    showError(message) {
        this.showToast(message, 'error');
    }

    showWarning(message) {
        this.showToast(message, 'warning');
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 max-w-md text-sm font-medium transition-all duration-300 transform translate-x-full`;
        
        const colors = {
            success: 'bg-moss/90 border border-moss/50 text-pearl',
            error: 'bg-amber/90 border border-amber/50 text-pearl',
            warning: 'bg-orange-500/90 border border-orange-500/50 text-pearl',
            info: 'bg-ocean/90 border border-ocean/50 text-pearl'
        };
        
        toast.className += ' ' + colors[type];
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        // Animate in
        setTimeout(() => {
            toast.classList.remove('translate-x-full');
        }, 100);
        
        // Auto remove
        setTimeout(() => {
            toast.classList.add('translate-x-full');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 5000);
    }
}

// Global functions for window access
function showSettings() {
    document.getElementById('settingsModal').classList.remove('hidden');
}

function hideSettings() {
    document.getElementById('settingsModal').classList.add('hidden');
}

function newSession() {
    if (confirm('Start a new session? This will clear all uploaded files and chat history.')) {
        sessionStorage.clear();
        window.location.href = '/';
    }
}

// Initialize chat manager
let chatManager;
document.addEventListener('DOMContentLoaded', () => {
    chatManager = new ChatManager();
});

// Handle page unload
window.addEventListener('beforeunload', (e) => {
    if (chatManager && chatManager.uploadedFiles.length > 0) {
        e.preventDefault();
        e.returnValue = 'You have uploaded files in this session. Are you sure you want to leave?';
        return e.returnValue;
    }
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + K to focus chat input
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        if (chatManager && chatManager.chatInput && !chatManager.chatInput.disabled) {
            chatManager.chatInput.focus();
        }
    }
    
    // Escape to close settings
    if (e.key === 'Escape') {
        hideSettings();
    }
});
