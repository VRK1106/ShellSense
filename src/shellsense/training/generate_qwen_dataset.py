import pandas as pd
import json
import urllib.request
import os
import random
import time
import itertools

# Configurations
TARGET_COUNT = 450
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CSV_PATH = os.path.join(BASE_DIR, 'Cleaned_text_intent.csv')

# Descriptions for Qwen fallback
INTENT_DESCS = {
    "PING_GOOGLE": "Check network connectivity by pinging Google or external servers.",
    "OPEN_NETWORK_SETTINGS": "Open the Windows network and sharing center or wifi configuration settings.",
    "POWER_OFF": "Turn off the computer immediately.",
    "CHECK_IP": "Display the current local or public IP address of the machine.",
    "OPEN_CALCULATOR": "Launch the calculator utility.",
    "OPEN_TASK_MANAGER": "Open the Windows Task Manager to monitor active applications.",
    "SYSTEM_DETAILS": "Display computer specifications, OS version, or hardware info.",
    "OPEN_CMD": "Open a Command Prompt or Terminal window.",
    "TRACE_ROUTE": "Run a tracert/traceroute to track network packets to a destination.",
    "DNS_LOOKUP": "Perform a DNS lookup query (nslookup) to resolve a domain to an IP.",
    "RESTART": "Reboot the computer immediately.",
    "QUIT_PROGRAM": "Quit or exit the ShellSense command generator program.",
    "POWER_OFF_TIMER": "Schedule a computer shutdown with a timer/delay (needs time duration in text).",
    "LOCK_SCREEN": "Lock the Windows desktop screen immediately.",
    "PROCESS_KILL": "Force close or kill a running application or PID.",
    "STORAGE_INFO": "Check hard drive disk space, free space, or capacity.",
    "CHECK_RESOURCES": "Check CPU usage, memory/RAM details, system load, or temperature."
}

# Combinatorial generation rules
GENERATION_RULES = {
    "CHECK_IP": {
        "verbs": ["check", "get", "show", "display", "view", "reveal", "print", "what is", "whats", "find"],
        "nouns": ["ip", "ip address", "ipv4 address", "network ip", "local ip", "internal ip", "current ip", "ip config"],
        "suffixes": ["", "now", "please", "for me", "of this pc", "of my machine", "on this system"]
    },
    "DNS_LOOKUP": {
        "verbs": ["run", "do", "perform", "execute", "start", "query", "check", "lookup"],
        "nouns": ["dns info", "dns records", "nslookup", "dns resolution", "name resolution", "domain ip"],
        "suffixes": ["for google.com", "for github.com", "on google", "on github", "for a website", "on 8.8.8.8", "for a host"]
    },
    "LOCK_SCREEN": {
        "verbs": ["lock", "secure", "close access to", "protect", "log off", "sign out"],
        "nouns": ["screen", "pc", "computer", "machine", "windows screen", "session", "workstation"],
        "suffixes": ["", "now", "immediately", "please", "for safety", "right away"]
    },
    "OPEN_CALCULATOR": {
        "verbs": ["open", "start", "launch", "run", "execute", "bring up", "show", "display"],
        "nouns": ["calculator", "calc", "math app", "calculator utility", "calculations tool"],
        "suffixes": ["", "please", "quickly", "now", "for some math", "to calculate numbers"]
    },
    "OPEN_CMD": {
        "verbs": ["open", "start", "launch", "run", "execute", "bring up"],
        "nouns": ["cmd", "terminal", "command prompt", "command line", "command shell", "cli console", "shell prompt"],
        "suffixes": ["", "please", "now", "instantly", "quickly"]
    },
    "OPEN_NETWORK_SETTINGS": {
        "verbs": ["open", "show", "view", "go to", "configure", "modify", "access", "manage"],
        "nouns": ["network settings", "wifi settings", "internet settings", "adapter properties", "network connections", "wifi panel", "sharing center"],
        "suffixes": ["", "please", "now", "to fix wifi", "to check connections"]
    },
    "OPEN_TASK_MANAGER": {
        "verbs": ["open", "start", "launch", "show", "bring up", "access", "view"],
        "nouns": ["task manager", "process manager", "taskmgr", "system monitor", "active applications list"],
        "suffixes": ["", "please", "now", "to end tasks", "to kill process"]
    },
    "PING_GOOGLE": {
        "verbs": ["ping", "test connectivity to", "check latency to", "send packets to", "test network on"],
        "nouns": ["google", "google.com", "8.8.8.8", "google servers", "external host"],
        "suffixes": ["", "please", "to check internet", "now", "for latency check"]
    },
    "POWER_OFF": {
        "verbs": ["shutdown", "power off", "turn off", "switch off", "kill power to", "halt"],
        "nouns": ["pc", "computer", "machine", "system", "windows desktop", "workstation"],
        "suffixes": ["now", "immediately", "right away", "instantly", "please", "safe shutdown"]
    },
    "POWER_OFF_TIMER": {
        "verbs": ["set a shutdown timer", "schedule shutdown", "turn off pc in", "shutdown timer for", "set power off in"],
        "nouns": ["10 minutes", "30 mins", "an hour", "5 minutes", "after 1 hour", "20 minutes", "15 mins", "45 minutes"],
        "suffixes": ["", "please", "immediately", "from now"]
    },
    "RESTART": {
        "verbs": ["restart", "reboot", "power cycle", "reset"],
        "nouns": ["pc", "computer", "machine", "system", "workstation"],
        "suffixes": ["now", "immediately", "please", "right away", "instantly"]
    },
    "SYSTEM_DETAILS": {
        "verbs": ["show", "display", "get", "view", "reveal", "print"],
        "nouns": ["specs", "system info", "hardware details", "pc specifications", "os details", "cpu and ram info", "system details"],
        "suffixes": ["", "please", "for me", "of this machine", "now"]
    },
    "TRACE_ROUTE": {
        "verbs": ["tracert", "traceroute", "trace route", "track path", "map connection route"],
        "nouns": ["to google.com", "to github.com", "to a domain", "to 8.8.8.8", "to host", "to server"],
        "suffixes": ["", "please", "now", "to debug route"]
    },
    "QUIT_PROGRAM": {
        "verbs": ["stop", "exit", "quit", "close", "shut down", "kill"],
        "nouns": ["program", "operations", "interface", "shellsense", "gui panel", "the application"],
        "suffixes": ["", "please", "now", "instantly", "immediately"]
    },
    "PROCESS_KILL": {
        "verbs": ["kill", "terminate", "stop", "force close", "end", "close", "force quit", "shutdown"],
        "nouns": ["process", "program", "app", "task", "pid", "application", "lagging app"],
        "suffixes": ["1234", "chrome", "explorer.exe", "immediately", "now", "please", "taskmgr"]
    },
    "STORAGE_INFO": {
        "verbs": ["check", "show", "display", "get", "view", "is my", "how much"],
        "nouns": ["disk space", "storage info", "c drive", "hard drive capacity", "free space", "disk health"],
        "suffixes": ["", "left", "full", "now", "please", "on my computer"]
    },
    "CHECK_RESOURCES": {
        "verbs": ["check", "show", "display", "get", "monitor", "whats my", "is my"],
        "nouns": ["cpu usage", "ram usage", "memory check", "system resources", "hardware load", "cpu temperature"],
        "suffixes": ["", "now", "please", "active", "high", "load"]
    }
}

def generate_combinatorial(intent):
    if intent not in GENERATION_RULES:
        return []
    rule = GENERATION_RULES[intent]
    prefixes = ["", "can you", "please", "i need to", "i want to", "could you", "go ahead and"]
    sentences = set()
    combinations = list(itertools.product(prefixes, rule["verbs"], rule["nouns"], rule["suffixes"]))
    for pref, verb, noun, suff in combinations:
        parts = [pref, verb, noun, suff]
        clean_str = " ".join([p.strip() for p in parts if p.strip()]).lower()
        sentences.add(clean_str)
    
    # Shuffle and return a list
    result = list(sentences)
    random.shuffle(result)
    return result

def query_qwen_raw(prompt):
    url = "http://localhost:11434/api/generate"
    data = {
        "model": "qwen2.5:1.5b",
        "prompt": prompt,
        "stream": False
    }
    
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=90) as response:
                res = json.loads(response.read().decode("utf-8"))
                return res["response"]
        except Exception as e:
            print(f"  Ollama request attempt {attempt + 1} failed: {e}")
            time.sleep(1)
    return None

def generate_phrases_qwen(intent, existing_list, target_needed):
    print(f"  Requesting {target_needed} phrases from Qwen...")
    new_phrases = set()
    
    desc = INTENT_DESCS.get(intent, intent)
    
    while len(new_phrases) < target_needed:
        batch_size = min(80, target_needed - len(new_phrases))
        prompt = f"""You are a training dataset generator for the command launcher ShellSense.
Generate exactly {batch_size} unique, diverse, natural-sounding phrases in English that a user would type to execute this intent:
Intent: {intent}
Description: {desc}

Rules:
1. Return the output as a simple list with ONE phrase per line.
2. Do NOT use markdown, numbering (like 1., 2.), bullet points, or quotes.
3. Keep the queries natural and conversational.
4. For POWER_OFF_TIMER, make sure the queries contain a duration or time offset.
5. For PROCESS_KILL, make sure the queries mention PIDs or process names to terminate.
6. Make them different from typical structured templates.

Output the lines now:"""

        response_text = query_qwen_raw(prompt)
        if not response_text:
            continue
            
        lines = response_text.strip().split("\n")
        valid_count = 0
        for line in lines:
            line_clean = line.strip().lower()
            # Remove leading/trailing bullet symbols, digits, quotes
            for char in ['-', '*', '"', "'"]:
                if line_clean.startswith(char):
                    line_clean = line_clean[1:].strip()
                if line_clean.endswith(char):
                    line_clean = line_clean[:-1].strip()
            
            # Filter digit numbering e.g. "1. "
            if "." in line_clean[:3]:
                parts = line_clean.split(".", 1)
                if parts[0].strip().isdigit():
                    line_clean = parts[1].strip()
            
            if line_clean and line_clean not in existing_list and line_clean not in new_phrases:
                new_phrases.add(line_clean)
                valid_count += 1
                
        print(f"    Added {valid_count} unique Qwen phrases. (Progress: {len(new_phrases)}/{target_needed})")
        if valid_count == 0:
            # Prevent infinite loops in case of poor LLM outputs
            time.sleep(0.5)
            
    return list(new_phrases)[:target_needed]

def main():
    if os.path.exists(CSV_PATH):
        df = pd.read_csv(CSV_PATH)
        print(f"Loaded existing dataset with {len(df)} rows.")
    else:
        df = pd.DataFrame(columns=["text", "intent"])
        print("Created new dataset.")

    df = df.dropna(subset=["text", "intent"])
    df["text"] = df["text"].astype(str).str.lower().str.strip()

    balanced_dfs = []
    
    # We mix 300 combinatorial/existing phrases and 150 Qwen phrases for maximum diversity
    QWEN_TARGET = 150
    COMB_TARGET = TARGET_COUNT - QWEN_TARGET # 300
    
    for intent in INTENT_DESCS.keys():
        # Clean existing raw entries for this intent
        intent_df = df[df["intent"] == intent].drop_duplicates(subset=["text"])
        
        # 1. Generate combinatorial pool
        comb_phrases = generate_combinatorial(intent)
        
        # Merge existing with combinatorial
        existing_pool = set(intent_df["text"].tolist())
        for p in comb_phrases:
            existing_pool.add(p)
            
        # Sample the target combinatorial count
        sampled_comb = random.sample(list(existing_pool), min(len(existing_pool), COMB_TARGET))
        
        print(f"\n--- Intent: {intent} ---")
        print(f"  Collected {len(sampled_comb)} combinatorial phrases.")
        
        # 2. Generate Qwen phrases
        # Make sure they don't collide with the combinatorial samples
        qwen_phrases = generate_phrases_qwen(intent, set(sampled_comb), QWEN_TARGET)
        
        # 3. Combine them
        final_phrases = sampled_comb + qwen_phrases
        
        # If we didn't get enough Qwen phrases for some reason, pad with more combinatorial
        if len(final_phrases) < TARGET_COUNT:
            padding_needed = TARGET_COUNT - len(final_phrases)
            remaining_comb = [p for p in existing_pool if p not in final_phrases]
            padding_phrases = random.sample(remaining_comb, min(len(remaining_comb), padding_needed))
            final_phrases += padding_phrases
            
        final_intent_df = pd.DataFrame([{"text": p, "intent": intent} for p in final_phrases[:TARGET_COUNT]])
        print(f"  Final count for {intent}: {len(final_intent_df)} phrases.")
        balanced_dfs.append(final_intent_df)

    final_df = pd.concat(balanced_dfs).sample(frac=1, random_state=42).reset_index(drop=True)
    final_df.to_csv(CSV_PATH, index=False)
    
    print("\n==============================================")
    print(f"SUCCESS: Balanced dataset saved to {CSV_PATH}")
    print(f"Total Rows: {len(final_df)}")
    print("Class Distribution:")
    print(final_df["intent"].value_counts())
    print("==============================================")

if __name__ == "__main__":
    main()
