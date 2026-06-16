# 🚀 ShellSense — The Keyboard-First Utility Command Palette

<p align="center">
  <img src="https://img.shields.io/badge/ShellSense-v1.2.0-blueviolet?style=for-the-badge&logo=quicktime" alt="ShellSense Version">
  <img src="https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows" alt="Platform: Windows">
  <img src="https://img.shields.io/badge/UI-PyQt6-41CD52?style=for-the-badge&logo=qt" alt="UI: PyQt6">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT">
</p>

---

**ShellSense** is a premium, keyboard-first command palette built for power users. Similar to Spotlight (macOS) or Raycast, it brings natural language commands, unit conversions, timezone translation, quick file snippets, and background timers right to your fingertips via a **sleek, frosted-glass interface**.

<p align="center">
  <img src="widget_render.png" alt="ShellSense Command Bar Interface" width="600" style="border-radius:12px; border: 1px solid rgba(255,255,255,0.25);">
</p>

---

## ✨ Features & Capabilities

### 🧮 1. Instant Calculations & Unit Conversions
* **The Problem:** Opening calculator apps or googling "10 miles to km" breaks your focus.
* **The Solution:** Evaluate expression instantly from the bar.
  * *Try:* `15% of 80`, `sqrt(144)`, or `10 miles to km`

### 🌐 2. Timezone Translation
* **The Problem:** Converting schedule invites between zones is tedious.
* **The Solution:** Quick zone matching.
  * *Try:* `10:30 am est to ist`

### 💱 3. Currency Exchange
* **The Problem:** Loading currency conversion websites is slow and ad-heavy.
* **The Solution:** Fast, local exchange rate conversions.
  * *Try:* `100 usd to eur`

### 📂 4. File Finder & Downloads Hook
* **The Problem:** Digging through your downloads folder to open or copy your latest file.
* **The Solution:** Access your most recent downloads instantly.
  * *Try:* `open last download` or `copy last download`

### ⏱️ 5. Distraction-Free Alarms & Timers
* **The Problem:** Setting a timer on your phone distracts you.
* **The Solution:** Background timers triggering native Windows alerts.
  * *Try:* `timer 5 mins to check oven` or `stop timer`

### ⚙️ 6. System Cleanup & Tune-up
* **The Problem:** SSD bloat and slow startup.
* **The Solution:** Audit startup apps and clear cache paths.
  * *Try:* `show startup apps` or `clean temp files`

---

## ⚡ Getting Started & Setup

Follow these steps to clone, configure, and use ShellSense:

### 1. Clone the Repository
Open your terminal (PowerShell, Command Prompt, or Git Bash) and run:
```bash
git clone https://github.com/VRK1106/ShellSense.git
cd ShellSense
```

### 2. Install Dependencies
Install the required packages using pip:
```bash
pip install -r requirements.txt
```

### 3. Launch the Application
Start the background engine:
* **Option A:** Double-click the `run.bat` file in the project folder.
* **Option B:** Run it via terminal:
  ```bash
  pythonw -m shellsense.ui.interface
  ```
*Once launched, the app runs silently in the background. You'll see a search icon appear in your **System Tray** (bottom-right).*

---

## ⌨️ How to Use & Give Inputs

1. **Summon the Bar:** Press **`Ctrl + Shift + Space`** to bring up the frosted-glass search bar.
2. **Type Your Command:**
   - **Math:** Type `25 * 40` or `15% of 240` and press **Enter**.
   - **Currency:** Type `100 usd to eur` and press **Enter**.
   - **Timezone:** Type `10:00 am est to ist` and press **Enter**.
   - **Recent Downloads:** Type `open last download` or `copy last download` and press **Enter**.
   - **Interactive Panels:** Type category names like `length`, `pressure`, `weight`, or `timer` and press **Enter** to open dedicated inputs.
     - *For Conversions (e.g. Length):* Type `50` in the value box and press **Enter** to get the output.
3. **Handle Results:**
   - Press **Enter** again (on the empty search bar) to **Copy the Result** to your clipboard and close the bar.
   - Press **Escape** at any time to **Close the Bar** without copying.

---

## ⚙️ Customizing Shortcuts & Snippets

You can create your own custom file hooks and text snippets by editing or creating JSON files in the project root.

### 1. File Shortcuts (`file_shortcuts.json`)
Create a file named `file_shortcuts.json` in the root of the project. It maps shorthand keys to full local file/folder paths.

**Example `file_shortcuts.json`:**
```json
{
    "resume": "C:\\Users\\Username\\Documents\\Resume.pdf",
    "photo": "C:\\Users\\Username\\Pictures\\Photo_ID.jpeg",
    "project": "D:\\Projects\\Codebase"
}
```

* **Usage in ShellSense:**
  - **Open file/folder:** Type `open resume` or `open project` and press Enter.
  - **Copy file path:** Type `copy path resume` and press Enter.
  - **Copy actual file (to clipboard):** Type `copy file photo` and press Enter. (You can then Ctrl+V directly to paste the image file into an email or File Explorer).

### 2. Text Snippets (`snippets.json`)
Create a file named `snippets.json` in the root of the project. It maps shorthand keys to text strings (e.g. emails, phone numbers, addresses, template text).

**Example `snippets.json`:**
```json
{
    "email": "username@gmail.com",
    "phone": "+919876543210",
    "address": "123 Main Street, City, Country"
}
```

* **Usage in ShellSense:**
  - **Copy text snippet:** Type `copy email` or `copy address` and press Enter. The value will be copied to your clipboard instantly.

---

## 📌 Start Menu & Taskbar Shortcuts (Windows)

To launch ShellSense instantly or keep it accessible, follow these simple setup steps:

### 1. Create the Desktop Shortcut
Run the included PowerShell script to create a optimized shortcut pointing to `pythonw.exe`:
```powershell
powershell -ExecutionPolicy Bypass -File .\create_shortcut.ps1
```
*This will create a `ShellSense` shortcut icon directly on your Desktop.*

### 2. Pin to Taskbar
1. Locate the **ShellSense** shortcut on your Desktop.
2. Right-click the shortcut and select **Pin to Taskbar** (or drag and drop it onto your Windows Taskbar).

### 3. Add to Start Menu Search & Programs
1. Press `Win + R` to open the Run dialog.
2. Type `shell:programs` and hit Enter. This opens the **Start Menu Programs** directory.
3. Move or Copy the `ShellSense` desktop shortcut into this folder.
4. *ShellSense is now indexable by Windows Search—just press the Windows key, type "ShellSense", and press Enter.*

### 4. Run Automatically at Startup
1. Press `Win + R` to open the Run dialog.
2. Type `shell:startup` and hit Enter. This opens the **Startup** folder.
3. Paste a copy of the `ShellSense` desktop shortcut into this folder.
4. *ShellSense will now start silently in the background whenever you boot Windows.*

---

## 📜 Version History & Progression

### 🛡️ Version 1 (v1) — Foundation
* **Core Functions:**
  * Basic command line generation and routing.
  * Launching programs and executing shell scripts silently.
  * Simple, flat keypress handlers for summoning the interface.
* **Brain Service:** Initial model `shellsense_v1.pkl` focused on basic command classification and matching.

### ⚡ Version 2 (v2) — Functional Utility Expansion
* **Core Upgrades:**
  * **Timezone Translator:** Integrated offline timezone offset translator (e.g., `est to ist`).
  * **Real-time Currency Exchange:** Integrated fast currency conversions (e.g., `usd to eur`).
  * **Downloads Finder:** Accessing or copying the latest file from the Downloads folder.
  * **File Shortcuts:** Opening custom files/folders or copying custom text snippets via shorthand bindings configured in `file_shortcuts.json`.
  * **Background Timers:** Setting native background timers that trigger native Windows OS alert dialogs.
  * **System Tuner:** Auditing and disabling startup applications and clearing temp files.
* **Brain Service:** Upgraded to `shellsense_v2.pkl` for increased classification confidence and broader parser intent classification.

### 🌟 Version 3 (v3) — Interactive UI & UX Polish (Current)
* **Core Upgrades:**
  * **Frosted-Glass Redesign:** Added dynamic sizing, glassmorphism transparency, and a clean minimalist styling.
  * **Interactive Unit Conversions:** Added comprehensive unit converters (length, speed, mass/weight, volume, temperature, pressure, area, power) with smart parsing logic.
  * **Dynamic Selection Panels:** Category inputs (like `length`, `mass/weight`, `timer`, etc.) now present visual inputs inside the palette instead of requiring pure command entry.
  * **Result Action Widget:** Persistent `Copy & Close` and `Close` buttons allow mouse-driven action on command output.
  * **Double-Enter & Escape Keyboard Flow:** Pressing Enter in the value field submits the conversion, focusing back to the search bar. Pressing Enter a second time copies the result and closes. Pressing Escape closes immediately without copying.
  * **Snooze Option:** Custom snooze timer settings directly in the alarm popup alert.
* **Brain Service:** High-confidence `shellsense_v3.pkl` model supporting categorization matching for interactive panels.