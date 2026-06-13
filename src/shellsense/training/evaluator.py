import joblib
import pandas as pd
from sklearn.metrics import accuracy_score
import os

# Adjust paths relative to project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
csv_path = os.path.join(BASE_DIR, 'Cleaned_text_intent.csv')
model_path = os.path.join(BASE_DIR, 'shellsense_v3.pkl')
fail_path = os.path.join(BASE_DIR, 'failed_tests.csv')

df = pd.read_csv(csv_path)
vectorizer, le, clf = joblib.load(model_path)

X = vectorizer.transform(df['text'].astype(str).str.lower())
y_true = le.transform(df['intent'])
y_pred = clf.predict(X)

accuracy = accuracy_score(y_true, y_pred)
df['predicted'] = le.inverse_transform(y_pred)
mismatches = df[df['intent'] != df['predicted']]

print(f"Total Samples: {len(df)}")
print(f"Overall Accuracy: {accuracy * 100:.2f}%")
print(f"Total Errors: {len(mismatches)}")

if not mismatches.empty:
    mismatches.to_csv(fail_path, index=False)
    print(f"Mismatches saved to {fail_path}")