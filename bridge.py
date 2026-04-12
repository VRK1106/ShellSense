import joblib
import subprocess
import os

vectorizer, le, clf = joblib.load('shellsense_v1.pkl')
SAFE_COMMANDS = {
    "POWER_OFF": ["shutdown", "/s", "/t", "0"],
    "POWER_OFF_TIMER": ["shutdown", "/s", "/t", "{s}"],
    "RESTART": ["shutdown", "/r", "/t", "0"],
    "LOCK_SCREEN": ["rundll32.exe", "user32.dll,LockWorkStation"],
    "OPEN_NET": ["control", "ncpa.cpl"],
    "OPEN_TASK_MANAGER": ["taskmgr"],
    "OPEN_CMD": ["start",  "cmd"],
    "OPEN_CALCULATOR": ["calc"]
}

def execute_intent(intent, user_text):
    if intent in SAFE_COMMANDS:
        print(f"Action authorized, Executing {intent}")
        command = SAFE_COMMANDS[intent]
        if intent == "POWER_OFF_TIMER":
            import re
            seconds = re.findall(r'\d+', user_text)
            if seconds:
                wait_time = int(seconds[0])*60
                subprocess.run(["shutdown", "/s", "/t", str(wait_time)])
            else:
                print("I heard a timer request, but no minutes. Aborting for safety")
        else:
            subprocess.run(command, shell = True)
    else:
        print(f"Security block. '{intent}' is not in the safe list")
    
while True:
    user_input = input(("\nHow can i help you? "))
    if user_input.lower() == 'quit':
        break
    text_vec = vectorizer.transform([user_input.lower()])
    intent = le.inverse_transform(clf.predict(text_vec))[0]
    execute_intent(intent, user_input)