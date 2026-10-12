import sys
import os

src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score
from shellsense.core.config import PROJECT_ROOT

csv_path = os.path.join(PROJECT_ROOT, 'test_set.csv')
model_path = os.path.join(PROJECT_ROOT, 'shellsense_v3.pkl')
fail_path = os.path.join(PROJECT_ROOT, 'failed_tests.csv')

if not os.path.exists(csv_path):
    print(f'Error: Test set not found at {csv_path}. Please run trainer.py first.')
    exit(1)

df = pd.read_csv(csv_path)
vectorizer, le, clf = joblib.load(model_path)
X = vectorizer.transform(df['text'].astype(str).str.lower())
y_true = le.transform(df['intent'])
y_pred = clf.predict(X)
accuracy = accuracy_score(y_true, y_pred)
df['predicted'] = le.inverse_transform(y_pred)
mismatches = df[df['intent'] != df['predicted']]
print(f'Test Set Samples: {len(df)}')
print(f'Out-of-Sample Accuracy: {accuracy * 100:.2f}%')
print(f'Total Errors: {len(mismatches)}')
if not mismatches.empty:
    mismatches.to_csv(fail_path, index=False)
    print(f'Mismatches saved to {fail_path}')
