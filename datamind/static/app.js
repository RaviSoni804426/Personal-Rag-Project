// DataMind Frontend Application

const API_BASE = '/api';

// State Management
const state = {
    messages: [],
    documents: [],
    stats: {},
    topK: 5,
    threshold: 0
};

// DOM Elements
const messagesBox = document.getElementById('messagesBox');
const queryInput = document.getElementById('queryInput');
const sendBtn = document.getElementById('sendBtn');
const fileInput = document.getElementById('fileInput');
const uploadBtn = document.getElementById('uploadBtn');
const uploadArea = document.getElementById('uploadArea');
const searchQuery = document.getElementById('searchQuery');
const searchBtn = document.getElementById('searchBtn');
const searchResults = document.getElementById('searchResults');
const documentsList = document.getElementById('documentsList');
const noDocuments = document.getElementById('noDocuments');
const topKInput = document.getElementById('topK');
const thresholdInput = document.getElementById('threshold');
const navButtons = document.querySelectorAll('.nav-button');
const tabContents = document.querySelectorAll('.tab-content');
const statusIndicator = document.getElementById('statusIndicator');
const statusText = document.getElementById('statusText');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    checkHealth();
    loadDocuments();
    loadStats();
    setInterval(checkHealth, 30000); // Check health every 30 seconds
});

// Event Listeners
function setupEventListeners() {
    // Chat
    sendBtn.addEventListener('click', sendMessage);
    queryInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Search
    searchBtn.addEventListener('click', performSearch);
    searchQuery.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            performSearch();
        }
    });

    // Upload
    uploadBtn.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.style.borderColor = 'var(--primary-color)';
    });
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.style.borderColor = 'var(--border-color)';
    });
    uploadArea.addEventListener('drop', handleFileDrop);
    fileInput.addEventListener('change', handleFileSelect);

    // Navigation
    navButtons.forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // Settings
    topKInput.addEventListener('change', (e) => {
        state.topK = parseInt(e.target.value);
    });
    thresholdInput.addEventListener('change', (e) => {
        state.threshold = parseFloat(e.target.value);
    });
}

// Chat Functions
async function sendMessage() {
    const message = queryInput.value.trim();
    if (!message) return;

    // Add user message to chat
    addMessage('user', message);
    queryInput.value = '';

    try {
        sendBtn.disabled = true;
        const response = await fetch(`${API_BASE}/chat/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                top_k: state.topK
            })
        });

        const data = await response.json();

        if (!response.ok) {
            addMessage('system', `Error: ${data.detail || 'Failed to get response'}`);
            return;
        }

        // Add assistant response
        if (data.assistant_response) {
            addMessage('assistant', data.assistant_response);
        } else {
            addMessage('assistant', 'No LLM response available. Retrieved documents are shown below.');
        }

        // Show retrieved context
        if (data.retrieved_context && data.retrieved_context.length > 0) {
            showRetrievedInfo(data.retrieved_context);
        }
    } catch (error) {
        addMessage('system', `Error: ${error.message}`);
    } finally {
        sendBtn.disabled = false;
    }
}

function addMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    if (role === 'assistant' || role === 'user') {
        contentDiv.textContent = content;
    } else {
        contentDiv.textContent = content;
    }
    
    messageDiv.appendChild(contentDiv);
    messagesBox.appendChild(messageDiv);
    messagesBox.scrollTop = messagesBox.scrollHeight;
    
    state.messages.push({ role, content });
}

function showRetrievedInfo(results) {
    const retrievedInfo = document.getElementById('retrievedInfo');
    const retrievedList = document.getElementById('retrievedList');
    retrievedList.innerHTML = '';
    
    results.forEach((result, idx) => {
        const item = document.createElement('div');
        item.className = 'result-card';
        item.innerHTML = `
            <h3>${result.filename}</h3>
            <p>${result.text.substring(0, 200)}...</p>
            <div class="score">
                Similarity: ${(result.similarity_score * 100).toFixed(1)}%
            </div>
        `;
        retrievedList.appendChild(item);
    });
    
    retrievedInfo.style.display = 'block';
}

// Search Functions
async function performSearch() {
    const query = searchQuery.value.trim();
    if (!query) return;

    try {
        searchBtn.disabled = true;
        searchResults.innerHTML = '<p>Searching...</p>';

        const response = await fetch(`${API_BASE}/documents/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: query,
                top_k: state.topK,
                similarity_threshold: state.threshold
            })
        });

        const data = await response.json();

        if (!response.ok) {
            searchResults.innerHTML = `<p>Error: ${data.detail || 'Search failed'}</p>`;
            return;
        }

        if (data.results.length === 0) {
            searchResults.innerHTML = '<p>No results found</p>';
            return;
        }

        searchResults.innerHTML = data.results.map(result => `
            <div class="result-card">
                <h3>${result.filename}</h3>
                <p>${result.text.substring(0, 300)}...</p>
                <div class="score">
                    Similarity: ${(result.similarity_score * 100).toFixed(1)}%
                </div>
            </div>
        `).join('');
    } catch (error) {
        searchResults.innerHTML = `<p>Error: ${error.message}</p>`;
    } finally {
        searchBtn.disabled = false;
    }
}

// Document Functions
async function loadDocuments() {
    try {
        const response = await fetch(`${API_BASE}/documents/`);
        const data = await response.json();
        
        state.documents = Array.isArray(data) ? data : [];
        
        if (state.documents.length === 0) {
            noDocuments.style.display = 'block';
            documentsList.innerHTML = '';
        } else {
            noDocuments.style.display = 'none';
            renderDocuments();
        }
    } catch (error) {
        console.error('Failed to load documents:', error);
    }
}

function renderDocuments() {
    documentsList.innerHTML = state.documents.map(doc => `
        <div class="doc-card">
            <h3>${doc.filename}</h3>
            <p>${doc.text.substring(0, 100)}...</p>
            <div class="meta">
                <span class="type">${doc.doc_type}</span>
                <span>${doc.char_count} chars</span>
            </div>
            <button class="btn btn-secondary" onclick="deleteDocument(${doc.id})">Delete</button>
        </div>
    `).join('');
}

async function deleteDocument(docId) {
    if (!confirm('Delete this document?')) return;
    
    try {
        const response = await fetch(`${API_BASE}/documents/${docId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            loadDocuments();
            loadStats();
        }
    } catch (error) {
        console.error('Failed to delete document:', error);
    }
}

// File Upload Functions
function handleFileDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    const files = e.dataTransfer.files;
    uploadFiles(files);
}

function handleFileSelect(e) {
    uploadFiles(e.target.files);
}

async function uploadFiles(files) {
    if (!files || files.length === 0) return;

    const uploadStatus = document.getElementById('uploadStatus');
    uploadStatus.textContent = `Uploading ${files.length} file(s)...`;

    const formData = new FormData();
    for (let file of files) {
        formData.append('files', file);
    }

    try {
        const response = await fetch(`${API_BASE}/documents/upload`, {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            uploadStatus.textContent = `✓ ${files.length} file(s) uploaded successfully`;
            fileInput.value = '';
            loadDocuments();
            loadStats();
            setTimeout(() => {
                uploadStatus.textContent = '';
            }, 3000);
        } else {
            const data = await response.json();
            uploadStatus.textContent = `✗ Error: ${data.detail || 'Upload failed'}`;
        }
    } catch (error) {
        uploadStatus.textContent = `✗ Error: ${error.message}`;
    }
}

// Analytics Functions
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/documents/stats`);
        const data = await response.json();
        
        state.stats = data;
        
        document.getElementById('statDocs').textContent = data.total_documents;
        document.getElementById('statChars').textContent = (data.total_characters / 1024).toFixed(1) + ' KB';
        document.getElementById('statAvg').textContent = (data.avg_document_size / 1024).toFixed(1) + ' KB';
        
        const types = Object.keys(data.document_types || {}).join(', ') || 'N/A';
        document.getElementById('statTypes').textContent = types;
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// Navigation Functions
function switchTab(tabName) {
    // Update active button
    navButtons.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    
    // Update active content
    tabContents.forEach(content => {
        content.classList.toggle('active', content.id === `${tabName}Tab`);
    });
    
    // Refresh data when switching tabs
    if (tabName === 'documents') {
        loadDocuments();
    } else if (tabName === 'analytics') {
        loadStats();
    }
}

// Health Check
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE}/health/`);
        const data = await response.json();
        
        const isHealthy = data.status === 'healthy';
        statusIndicator.style.backgroundColor = isHealthy ? '#10b981' : '#f59e0b';
        statusText.textContent = isHealthy ? 'Connected' : 'Degraded';
    } catch (error) {
        statusIndicator.style.backgroundColor = '#ef4444';
        statusText.textContent = 'Offline';
    }
}
