const API_BASE = '/api';

const app = {
    data: {
        snippets: {},
        shortcuts: {},
        commands: {}
    },

    init() {
        this.setupNavigation();
        this.loadData();
    },

    setupNavigation() {
        const navItems = document.querySelectorAll('nav li');
        navItems.forEach(item => {
            item.addEventListener('click', () => {
                // Update active state
                navItems.forEach(n => n.classList.remove('active'));
                item.classList.add('active');

                // Show target section
                const targetId = item.getAttribute('data-target');
                document.querySelectorAll('.tab-content').forEach(s => s.classList.remove('active'));
                document.getElementById(targetId).classList.add('active');
            });
        });
    },

    async loadData() {
        try {
            const [snipRes, shortRes, cmdRes] = await Promise.all([
                fetch(`${API_BASE}/snippets`),
                fetch(`${API_BASE}/shortcuts`),
                fetch(`${API_BASE}/commands`)
            ]);

            this.data.snippets = await snipRes.json();
            this.data.shortcuts = await shortRes.json();
            this.data.commands = await cmdRes.json();

            this.renderEditor('snippets-editor', this.data.snippets);
            this.renderEditor('shortcuts-editor', this.data.shortcuts);
            this.renderEditor('commands-editor', this.data.commands);
        } catch (error) {
            this.showToast('Failed to load configuration data', true);
            console.error(error);
        }
    },

    renderEditor(containerId, dataObj) {
        const container = document.getElementById(containerId);
        container.innerHTML = '';
        
        Object.entries(dataObj).forEach(([key, value]) => {
            this.createRow(container, key, value);
        });
    },

    createRow(container, key = '', value = '') {
        const row = document.createElement('div');
        row.className = 'kv-pair';
        
        const keyInput = document.createElement('input');
        keyInput.className = 'key-input';
        keyInput.value = key;
        keyInput.placeholder = 'Key';
        // Now key is editable

        const valInput = document.createElement('input');
        valInput.className = 'val-input';
        valInput.value = typeof value === 'object' ? JSON.stringify(value) : value;
        valInput.placeholder = 'Value';

        const removeBtn = document.createElement('button');
        removeBtn.className = 'btn-remove';
        removeBtn.textContent = 'Remove';
        removeBtn.onclick = () => row.remove();

        const saveBtn = document.createElement('button');
        saveBtn.className = 'btn-save-row';
        saveBtn.textContent = '✓';
        saveBtn.title = 'Save';
        saveBtn.onclick = () => {
            if (container.id === 'snippets-editor') this.saveSnippets();
            else if (container.id === 'shortcuts-editor') this.saveShortcuts();
            else if (container.id === 'commands-editor') this.saveCommands();
        };

        row.appendChild(keyInput);
        row.appendChild(valInput);
        row.appendChild(saveBtn);
        row.appendChild(removeBtn);
        container.appendChild(row);
        
        return keyInput;
    },

    addEntry(containerId) {
        const container = document.getElementById(containerId);
        const keyInput = this.createRow(container);
        keyInput.focus();
    },

    getDataFromEditor(containerId) {
        const container = document.getElementById(containerId);
        const rows = container.querySelectorAll('.kv-pair');
        const newData = {};
        
        rows.forEach(row => {
            const key = row.querySelector('.key-input').value.trim();
            if (!key) return; // Skip empty keys
            let val = row.querySelector('.val-input').value;
            try {
                // Parse arrays/nulls if it's commands
                if (val === "null") val = null;
                else if (val.startsWith('[')) val = JSON.parse(val);
            } catch(e) {}
            newData[key] = val;
        });
        return newData;
    },

    async saveData(endpoint, dataObj) {
        try {
            const res = await fetch(`${API_BASE}/${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ data: dataObj })
            });
            if (res.ok) {
                this.showToast('Changes saved successfully');
            } else {
                throw new Error('Server returned ' + res.status);
            }
        } catch(error) {
            this.showToast('Failed to save changes', true);
            console.error(error);
        }
    },

    async saveSnippets() {
        const data = this.getDataFromEditor('snippets-editor');
        await this.saveData('snippets', data);
    },

    async saveShortcuts() {
        const data = this.getDataFromEditor('shortcuts-editor');
        await this.saveData('shortcuts', data);
    },

    async saveCommands() {
        const data = this.getDataFromEditor('commands-editor');
        await this.saveData('commands', data);
    },

    toggleMenuSidebar() {
        const sidebar = document.querySelector('.sidebar');
        sidebar.classList.toggle('collapsed');
    },

    toggleAISidebar() {
        const sidebar = document.querySelector('.ai-sidebar');
        sidebar.classList.toggle('collapsed');
    },

    initResizers() {
        const leftResizer = document.getElementById('left-resizer');
        const rightResizer = document.getElementById('right-resizer');
        const leftSidebar = document.querySelector('.sidebar');
        const rightSidebar = document.querySelector('.ai-sidebar');
        const body = document.body;

        let isResizingLeft = false;
        let isResizingRight = false;

        leftResizer.addEventListener('mousedown', (e) => {
            isResizingLeft = true;
            body.style.cursor = 'col-resize';
            leftSidebar.style.transition = 'none'; // Disable transition while dragging
        });

        rightResizer.addEventListener('mousedown', (e) => {
            isResizingRight = true;
            body.style.cursor = 'col-resize';
            rightSidebar.style.transition = 'none';
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizingLeft && !isResizingRight) return;

            if (isResizingLeft) {
                // Ensure min width
                const newWidth = Math.max(150, e.clientX);
                leftSidebar.style.width = `${newWidth}px`;
            }

            if (isResizingRight) {
                const newWidth = Math.max(200, window.innerWidth - e.clientX);
                rightSidebar.style.width = `${newWidth}px`;
            }
        });

        document.addEventListener('mouseup', () => {
            if (isResizingLeft) {
                isResizingLeft = false;
                leftSidebar.style.transition = ''; // Restore CSS transition
            }
            if (isResizingRight) {
                isResizingRight = false;
                rightSidebar.style.transition = '';
            }
            body.style.cursor = 'default';
        });
    },

    currentAIPromptController: null,

    async sendAIPrompt() {
        const input = document.getElementById('ai-prompt');
        const prompt = input.value.trim();
        if (!prompt) return;

        this.appendMessage('user', prompt);
        input.value = '';
        
        const loadingId = this.appendMessage('system', 'Processing Request with Groq...');
        
        // Show stop button, hide exec
        document.getElementById('ai-exec-btn').style.display = 'none';
        document.getElementById('ai-stop-btn').style.display = 'block';

        this.currentAIPromptController = new AbortController();
        const signal = this.currentAIPromptController.signal;

        try {
            const res = await fetch(`${API_BASE}/ai/code`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt }),
                signal
            });
            const result = await res.json();
            
            const msgEl = document.getElementById(loadingId);
            if (res.ok) {
                msgEl.textContent = `Success: ${result.message}`;
            } else {
                msgEl.textContent = `Error: ${result.detail}`;
            }
        } catch(error) {
            const msgEl = document.getElementById(loadingId);
            if (error.name === 'AbortError') {
                msgEl.textContent = 'Request stopped by user.';
            } else {
                msgEl.textContent = 'Connection Error: Failed to reach AI backend.';
                console.error(error);
            }
        } finally {
            this.currentAIPromptController = null;
            document.getElementById('ai-exec-btn').style.display = 'block';
            document.getElementById('ai-stop-btn').style.display = 'none';
        }
    },

    stopAIPrompt() {
        if (this.currentAIPromptController) {
            this.currentAIPromptController.abort();
        }
    },

    appendMessage(role, text) {
        const history = document.getElementById('ai-history');
        const msgDiv = document.createElement('div');
        msgDiv.className = `ai-message ${role}`;
        msgDiv.textContent = text;
        const id = 'msg-' + Date.now();
        msgDiv.id = id;
        history.appendChild(msgDiv);
        history.scrollTop = history.scrollHeight;
        return id;
    },

    showToast(message, isError = false) {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.className = 'toast show ' + (isError ? 'error' : '');
        setTimeout(() => {
            toast.className = 'toast';
        }, 3000);
    }
};

document.addEventListener('DOMContentLoaded', () => {
    app.init();
    app.initResizers();
});