import sys
import os

src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib
from shellsense.core.config import PROJECT_ROOT

csv_path = os.path.join(PROJECT_ROOT, 'Cleaned_text_intent.csv')
model_path = os.path.join(PROJECT_ROOT, 'shellsense_v3.pkl')
test_set_path = os.path.join(PROJECT_ROOT, 'test_set.csv')

def train_model():
    if not os.path.exists(csv_path):
        print(f'Error: Dataset not found at {csv_path}')
        return

    df = pd.read_csv(csv_path)
    indices = df.index
    train_idx, test_idx = train_test_split(
        indices, test_size=0.2, random_state=42, stratify=df['intent']
    )
    train_df = df.loc[train_idx]
    test_df = df.loc[test_idx]
    le = LabelEncoder()
    y_train = le.fit_transform(train_df['intent'])
    y_test = le.transform(test_df['intent'])
    vectorizer = TfidfVectorizer(max_features=1200, ngram_range=(1, 3), max_df=0.8, min_df=1)
    X_train = vectorizer.fit_transform(train_df['text'].astype(str).str.lower())
    X_test = vectorizer.transform(test_df['text'].astype(str).str.lower())
    clf = MLPClassifier(hidden_layer_sizes=(512, 256), max_iter=2000, early_stopping=True, validation_fraction=0.15, random_state=42)
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    new_accuracy = accuracy_score(y_test, y_pred)
    print(f'New Model Accuracy on Test Set: {new_accuracy * 100:.2f}%')
    should_save = True
    if os.path.exists(model_path):
        try:
            old_vec, old_le, old_clf = joblib.load(model_path)
            old_X_test = old_vec.transform(test_df['text'].astype(str).str.lower())
            old_pred = old_clf.predict(old_X_test)
            old_pred_labels = old_le.inverse_transform(old_pred)
            old_accuracy = accuracy_score(test_df['intent'], old_pred_labels)
            print(f'Existing Model Accuracy: {old_accuracy * 100:.2f}%')
            if new_accuracy < old_accuracy - 0.01:
                print('New model is significantly worse. Skipping save.')
                should_save = False
        except Exception as e:
            print(f'Could not load old model for comparison: {e}')
    if should_save:
        joblib.dump((vectorizer, le, clf), model_path)
        test_df.to_csv(test_set_path, index=False)
        print('Model and Test Set saved successfully.')

if __name__ == '__main__':
    train_model()
