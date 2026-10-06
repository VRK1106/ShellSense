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

        if (container.id === 'snippets-editor' && String(valInput.value).startsWith('ENC:')) {
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

        // Add Vault toggle button for snippets
        if (container.id === 'snippets-editor') {
            const vaultBtn = document.createElement('button');
            const isEnc = String(valInput.value).startsWith('ENC:');
            vaultBtn.className = isEnc ? 'btn-vault locked' : 'btn-vault';
            vaultBtn.textContent = isEnc ? '🔒 Locked' : '🔓 Protect';
            vaultBtn.title = isEnc ? 'Click to decrypt and view/edit' : 'Click to encrypt with Master Password';

            vaultBtn.onclick = async () => {
                const currentVal = valInput.value.trim();
                if (currentVal.startsWith('ENC:')) {
                    const pass = prompt('Enter Master Password to decrypt (client-side):');
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
                    const pass = prompt('Enter Master Password to encrypt this snippet (client-side):');
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
    }
};

document.addEventListener('DOMContentLoaded', () => {
    app.init();
    app.initResizers();
});