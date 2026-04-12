import joblib

try:
    vectorizer, le, clf = joblib.load('shellsense_v1.pkl')
    print("Model loaded successfully")
except Exception as e:
    print(f"Error loading model: {e}")
    exit()

def predict_intent(user_text):
    text_vec = vectorizer.transform([user_text.lower()])
    prediction_id = clf.predict(text_vec)[0]
    probability = clf.predict_proba(text_vec).max()*100
    intent = le.inverse_transform([prediction_id])[0]
    return intent, probability

print("---Type the command to test the brain('Quit to exit)---")
while True:
    user_input = input("\nUser says: ")
    if user_input.lower() == 'quit':
        break
    intent, prob = predict_intent(user_input)
    print(f"Detected intent: {intent}")
    print(f"Confidence: {prob:.2f}%")