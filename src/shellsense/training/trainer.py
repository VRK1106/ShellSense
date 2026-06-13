import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
from sklearn.neural_network import MLPClassifier
import joblib

import os

# Adjust paths relative to project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
csv_path = os.path.join(BASE_DIR, 'Cleaned_text_intent.csv')
model_path = os.path.join(BASE_DIR, 'shellsense_v3.pkl')

df = pd.read_csv(csv_path)

le = LabelEncoder()
y = le.fit_transform(df['intent'])

vectorizer = TfidfVectorizer(
    max_features=1200, 
    ngram_range=(1, 3), 
    max_df=0.8, 
    min_df=1
)

X = vectorizer.fit_transform(df['text'].astype(str).str.lower())

clf = MLPClassifier(
    hidden_layer_sizes=(512, 256), 
    max_iter=2000, 
    early_stopping=True,
    validation_fraction=0.15,
    random_state=42
)

clf.fit(X, y)
joblib.dump((vectorizer, le, clf), model_path)