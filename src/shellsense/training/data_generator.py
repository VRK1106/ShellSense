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
    "OPEN_NET": {
        "verbs": ["open", "start", "launch", "run", "go to", "access"],
        "nouns": ["default browser", "web browser", "the internet", "the net", "chrome browser", "edge browser", "web portal"],
        "suffixes": ["", "please", "now", "to surf", "to go online"]
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
    "SHOW_SYSTEM_INFO": {
        "verbs": ["show", "display", "get", "view", "reveal", "print"],
        "nouns": ["specs", "system info", "hardware details", "pc specifications", "os details", "cpu and ram info", "system details"],
        "suffixes": ["", "please", "for me", "of this machine", "now"]
    },
    "SYSTEM_DETAILS": {  # Alias safety fallback to match both naming structures
        "verbs": ["show", "display", "get", "view", "reveal", "print"],
        "nouns": ["specs", "system info", "hardware details", "pc specifications", "os details", "cpu and ram info", "system details"],
        "suffixes": ["", "please", "for me", "of this machine", "now"]
    },
    "SHOW_TASKS": {
        "verbs": ["show", "display", "list", "get", "view", "print"],
        "nouns": ["running tasks", "active processes", "running programs", "system processes", "task list", "background tasks"],
        "suffixes": ["", "please", "on this system", "now"]
    },
    "SHUTDOWN_TIMER": {
        "verbs": ["set shutdown timer", "schedule pc turn off", "shutdown timer in", "auto shutdown in", "timer for shutdown"],
        "nouns": ["10 minutes", "30 mins", "an hour", "5 minutes", "after 1 hour", "20 minutes", "15 mins", "45 minutes"],
        "suffixes": ["", "please", "now", "immediately"]
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
    }
}

def generate_unique_sentences(intent, max_needed):
    """Generates unique phrases dynamically using rule combinatorics."""
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

    # 2. Iterate through each intent to downsample or augment
    for intent in all_intents:
        intent_df = df[df['intent'] == intent].drop_duplicates(subset=['text'])
        current_len = len(intent_df)

        if current_len > TARGET_COUNT:
            # DOWNSAMPLE overrepresented classes (e.g., SHUTDOWN_TIMER)
            balanced_intent_df = intent_df.sample(n=TARGET_COUNT, random_state=42)
            print(f"[{intent}] Downsampled from {current_len} to {TARGET_COUNT}")
        elif current_len < TARGET_COUNT:
            # AUGMENT underrepresented classes programmatically
            needed = TARGET_COUNT - current_len
            generated_phrases = generate_unique_sentences(intent, needed * 3)  # Get extra to ensure no collision
            
            # Filter out phrases that already exist in the original data
            existing_texts = set(intent_df['text'].tolist())
            unique_new_phrases = [p for p in generated_phrases if p not in existing_texts][:needed]
            
            new_rows_df = pd.DataFrame([{"text": p, "intent": intent} for p in unique_new_phrases])
            balanced_intent_df = pd.concat([intent_df, new_rows_df]).drop_duplicates(subset=['text'])
            
            # Safety checks in case final totals drift
            if len(balanced_intent_df) > TARGET_COUNT:
                balanced_intent_df = balanced_intent_df.iloc[:TARGET_COUNT]
            elif len(balanced_intent_df) < TARGET_COUNT:
                print(f"Warning: Could only generate {len(balanced_intent_df)} unique rows for {intent}.")
            
            print(f"[{intent}] Augmented from {current_len} to {len(balanced_intent_df)}")
        else:
            # Already matches the target
            balanced_intent_df = intent_df
            print(f"[{intent}] Maintained perfectly at {TARGET_COUNT}")
            
        balanced_dfs.append(balanced_intent_df)

    # 3. Concatenate and save balanced results
    final_df = pd.concat(balanced_dfs).sample(frac=1, random_state=42).reset_index(drop=True)
    final_df.to_csv(OUTPUT_CSV, index=False)

    print("\n--- Balanced Class Distribution Saved ---")
    print(final_df['intent'].value_counts())
    print(f"\nFinal dataset complete. Saved {len(final_df)} rows to {OUTPUT_CSV}")

if __name__ == "__main__":
    balance_dataset()