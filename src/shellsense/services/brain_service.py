import joblib
import logging
from shellsense.core.config import MODEL_PATH

# Force PyInstaller to package scikit-learn and its submodules
import sklearn
import sklearn.feature_extraction.text
import sklearn.preprocessing
import sklearn.neural_network

logger = logging.getLogger(__name__)

class BrainService:
    def __init__(self, model_path=MODEL_PATH):
        self.model_path = model_path
        self.vectorizer = None
        self.le = None
        self.clf = None
        self.is_loaded = False
        self.load_model()

    def load_model(self):
        try:
            self.vectorizer, self.le, self.clf = joblib.load(self.model_path)
            self.is_loaded = True
            logger.info(f"Model loaded successfully from {self.model_path}")
        except Exception as e:
            logger.error(f"Error loading model from {self.model_path}: {e}")
            self.is_loaded = False

    def predict(self, text):
        if not self.is_loaded:
            logger.warning("Prediction attempted on uninitialized BrainService.")
            return None, 0.0

        text_vec = self.vectorizer.transform([text.lower()])
        probs = self.clf.predict_proba(text_vec)[0]
        max_prob = max(probs)
        prediction_id = self.clf.predict(text_vec)[0]
        intent = self.le.inverse_transform([prediction_id])[0]
        
        return intent, max_prob
