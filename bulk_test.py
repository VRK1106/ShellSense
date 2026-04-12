import joblib
import pandas as pd
from sklearn.metrics import accuracy_score

df = pd.read_csv('Cleaned_text_intent.csv')
vectorizer, le, clf = joblib.load('shellsense_v2.pkl')

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
    mismatches.to_csv('failed_tests.csv', index=False)
    print("Mismatches saved to failed_tests.csv")