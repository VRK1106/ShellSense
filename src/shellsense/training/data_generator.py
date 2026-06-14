import pandas as pd
import random
import itertools

# --- CONFIGURATION ---
TARGET_COUNT = 450  # Set the uniform target count for ALL intents
INPUT_CSV = 'Cleaned_text_intent.csv'
OUTPUT_CSV = 'Cleaned_text_intent.csv'

# Combinatorial generation rules mapped to all of your unique intents
# (Provides clean, high-variety natural language combinations)
generation_rules = {
    "CHECK_IP": {
        "nouns": ["ip", "ip address", "ipv4 address", "network ip", "local ip", "internal ip", "current ip", "ip config"],
        "suffixes": ["", "now", "please", "for me", "of this pc", "of my machine", "on this system"],
        "verbs": ["check", "get", "show", "display", "view", "reveal", "print", "what is", "whats", "find"]
    },
    "DNS_LOOKUP": {
        "nouns": ["dns info", "dns records", "nslookup", "dns resolution", "name resolution", "domain ip"],
        "suffixes": ["for google.com", "for github.com", "on google", "on github", "for a website", "on 8.8.8.8", "for a host"],
        "verbs": ["run", "do", "perform", "execute", "start", "query", "check", "lookup"]
    },
    "LAUNCH_APP": {
        "nouns": ["chrome", "spotify", "notepad", "word", "excel", "powerpoint", "discord", "vscode", "paint", "steam", "photoshop", "firefox", "slack", "vs code", "visual studio code", "zoom", "teams", "outlook"],
        "suffixes": ["", "please", "now", "app", "application"],
        "verbs": ["open", "start", "launch", "run", "execute", "bring up"]
    },
    "LOCK_SCREEN": {
        "nouns": ["screen", "pc", "computer", "machine", "windows screen", "session", "workstation"],
        "suffixes": ["", "now", "immediately", "please", "for safety", "right away"],
        "verbs": ["lock", "secure", "close access to", "protect", "log off", "sign out"]
    },
    "OPEN_CALCULATOR": {
        "nouns": ["calculator", "calc", "math app", "calculator utility", "calculations tool", "calcuator", "claculator", "calclator"],
        "suffixes": ["", "please", "quickly", "now", "for some math", "to calculate numbers"],
        "verbs": ["open", "start", "launch", "run", "execute", "bring up", "show", "display"]
    },
    "OPEN_CMD": {
        "nouns": ["cmd", "terminal", "command prompt", "command line", "command shell", "cli console", "shell prompt", "teminal", "termnial", "commnad prompt"],
        "suffixes": ["", "please", "now", "instantly", "quickly"],
        "verbs": ["open", "start", "launch", "run", "execute", "bring up"]
    },
    "OPEN_NET": {
        "nouns": ["default browser", "web browser", "the internet", "the net", "chrome browser", "edge browser", "web portal"],
        "suffixes": ["", "please", "now", "to surf", "to go online"],
        "verbs": ["open", "start", "launch", "run", "go to", "access"]
    },
    "OPEN_NETWORK_SETTINGS": {
        "nouns": ["network settings", "wifi settings", "internet settings", "adapter properties", "network connections", "wifi panel", "sharing center", "slow internet", "slow connection", "slow wifi", "slow network", "connection speed"],
        "suffixes": ["", "please", "now", "to fix wifi", "to check connections"],
        "verbs": ["open", "show", "view", "go to", "configure", "modify", "access", "manage", "fix my", "troubleshoot my"]
    },
    "OPEN_TASK_MANAGER": {
        "nouns": ["task manager", "process manager", "taskmgr", "system monitor", "active applications list"],
        "suffixes": ["", "please", "now", "to end tasks", "to kill process"],
        "verbs": ["open", "start", "launch", "show", "bring up", "access", "view"]
    },
    "PING_GOOGLE": {
        "nouns": ["google", "google.com", "8.8.8.8", "google servers", "external host"],
        "suffixes": ["", "please", "to check internet", "now", "for latency check"],
        "verbs": ["ping", "test connectivity to", "check latency to", "send packets to", "test network on"]
    },
    "POWER_OFF": {
        "nouns": ["pc", "computer", "machine", "system", "windows desktop", "workstation"],
        "suffixes": ["now", "immediately", "right away", "instantly", "please", "safe shutdown"],
        "verbs": ["shutdown", "power off", "turn off", "switch off", "kill power to", "halt"]
    },
    "POWER_OFF_TIMER": {
        "nouns": ["10 minutes", "30 mins", "an hour", "5 minutes", "after 1 hour", "20 minutes", "15 mins", "45 minutes"],
        "suffixes": ["", "please", "immediately", "from now"],
        "verbs": ["set a shutdown timer", "schedule shutdown", "turn off pc in", "shutdown timer for", "set power off in"]
    },
    "RESTART": {
        "nouns": ["pc", "computer", "machine", "system", "workstation"],
        "suffixes": ["now", "immediately", "please", "right away", "instantly"],
        "verbs": ["restart", "reboot", "power cycle", "reset"]
    },
    "SHOW_SYSTEM_INFO": {
        "nouns": ["specs", "system info", "hardware details", "pc specifications", "os details", "cpu and ram info", "system details", "hardware specs profile", "specs profile", "system", "my system", "system information", "my pc specs"],
        "suffixes": ["", "please", "for me", "of this machine", "now"],
        "verbs": ["show", "display", "get", "view", "reveal", "print", "verify", "do some math to verify", "show me about", "tell me about", "show details of"]
    },
    "SYSTEM_DETAILS": {  # Alias safety fallback to match both naming structures
        "nouns": ["specs", "system info", "hardware details", "pc specifications", "os details", "cpu and ram info", "system details", "hardware specs profile", "specs profile", "system", "my system", "system information", "my pc specs"],
        "suffixes": ["", "please", "for me", "of this machine", "now"],
        "verbs": ["show", "display", "get", "view", "reveal", "print", "verify", "do some math to verify", "show me about", "tell me about", "show details of"]
    },
    "SHOW_TASKS": {
        "nouns": ["running tasks", "active processes", "running programs", "system processes", "task list", "background tasks"],
        "suffixes": ["", "please", "on this system", "now"],
        "verbs": ["show", "display", "list", "get", "view", "print"]
    },
    "SHUTDOWN_TIMER": {
        "nouns": ["10 minutes", "30 mins", "an hour", "5 minutes", "after 1 hour", "20 minutes", "15 mins", "45 minutes"],
        "suffixes": ["", "please", "now", "immediately"],
        "verbs": ["set shutdown timer", "schedule pc turn off", "shutdown timer in", "auto shutdown in", "timer for shutdown"]
    },
    "TRACE_ROUTE": {
        "nouns": ["to google.com", "to github.com", "to a domain", "to 8.8.8.8", "to host", "to server"],
        "suffixes": ["", "please", "now", "to debug route"],
        "verbs": ["tracert", "traceroute", "trace route", "track path", "map connection route"]
    },
    "QUIT_PROGRAM": {
        "nouns": ["program", "operations", "interface", "shellsense", "gui panel", "the application"],
        "suffixes": ["", "please", "now", "instantly", "immediately"],
        "verbs": ["stop", "exit", "quit", "close", "shut down", "kill"]
    },
    "DRIVER_MGMT": {
        "nouns": ["device manager", "drivers", "display drivers", "hdmi connection", "hardware drivers", "peripheral devices", "hdmi driver", "graphics driver", "hdmi lag", "monitor lag", "hdmi lag issues"],
        "suffixes": ["", "please", "now", "for lag issues", "to fix displays"],
        "verbs": ["open", "start", "launch", "run", "check", "update", "troubleshoot", "manage", "fix my", "resolve"]
    },
    "STORAGE_INFO": {
        "nouns": ["storage info", "disk space", "hard drive storage", "disk management", "free space", "storage details", "disk capacity", "drive allocation", "partition info"],
        "suffixes": ["", "please", "on this pc", "now", "for C drive"],
        "verbs": ["check", "show", "get", "view", "display", "manage", "monitor"]
    },
    "NEUTRAL": {
        "nouns": ["you doing", "the weather", "a joke", "your name", "about yourself", "how pc works", "with homework", "2 + 2", "the news", "the time", "coffee", "life", "universe"],
        "suffixes": ["", "today", "please", "for me", "right now"],
        "verbs": ["how are", "what is", "hello", "hi", "tell me", "can you", "why is", "who is", "explain", "what is the meaning of", "how do I make"]
    },
    "PROCESS_KILL": {
        "nouns": ["process", "task", "program", "app", "application", "running process", "frozen app", "pid"],
        "suffixes": ["", "now", "please", "by pid", "with force", "immediately"],
        "verbs": ["kill", "terminate", "stop", "force close", "end", "close", "force quit"]
    },
    "CHECK_RESOURCES": {
        "nouns": ["cpu usage", "ram utilization", "resource consumption", "memory load", "system resources", "hardware utilization", "performance statistics", "system load"],
        "suffixes": ["", "please", "on this system", "to monitor status"],
        "verbs": ["check", "show", "display", "get", "view", "monitor", "track"]
    }
}

def introduce_typos(text, probability=0.15):
    """Randomly introduces typos into the text to train the model to be typo-tolerant."""
    if random.random() > probability:
        return text
    
    words = text.split()
    if not words:
        return text
        
    # Pick a random word to modify
    idx = random.randint(0, len(words) - 1)
    word = words[idx]
    
    # We only modify words that are long enough
    if len(word) < 4:
        return text
        
    typo_type = random.choice(["swap", "drop", "replace"])
    
    if typo_type == "swap":
        # Swap two adjacent characters
        pos = random.randint(0, len(word) - 2)
        word_list = list(word)
        word_list[pos], word_list[pos+1] = word_list[pos+1], word_list[pos]
        words[idx] = "".join(word_list)
    elif typo_type == "drop":
        # Drop a character
        pos = random.randint(0, len(word) - 1)
        words[idx] = word[:pos] + word[pos+1:]
    elif typo_type == "replace":
        # Replace a character with a common typo or common misspelling
        if "calculator" in word:
            words[idx] = word.replace("calculator", "calcuator")
        elif "shutdown" in word:
            words[idx] = word.replace("shutdown", "shudown")
        elif "network" in word:
            words[idx] = word.replace("network", "netwrok")
        else:
            pos = random.randint(0, len(word) - 1)
            words[idx] = word[:pos] + random.choice("abcdefghijklmnopqrstuvwxyz") + word[pos+1:]
            
    return " ".join(words)

def generate_unique_sentences(intent, max_needed):
    """Generates unique phrases dynamically using rule combinatorics with typo injection."""
    if intent not in generation_rules:
        # Generic programmatic fallback if rules for a class are omitted
        base_nouns = ["system utility", "interface command", "operation", "process"]
        prefixes = ["please run", "execute", "open up", "start", "trigger"]
        sentences = set()
        for p in prefixes:
            for n in base_nouns:
                sentences.add(f"{p} {intent.lower().replace('_', ' ')} {n}".strip())
        return list(sentences)
    
    rule = generation_rules[intent]
    prefixes = ["", "can you", "please", "i need to", "i want to", "could you", "go ahead and"]
    
    sentences = set()
    # Generate all unique combinations
    combinations = list(itertools.product(prefixes, rule["verbs"], rule["nouns"], rule["suffixes"]))
    random.shuffle(combinations)
    
    for pref, verb, noun, suff in combinations:
        parts = [pref, verb, noun, suff]
        clean_str = " ".join([p.strip() for p in parts if p.strip()]).lower()
        # Introduce typos with 15% probability
        clean_str = introduce_typos(clean_str, probability=0.15)
        sentences.add(clean_str)
        if len(sentences) >= max_needed:
            break
            
    return list(sentences)

def balance_dataset():
    # 1. Load the original dataset
    try:
        df = pd.read_csv(INPUT_CSV)
        print(f"Loaded original dataset containing {len(df)} rows.")
    except FileNotFoundError:
        print(f"Error: Could not find {INPUT_CSV}. Creating a brand new balanced file.")
        df = pd.DataFrame(columns=["text", "intent"])

    # Show original class distribution
    print("\n--- Original Class Distribution ---")
    print(df['intent'].value_counts() if not df.empty else "No existing records.")

    # Get a distinct list of all target intents
    all_intents = list(set(list(df['intent'].unique()) + list(generation_rules.keys())))
    if 'SYSTEM_DETAILS' in all_intents and 'SHOW_SYSTEM_INFO' in all_intents:
        all_intents.remove('SYSTEM_DETAILS') # Clean up duplication if applicable

    balanced_dfs = []

    # 2. Iterate through each intent to downsample or augment with new rules/typos
    for intent in all_intents:
        intent_df = df[df['intent'] == intent].drop_duplicates(subset=['text'])
        current_len = len(intent_df)

        if current_len > 0:
            # Take a blend: up to 50% from original, and the rest from generation
            original_keep = min(current_len, TARGET_COUNT // 2)
            original_sample = intent_df.sample(n=original_keep, random_state=42)
            
            needed = TARGET_COUNT - original_keep
            generated_phrases = generate_unique_sentences(intent, needed * 3)
            existing_texts = set(original_sample['text'].tolist())
            unique_new_phrases = [p for p in generated_phrases if p not in existing_texts][:needed]
            
            new_rows_df = pd.DataFrame([{"text": p, "intent": intent} for p in unique_new_phrases])
            balanced_intent_df = pd.concat([original_sample, new_rows_df]).drop_duplicates(subset=['text'])
            
            # Safety check
            if len(balanced_intent_df) > TARGET_COUNT:
                balanced_intent_df = balanced_intent_df.iloc[:TARGET_COUNT]
            
            print(f"[{intent}] Blended original ({original_keep}) and generated ({len(balanced_intent_df) - original_keep}) to match {TARGET_COUNT}")
        else:
            # No original data, generate all
            generated_phrases = generate_unique_sentences(intent, TARGET_COUNT)
            balanced_intent_df = pd.DataFrame([{"text": p, "intent": intent} for p in generated_phrases])
            print(f"[{intent}] Generated all {TARGET_COUNT} from scratch")
            
        balanced_dfs.append(balanced_intent_df)

    # 3. Concatenate and save balanced results
    final_df = pd.concat(balanced_dfs).sample(frac=1, random_state=42).reset_index(drop=True)
    final_df.to_csv(OUTPUT_CSV, index=False)

    print("\n--- Balanced Class Distribution Saved ---")
    print(final_df['intent'].value_counts())
    print(f"\nFinal dataset complete. Saved {len(final_df)} rows to {OUTPUT_CSV}")

if __name__ == "__main__":
    balance_dataset()