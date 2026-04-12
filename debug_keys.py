import keyboard
print("Press Ctrl+Shift+Space to see if it works")
keyboard.add_hotkey('ctrl+shift+space', lambda: print("Works"))
keyboard.wait('esc')