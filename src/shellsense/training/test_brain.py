import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from shellsense.services.brain_service import BrainService

def main():
    brain = BrainService()
    if not brain.is_loaded:
        print("Failed to load brain.")
        return

    print("---Type the command to test the brain('Quit to exit)---")
    while True:
        try:
            user_input = input("\nUser says: ").strip()
            if not user_input:
                continue
            if user_input.lower() == 'quit':
                break
            
            intent, prob = brain.predict(user_input)
            print(f"Detected intent: {intent}")
            print(f"Confidence: {prob*100:.2f}%")
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()