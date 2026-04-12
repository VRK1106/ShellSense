import pandas as pd
df = pd.read_csv('cmd_text_intent (1).csv')
def audit_dataset(df):
    print('---ShellSense data audit report---')
    null_counts = df.isnull().sum()
    print(f"\n[1] Missing values: {null_counts}")
    duplicates = df.duplicated().sum()
    print(f"\n[2] Duplicate rows: {duplicates}")
    unique_intents = df['intent'].unique()
    print(f"\nUnique intents found: {len(unique_intents)}")
    for intent in sorted(unique_intents):
        print(f" - {intent}")
    df['text_len'] = df['text'].astype(str).apply(len)
    suspicious_short = df[df['text_len'] < 3]
    print(f"\n[4] Suspiciously short entries(Len < 3): {len(suspicious_short)}")
    print(f"\n[5] Class Distribution (Target over spread): ")
    print(df['intent'].value_counts())
    conflicts = df.groupby('text')['intent'].nunique()
    conflicting_text = conflicts[conflicts > 1]
    if not conflicting_text.empty:
        print(f"⚠️ Warning: Found {len(conflicting_text)} text strings mapped to multiple intents!")
        print(df[df['text'].isin(conflicting_text.index)].sort_values(by='text'))
audit_dataset(df)