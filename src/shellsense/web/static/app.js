const API_BASE = '/api';

/**
 * Zero-Knowledge Client-Side Web Vault
 * Implements PBKDF2-HMAC-SHA256 (100,000 iterations) + AES-GCM-256.
 * The Master Password and raw secrets never leave the browser.
 */
const WebVault = {
    bufferToBase64(buf) {
        const bytes = new Uint8Array(buf);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    },

    base64ToBuffer(b64) {
        const binary = atob(b64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
        }
        return bytes;
    },

    async deriveKey(password, salt) {
        const enc = new TextEncoder();
        const pwKey = await crypto.subtle.importKey(
            'raw',
            enc.encode(password),
            'PBKDF2',
            false,
            ['deriveKey']
        );
        return await crypto.subtle.deriveKey(
            {
                name: 'PBKDF2',
                salt: salt,
                iterations: 100000,
                hash: 'SHA-256'
            },
            pwKey,
            { name: 'AES-GCM', length: 256 },
            false,
            ['encrypt', 'decrypt']
        );
    },

    async encrypt(plainText, masterPassword) {
        if (!plainText || !masterPassword) return plainText;
        const salt = crypto.getRandomValues(new Uint8Array(16));
        const iv = crypto.getRandomValues(new Uint8Array(12));
        const key = await this.deriveKey(masterPassword, salt);
        const enc = new TextEncoder();
        const cipherBuffer = await crypto.subtle.encrypt(
            { name: 'AES-GCM', iv: iv },
            key,
            enc.encode(plainText)
        );
        const saltB64 = this.bufferToBase64(salt);
        const ivB64 = this.bufferToBase64(iv);
        const cipherB64 = this.bufferToBase64(cipherBuffer);
        return `ENC:GCM:${saltB64}:${ivB64}:${cipherB64}`;
    },

    async decrypt(encValue, masterPassword) {
        if (!encValue || !encValue.startsWith('ENC:GCM:')) {
            throw new Error('Unsupported or legacy vault format. Please unlock on desktop to migrate.');
        }
        const parts = encValue.slice('ENC:GCM:'.length).split(':');
        if (parts.length !== 3) {
            throw new Error('Invalid vault ciphertext structure');
        }
        const [saltB64, ivB64, cipherB64] = parts;
        const salt = this.base64ToBuffer(saltB64);
        const iv = this.base64ToBuffer(ivB64);
        const cipherBytes = this.base64ToBuffer(cipherB64);
        const key = await this.deriveKey(masterPassword, salt);
        const decryptedBuf = await crypto.subtle.decrypt(
            { name: 'AES-GCM', iv: iv },
            key,
            cipherBytes
        );
        const dec = new TextDecoder();
        return dec.decode(decryptedBuf);
    }
};

const app = {
    data: {
        snippets: {},
        shortcuts: {},
        commands: {}
    },


    closeModal() {
        const modal = document.getElementById('vault-modal');
        if (modal) modal.style.display = 'none';
        const passInput = document.getElementById('modal-password');
        if (passInput) {
            passInput.value = '';
            passInput.onkeydown = null;
        }
        if (this._modalResolver) {
            const resolve = this._modalResolver;
            this._modalResolver = null;
            resolve(null);
        }
    },

    async customPrompt(title, desc) {
        return new Promise((resolve) => {
            const modal = document.getElementById('vault-modal');
            const titleEl = document.getElementById('modal-title');
            const descEl = document.getElementById('modal-desc');
            const passInput = document.getElementById('modal-password');
            const confirmBtn = document.getElementById('modal-confirm');

            if (titleEl) titleEl.textContent = title;
            if (descEl) descEl.textContent = desc;
            if (modal) modal.style.display = 'flex';
            if (passInput) {
                passInput.value = '';
                passInput.focus();
            }

            this._modalResolver = resolve;

            const handleConfirm = () => {
                const val = passInput ? passInput.value : '';
                this._modalResolver = null;
                this.closeModal();
                if (confirmBtn) confirmBtn.onclick = null;
                resolve(val || null);
            };

            if (confirmBtn) {
                confirmBtn.onclick = handleConfirm;
            }
            if (passInput) {
                passInput.onkeydown = (e) => {
                    if (e.key === 'Enter') handleConfirm();
                    if (e.key === 'Escape') this.closeModal();
                };
            }
        });
    },

    init() {
        this.setupNavigation();
        this.loadData();
        this.initPalette();
        this.loadSqliteRecords();
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

        const valInput = document.createElement('input');
        valInput.className = 'val-input';
        valInput.value = typeof value === 'object' ? JSON.stringify(value) : value;

        if (container.id === 'snippets-editor') {
            keyInput.placeholder = 'e.g., React Component';
            valInput.placeholder = 'e.g., function Component() { return <div />; }';
        } else if (container.id === 'shortcuts-editor') {
            keyInput.placeholder = 'e.g., Ctrl+Shift+P';
            valInput.placeholder = 'e.g., Open Palette';
        } else if (container.id === 'commands-editor') {
            keyInput.placeholder = 'e.g., git commit -am "Update"';
            valInput.placeholder = 'e.g., Commits all changes';
        } else {
            keyInput.placeholder = 'Key';
            valInput.placeholder = 'Value';
        }

        if ((container.id === 'snippets-editor' || container.id === 'shortcuts-editor') && String(valInput.value).startsWith('ENC:')) {
            valInput.classList.add('is-encrypted');
            valInput.readOnly = true;
            valInput.setAttribute('readonly', 'true');
        }

        // Strict immutability protection for encrypted fields
        valInput.addEventListener('keydown', (e) => {
            if (valInput.classList.contains('is-encrypted') || valInput.readOnly) {
                if ((e.ctrlKey || e.metaKey) && (e.key === 'c' || e.key === 'a')) {
                    return; // Allow select-all and copy
                }
                e.preventDefault();
                return false;
            }
        });
        valInput.addEventListener('paste', (e) => {
            if (valInput.classList.contains('is-encrypted') || valInput.readOnly) {
                e.preventDefault();
            }
        });
        valInput.addEventListener('cut', (e) => {
            if (valInput.classList.contains('is-encrypted') || valInput.readOnly) {
                e.preventDefault();
            }
        });

        const saveBtn = document.createElement('button');
        saveBtn.className = 'btn-save-row';
        saveBtn.textContent = '✓';
        saveBtn.title = 'Save';
        saveBtn.onclick = () => {
            if (container.id === 'snippets-editor') this.saveSnippets();
            else if (container.id === 'shortcuts-editor') this.saveShortcuts();
            else if (container.id === 'commands-editor') this.saveCommands();
        };

        const removeBtn = document.createElement('button');
        removeBtn.className = 'btn-remove';
        removeBtn.textContent = 'Remove';
        removeBtn.onclick = () => row.remove();

        row.appendChild(keyInput);
        row.appendChild(valInput);

        // Add Vault toggle button for snippets and shortcuts
        if (container.id === 'snippets-editor' || container.id === 'shortcuts-editor') {
            const vaultBtn = document.createElement('button');
            const isEnc = String(valInput.value).startsWith('ENC:');
            vaultBtn.className = isEnc ? 'btn-vault locked' : 'btn-vault';
            vaultBtn.textContent = isEnc ? '🔒 Locked' : '🔓 Protect';
            vaultBtn.title = isEnc ? 'Click to decrypt and view/edit' : 'Click to encrypt with Master Password';

            vaultBtn.onclick = async () => {
                const currentVal = valInput.value.trim();
                if (currentVal.startsWith('ENC:')) {
                    const pass = await this.customPrompt('Decrypt Entry', 'Enter Master Password to view this secret');
                    if (!pass) return;
                    try {
                        const decrypted = await WebVault.decrypt(currentVal, pass);
                        valInput.value = decrypted;
                        valInput.classList.remove('is-encrypted');
                        valInput.readOnly = false;
                        vaultBtn.className = 'btn-vault';
                        vaultBtn.textContent = '🔓 Protect';
                        vaultBtn.title = 'Click to encrypt with Master Password';
                        app.showToast('Decrypted client-side! Password never sent to server.');
                    } catch(err) {
                        app.showToast(err.message || 'Incorrect master password', true);
                    }
                } else {
                    if (!currentVal) {
                        app.showToast('Please enter a value to encrypt', true);
                        return;
                    }
                    const pass = await this.customPrompt('Protect Entry', 'Enter Master Password to encrypt this secret');
                    if (!pass) return;
                    try {
                        const encrypted = await WebVault.encrypt(currentVal, pass);
                        valInput.value = encrypted;
                        valInput.classList.add('is-encrypted');
                        valInput.readOnly = true;
                        vaultBtn.className = 'btn-vault locked';
                        vaultBtn.textContent = '🔒 Locked';
                        vaultBtn.title = 'Click to decrypt and view/edit';
                        app.showToast('Encrypted client-side (AES-GCM-256)! Click Save Changes to store.');
                    } catch(err) {
                        app.showToast('Client-side encryption failed: ' + err.message, true);
                    }
                }
            };
            row.appendChild(vaultBtn);
        }

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

    async lockAll(containerId) {
        const pass = await this.customPrompt('Lock Vault', 'Encrypt all visible items with your Master Password');
        if (!pass) return;
        
        const container = document.getElementById(containerId);
        const rows = container.querySelectorAll('.kv-pair');
        let lockedCount = 0;
        
        for (const row of rows) {
            const valInput = row.querySelector('.val-input');
            const vaultBtn = row.querySelector('.btn-vault');
            if (valInput && vaultBtn && !valInput.classList.contains('is-encrypted')) {
                const currentVal = valInput.value.trim();
                if (currentVal) {
                    try {
                        const encrypted = await WebVault.encrypt(currentVal, pass);
                        valInput.value = encrypted;
                        valInput.classList.add('is-encrypted');
                        valInput.readOnly = true;
                        vaultBtn.className = 'btn-vault locked';
                        vaultBtn.textContent = '🔒 Locked';
                        vaultBtn.title = 'Click to decrypt and view/edit';
                        lockedCount++;
                    } catch (err) {
                        console.error("Failed to encrypt:", err);
                    }
                }
            }
        }
        if (lockedCount > 0) {
            app.showToast(`Encrypted ${lockedCount} items client-side! Saving...`);
            if (containerId === 'snippets-editor') await this.saveSnippets();
            else if (containerId === 'shortcuts-editor') await this.saveShortcuts();
        } else {
            app.showToast('No items to encrypt.');
        }
    },

    async unlockAll(containerId) {
        const pass = await this.customPrompt('Unlock Vault', 'Enter your Master Password to decrypt items');
        if (!pass) return;
        
        const container = document.getElementById(containerId);
        const rows = container.querySelectorAll('.kv-pair');
        let unlockedCount = 0;
        
        for (const row of rows) {
            const valInput = row.querySelector('.val-input');
            const vaultBtn = row.querySelector('.btn-vault');
            if (valInput && vaultBtn && valInput.classList.contains('is-encrypted')) {
                const currentVal = valInput.value.trim();
                if (currentVal.startsWith('ENC:')) {
                    try {
                        const decrypted = await WebVault.decrypt(currentVal, pass);
                        valInput.value = decrypted;
                        valInput.classList.remove('is-encrypted');
                        valInput.readOnly = false;
                        vaultBtn.className = 'btn-vault';
                        vaultBtn.textContent = '🔓 Protect';
                        vaultBtn.title = 'Click to encrypt with Master Password';
                        unlockedCount++;
                    } catch (err) {
                        console.error("Failed to decrypt:", err);
                    }
                }
            }
        }
        if (unlockedCount > 0) {
            app.showToast(`Decrypted ${unlockedCount} items client-side! Saving...`);
            if (containerId === 'snippets-editor') await this.saveSnippets();
            else if (containerId === 'shortcuts-editor') await this.saveShortcuts();
        } else {
            app.showToast('Incorrect password or no items to decrypt.', true);
        }
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

    initResizers() {
        const leftResizer = document.getElementById('left-resizer');
        const leftSidebar = document.querySelector('.sidebar');
        const body = document.body;

        if (!leftResizer || !leftSidebar) return;

        let isResizingLeft = false;

        leftResizer.addEventListener('mousedown', (e) => {
            isResizingLeft = true;
            body.style.cursor = 'col-resize';
            leftSidebar.style.transition = 'none'; // Disable transition while dragging
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizingLeft) return;

            // Ensure min width
            const newWidth = Math.max(150, e.clientX);
            leftSidebar.style.width = `${newWidth}px`;
        });

        document.addEventListener('mouseup', () => {
            if (isResizingLeft) {
                isResizingLeft = false;
                leftSidebar.style.transition = ''; // Restore CSS transition
            }
            body.style.cursor = 'default';
        });
    },

    showToast(message, isError = false) {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.className = 'toast show ' + (isError ? 'error' : '');
        setTimeout(() => {
            toast.className = 'toast';
        }, 3000);
    },

    copyToClipboard(text, message = 'Copied to clipboard!') {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(() => {
                this.showToast(message);
            }).catch(() => {
                this.fallbackCopyText(text, message);
            });
        } else {
            this.fallbackCopyText(text, message);
        }
    },

    fallbackCopyText(text, message) {
        const tempInput = document.createElement('textarea');
        tempInput.value = text;
        tempInput.style.position = 'fixed';
        tempInput.style.opacity = '0';
        document.body.appendChild(tempInput);
        tempInput.select();
        try {
            document.execCommand('copy');
            this.showToast(message);
        } catch (e) {
            this.showToast('Failed to copy text', true);
        }
        document.body.removeChild(tempInput);
    },

    sendEmail(email = 'vrk1711@gmail.com', subject = 'ShellSense Support Request') {
        const mailtoUrl = `mailto:${email}?subject=${encodeURIComponent(subject)}`;
        window.location.href = mailtoUrl;
    },

    openGmail(email = 'vrk1711@gmail.com', subject = 'ShellSense Support Request') {
        const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(email)}&su=${encodeURIComponent(subject)}`;
        window.open(gmailUrl, '_blank', 'noopener,noreferrer');
    },

    // --- AI Command Palette & Tokenized Bar Logic ---
    paletteState: {
        mode: 'IDLE', // 'IDLE', 'PASSWORD_KEY', 'PASSWORD_VAL', 'FILE_NAME', 'COMMAND_PROMPT'
        tokens: [],
        collected: {},
        debounceTimer: null,
        candidates: [],
        currentResult: null
    },

    initPalette() {
        const input = document.getElementById('palette-input');
        if (!input) return;

        input.addEventListener('input', (e) => this.onPaletteInput(e.target.value));
        input.addEventListener('keydown', (e) => this.onPaletteKeydown(e));
    },

    setPaletteExample(text) {
        const input = document.getElementById('palette-input');
        if (!input) return;
        input.value = text;
        input.focus();
        this.onPaletteInput(text);
    },

    onPaletteInput(val) {
        clearTimeout(this.paletteState.debounceTimer);
        const trimmed = val.trim();
        const dropdown = document.getElementById('palette-dropdown');

        if (!trimmed) {
            if (dropdown) dropdown.style.display = 'none';
            return;
        }

        // 1. Slash actions
        if (this.paletteState.mode === 'IDLE' && trimmed.startsWith('/')) {
            const matches = [
                { label: '🔒 /vault — Store encrypted secret password in SQLite', mode: 'PASSWORD_KEY', token: 'Vault' },
                { label: '📁 /file — Create fast file launcher shortcut', mode: 'FILE_NAME', token: 'File' },
                { label: '⚡ /command — Execute & store terminal command', mode: 'COMMAND_PROMPT', token: 'Command' }
            ].filter(m => m.label.toLowerCase().includes(trimmed.toLowerCase()));

            this.renderPaletteDropdown(matches.map(m => ({
                label: m.label,
                action: () => this.selectPaletteMode(m.mode, m.token)
            })));
            return;
        }

        // 2. IDLE mode natural language -> AI Intent classification
        if (this.paletteState.mode === 'IDLE' && this.paletteState.tokens.length === 0 && trimmed.length >= 2) {
            this.showPaletteLoader('⚡ Analyzing natural language intent...');
            this.paletteState.debounceTimer = setTimeout(() => this.fetchIntentCandidates(trimmed), 120);
            return;
        }

        // 3. COMMAND_PROMPT mode free-form command -> AI Shell syntax synthesis
        if (this.paletteState.mode === 'COMMAND_PROMPT' && trimmed.length >= 3 && !trimmed.includes('=')) {
            this.showPaletteLoader('⚡ Generating verified shell syntax...');
            this.paletteState.debounceTimer = setTimeout(() => this.fetchShellSyntax(trimmed), 150);
            return;
        }

        if (dropdown) dropdown.style.display = 'none';
    },

    showPaletteLoader(msg) {
        const dropdown = document.getElementById('palette-dropdown');
        if (!dropdown) return;
        dropdown.innerHTML = `<div class="dropdown-item" style="color: #93c5fd; font-style: italic;">${msg}</div>`;
        dropdown.style.display = 'block';
    },

    async fetchIntentCandidates(query) {
        try {
            const res = await fetch(`${API_BASE}/ai/classify`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query, top_k: 5 })
            });
            if (!res.ok) return;
            const data = await res.json();
            const candidates = data.candidates || [];
            if (!candidates.length) {
                const dropdown = document.getElementById('palette-dropdown');
                if (dropdown) dropdown.style.display = 'none';
                return;
            }

            this.renderPaletteDropdown(candidates.map(c => ({
                label: `${c.icon || '⚡'} ${c.title} — <code>${c.command}</code>`,
                confidence: Math.round((c.confidence || 0.8) * 100),
                action: () => this.acceptIntentCandidate(c)
            })));
        } catch (e) {
            console.error('AI classify error:', e);
        }
    },

    async fetchShellSyntax(prompt) {
        try {
            const res = await fetch(`${API_BASE}/ai/synthesize`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: prompt })
            });
            if (!res.ok) return;
            const data = await res.json();
            const syntax = data.syntax;
            if (!syntax) return;

            this.renderPaletteDropdown([{
                label: `⚡ Shell: <code>${syntax}</code>`,
                action: () => {
                    const input = document.getElementById('palette-input');
                    if (input) input.value = syntax;
                    this.showPaletteFeedback('Generated Shell Syntax', syntax, 'command', 'command', syntax);
                    const dropdown = document.getElementById('palette-dropdown');
                    if (dropdown) dropdown.style.display = 'none';
                }
            }]);
        } catch (e) {
            console.error('AI synthesize error:', e);
        }
    },

    renderPaletteDropdown(items) {
        const dropdown = document.getElementById('palette-dropdown');
        if (!dropdown) return;
        if (!items || !items.length) {
            dropdown.style.display = 'none';
            return;
        }
        dropdown.innerHTML = '';
        items.forEach((item, idx) => {
            const el = document.createElement('div');
            el.className = 'dropdown-item' + (idx === 0 ? ' active' : '');
            el.innerHTML = `<span>${item.label}</span>` + (item.confidence ? `<span class="confidence-badge">${item.confidence}%</span>` : '');
            el.onclick = () => item.action();
            dropdown.appendChild(el);
        });
        dropdown.style.display = 'block';
    },

    selectPaletteMode(mode, tokenLabel) {
        this.paletteState.mode = mode;
        this.paletteState.tokens = [tokenLabel];
        this.renderPaletteBadges();
        const input = document.getElementById('palette-input');
        if (input) {
            input.value = '';
            if (mode === 'PASSWORD_KEY') input.placeholder = 'Enter secret key name (e.g. github_token)...';
            else if (mode === 'FILE_NAME') input.placeholder = 'Enter shortcut name (e.g. project_report) and press Enter to choose file...';
            else if (mode === 'COMMAND_PROMPT') input.placeholder = 'Describe command or enter shell syntax...';
            input.focus();
        }
        const dropdown = document.getElementById('palette-dropdown');
        if (dropdown) dropdown.style.display = 'none';
    },

    acceptIntentCandidate(candidate) {
        this.paletteState.tokens = [`${candidate.icon || '⚡'} ${candidate.title}`];
        this.renderPaletteBadges();
        const input = document.getElementById('palette-input');
        if (input) {
            input.value = candidate.command || '';
            input.focus();
        }
        this.showPaletteFeedback('Natural Language Intent', candidate.command, 'command', candidate.title, candidate.command);
        const dropdown = document.getElementById('palette-dropdown');
        if (dropdown) dropdown.style.display = 'none';
    },

    renderPaletteBadges() {
        const container = document.getElementById('palette-badges');
        if (!container) return;
        container.innerHTML = '';
        this.paletteState.tokens.forEach(tok => {
            const b = document.createElement('div');
            b.className = 'token-badge';
            b.innerHTML = `<span>${tok}</span><span class="badge-close" onclick="app.popPaletteBadge()">✕</span>`;
            container.appendChild(b);
        });
    },

    popPaletteBadge() {
        this.paletteState.tokens.pop();
        if (this.paletteState.tokens.length === 0) {
            this.paletteState.mode = 'IDLE';
            const input = document.getElementById('palette-input');
            if (input) {
                input.placeholder = 'Search or type a natural language command (or / for modes)...';
                input.value = '';
            }
        }
        this.renderPaletteBadges();
    },

    onPaletteKeydown(e) {
        const dropdown = document.getElementById('palette-dropdown');
        const isDropdownOpen = dropdown && dropdown.style.display !== 'none';

        if (e.key === 'Escape') {
            this.paletteState.tokens = [];
            this.paletteState.mode = 'IDLE';
            this.renderPaletteBadges();
            if (dropdown) dropdown.style.display = 'none';
            e.target.value = '';
            return;
        }

        if (e.key === 'Backspace' && e.target.value === '' && this.paletteState.tokens.length > 0) {
            this.popPaletteBadge();
            return;
        }

        if (e.key === 'Enter') {
            if (isDropdownOpen) {
                const activeItem = dropdown.querySelector('.dropdown-item.active') || dropdown.querySelector('.dropdown-item');
                if (activeItem) {
                    activeItem.click();
                    return;
                }
            }
            this.handlePaletteEnter();
        }
    },

    handlePaletteEnter() {
        const input = document.getElementById('palette-input');
        const text = input ? input.value.trim() : '';
        if (!text && this.paletteState.tokens.length === 0) return;

        const mode = this.paletteState.mode;

        if (mode === 'PASSWORD_KEY') {
            this.paletteState.collected.key = text;
            this.paletteState.tokens.push(`Key: ${text}`);
            this.paletteState.mode = 'PASSWORD_VAL';
            this.renderPaletteBadges();
            input.value = '';
            input.placeholder = 'Enter secret password/value to store...';
            return;
        }

        if (mode === 'PASSWORD_VAL') {
            const key = this.paletteState.collected.key;
            this.saveSqliteDirect('vault', key, text);
            this.showPaletteFeedback('Vault Password Stored', `Successfully encrypted and saved key: ${key}`, 'vault', key, text);
            this.resetPalette();
            return;
        }

        if (mode === 'FILE_NAME') {
            if (text.includes('=')) {
                const parts = text.split('=');
                const key = parts[0].trim();
                const val = parts[1].trim();
                if (!key || !val) return;
                this.saveSqliteDirect('file', key, val);
                this.showPaletteFeedback('File Shortcut Saved', `Shortcut ${key} -> ${val}`, 'file', key, val);
                this.resetPalette();
                return;
            }

            const key = text.trim();
            if (!key) return;

            this.showToast('📂 Opening file chooser for shortcut...');
            this.promptFileChooser(`Select file for shortcut: ${key}`).then(selectedPath => {
                if (!selectedPath) {
                    this.showToast('File selection cancelled. Please choose a file or type name=path.', true);
                    return;
                }
                this.saveSqliteDirect('file', key, selectedPath);
                this.showPaletteFeedback('File Shortcut Saved', `Shortcut ${key} -> ${selectedPath}`, 'file', key, selectedPath);
                this.resetPalette();
            });
            return;
        }

        if (mode === 'COMMAND_PROMPT' || this.paletteState.tokens.length > 0 || text) {
            const key = text.includes(' ') ? text.split(' ')[0] : text;
            this.saveSqliteDirect('command', key, text);
            this.showPaletteFeedback('Terminal Command Ready', `Command stored & ready: ${text}`, 'command', key, text);
            this.resetPalette();
            return;
        }
    },

    async promptFileChooser(title = 'Select Target File for Shortcut') {
        // 1. Primary: Native OS file chooser dialog via local server
        try {
            const res = await fetch(`${API_BASE}/choose-file`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title })
            });
            if (res.ok) {
                const data = await res.json();
                if (data.file_path) {
                    return data.file_path;
                }
                if (data.cancelled) {
                    return null;
                }
            }
        } catch (err) {
            console.warn('Native server file chooser failed, falling back to browser picker:', err);
        }

        // 2. Client-side browser file picker fallback
        return new Promise((resolve) => {
            let picker = document.getElementById('palette-file-picker');
            if (!picker) {
                picker = document.createElement('input');
                picker.type = 'file';
                picker.id = 'palette-file-picker';
                picker.style.display = 'none';
                document.body.appendChild(picker);
            }
            picker.value = '';

            const handleChange = () => {
                picker.removeEventListener('change', handleChange);
                if (picker.files && picker.files[0]) {
                    resolve(picker.files[0].name);
                } else {
                    resolve(null);
                }
            };

            picker.addEventListener('change', handleChange, { once: true });

            const handleFocus = () => {
                window.removeEventListener('focus', handleFocus);
                setTimeout(() => {
                    if (!picker.files || picker.files.length === 0) {
                        resolve(null);
                    }
                }, 1000);
            };
            window.addEventListener('focus', handleFocus, { once: true });

            picker.click();
        });
    },

    async browseFileForModal() {
        this.showToast('📂 Opening file chooser...');
        const path = await this.promptFileChooser('Select Target File for Shortcut');
        if (path) {
            const valInput = document.getElementById('modal-record-val');
            if (valInput) valInput.value = path;
            this.showToast(`Selected: ${path}`);
        } else {
            this.showToast('File selection cancelled', true);
        }
    },

    resetPalette() {
        this.paletteState.tokens = [];
        this.paletteState.mode = 'IDLE';
        this.paletteState.collected = {};
        this.renderPaletteBadges();
        const input = document.getElementById('palette-input');
        if (input) {
            input.value = '';
            input.placeholder = 'Search or type a natural language command (or / for modes)...';
        }
        const dropdown = document.getElementById('palette-dropdown');
        if (dropdown) dropdown.style.display = 'none';
    },

    showPaletteFeedback(title, body, category, key, value) {
        const panel = document.getElementById('palette-feedback');
        if (!panel) return;
        document.getElementById('feedback-title').textContent = title;
        document.getElementById('feedback-body').textContent = body;
        this.paletteState.currentResult = { category, key, value };
        panel.style.display = 'block';
    },

    dismissPaletteFeedback() {
        const panel = document.getElementById('palette-feedback');
        if (panel) panel.style.display = 'none';
    },

    async executeOrSaveResult() {
        if (!this.paletteState.currentResult) return;
        const { category, key, value } = this.paletteState.currentResult;
        await this.saveSqliteDirect(category, key, value);
        this.dismissPaletteFeedback();
    },

    async saveSqliteDirect(category, key, value) {
        try {
            const res = await fetch(`${API_BASE}/records`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ category, key, value })
            });
            if (res.ok) {
                this.showToast(`Saved to SQLite (${category}): ${key}`);
                this.loadSqliteRecords();
            } else {
                this.showToast('Failed to save to SQLite', true);
            }
        } catch (e) {
            this.showToast('Network error saving record', true);
        }
    },

    // --- SQLite Records Viewer ---
    async loadSqliteRecords() {
        try {
            const res = await fetch(`${API_BASE}/records`);
            if (!res.ok) return;
            const data = await res.json();

            const vaultList = data.vault_passwords || [];
            const fileList = data.file_shortcuts || [];
            const cmdList = data.terminal_commands || [];

            const cVault = document.getElementById('count-vault');
            const cFile = document.getElementById('count-file');
            const cCmd = document.getElementById('count-cmd');
            if (cVault) cVault.textContent = vaultList.length;
            if (cFile) cFile.textContent = fileList.length;
            if (cCmd) cCmd.textContent = cmdList.length;

            this.renderRecordsTable('records-vault-list', vaultList, 'key_name', 'encrypted_value', 'vault');
            this.renderRecordsTable('records-file-list', fileList, 'shortcut_name', 'file_path', 'file');
            this.renderRecordsTable('records-cmd-list', cmdList, 'command_name', 'command_string', 'command');
        } catch (e) {
            console.error('Failed to load SQLite records:', e);
        }
    },

    renderRecordsTable(containerId, items, keyField, valField, category) {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (!items.length) {
            const catLabels = { vault: 'Vault Password', file: 'File Shortcut', command: 'Terminal Command' };
            const catLabel = catLabels[category] || category;
            container.innerHTML = `
                <div style="padding: 36px 20px; text-align: center; color: var(--text-secondary); background: rgba(15, 23, 42, 0.4); border: 1px dashed var(--border); border-radius: 10px; margin-top: 8px;">
                    <div style="font-size: 2rem; margin-bottom: 8px;">📂</div>
                    <div style="font-size: 1rem; color: #e2e8f0; font-weight: 500;">No ${catLabel} records found in SQLite</div>
                    <p style="font-size: 0.85rem; margin-top: 4px; color: var(--text-secondary);">Use the <strong>AI Command Palette</strong> or click <strong>+ Add Record</strong> to store entries.</p>
                </div>`;
            return;
        }

        let html = '<table class="records-table"><thead><tr>';
        html += `<th>Key / Name</th><th>Value / Command</th><th>Updated</th><th>Action</th></tr></thead><tbody>`;

        items.forEach(item => {
            const keyVal = item[keyField];
            const rawVal = item[valField];
            const updated = item.updated_at ? item.updated_at.split('T')[0] : 'Just now';

            html += `<tr>
                <td style="font-weight: 600; color: #93c5fd;">${this.escapeHtml(keyVal)}</td>
                <td style="font-family: monospace; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${this.escapeHtml(rawVal)}</td>
                <td style="color: var(--text-secondary); font-size: 0.8rem;">${updated}</td>
                <td>
                    <button class="btn-delete" onclick="app.deleteSqliteRecord('${category}', '${this.escapeHtml(keyVal)}')">Delete</button>
                </td>
            </tr>`;
        });

        html += '</tbody></table>';
        container.innerHTML = html;
    },

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    },

    async deleteSqliteRecord(category, key) {
        if (!confirm(`Are you sure you want to delete '${key}' from SQLite?`)) return;
        try {
            const res = await fetch(`${API_BASE}/records`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ category, key })
            });
            if (res.ok) {
                this.showToast(`Deleted '${key}' from SQLite`);
                this.loadSqliteRecords();
            } else {
                this.showToast('Failed to delete record', true);
            }
        } catch (e) {
            this.showToast('Network error deleting record', true);
        }
    },

    switchSubTab(e, tabId) {
        document.querySelectorAll('.subnav-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.subtab-content').forEach(s => s.classList.remove('active'));
        e.currentTarget.classList.add('active');
        const tabEl = document.getElementById(tabId);
        if (tabEl) tabEl.classList.add('active');
    },

    showAddRecordModal() {
        const modal = document.getElementById('record-modal');
        if (modal) modal.style.display = 'flex';
    },

    closeRecordModal() {
        const modal = document.getElementById('record-modal');
        if (modal) modal.style.display = 'none';
    },

    async submitNewRecord() {
        const cat = document.getElementById('modal-record-category').value;
        const key = document.getElementById('modal-record-key').value.trim();
        const val = document.getElementById('modal-record-val').value.trim();

        if (!key || !val) {
            this.showToast('Key and Value are required', true);
            return;
        }

        await this.saveSqliteDirect(cat, key, val);
        this.closeRecordModal();
        document.getElementById('modal-record-key').value = '';
        document.getElementById('modal-record-val').value = '';
    }
};

document.addEventListener('DOMContentLoaded', () => {
    app.init();
    app.initResizers();
});