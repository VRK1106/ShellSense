import pandas as pd
df = pd.read_csv('cmd_text_intent (1).csv')
df = df[df['intent'] != 'intent']
intent_map = {
    "SHUTDOWN_TIMER": "POWER_OFF_TIMER",
    "OPEN_NET": "OPEN_NETWORK_SETTINGS",
    "SHOW_TASKS": "OPEN_TASK_MANAGER",
    "SHOW_SYSTEM_INFO": "SYSTEM_DETAILS"
}
df['intent'] = df['intent'].replace(intent_map)
df = df.drop_duplicates(subset = ['text', 'intent'])
balanced_df = df.groupby('intent').apply(lambda x: x.sample(n=min(len(x), 500), random_state=42)).reset_index(drop=True)
balanced_df.to_csv("Cleaned_text_intent.csv", index = False)
print(f"Unique intents now: {balanced_df['intent'].nunique()}")