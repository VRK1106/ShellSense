import pandas as pd
import random

df = pd.read_csv('Cleaned_text_intent.csv')
templates = [
    "{}", "can you {}", "please {}", "i need to {}", "i want to {}", 
    "launch {}", "start {}", "execute {}", "run {}", "open {}", 
    "check {}", "display {}", "monitor {}", "show me {}", "give me {}"
]
extra_data = {
    "CHECK_IP": ["ip address", "ip config", "local ip", "network ip", "my ip info"],
    "SYSTEM_DETAILS": ["pc specs", "system information", "hardware info", "windows version", "bios details"],
    "PING_GOOGLE": ["internet connection", "connectivity", "ping google", "network test", "is internet working", "internet strength"],
    "TRACE_ROUTE": ["trace route", "network path", "tracert", "track route", "path to server"],
    "DNS_LOOKUP": ["dns info", "nslookup", "resolve domain", "domain ip", "check dns"],
    "POWER_OFF": ["shutdown now", "power off computer", "turn off pc", "switch off"],
    "RESTART": ["reboot now", "restart machine", "restart pc", "reboot system"],
    "OPEN_NETWORK_SETTINGS": ["wifi issues", "wifi settings", "open network", "network problems", "internet is down"],
    "OPEN_CALCULATOR": ["calculations", "do math", "calculate", "some numbers"],
    "OPEN_CMD": ["run some commands", "open terminal", "execute commands", "command shell"],
    "OPEN_TASK_MANAGER": ["kill some tasks", "end tasks", "kill processes", "close unresponsive apps"],
    "QUIT_PROGRAM": ["stop program", "exit program", "quit operations", "shut down interface", "close shellsense"]
}
augmented_rows = []
for intent, keywords in extra_data.items():
    for kw in keywords:
        for temp in templates:
            augmented_rows.append({"text": temp.format(kw).lower(), "intent": intent})
new_data = pd.DataFrame(augmented_rows)
final_df = pd.concat([df, new_data]).drop_duplicates(subset=['text'])
final_df.to_csv('Cleaned_text_intent.csv', index=False)
print(f"Dataset boosted from {len(df)} to {len(final_df)} rows.")