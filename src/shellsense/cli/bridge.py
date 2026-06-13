import sys
import os

# Auto-resolve 'src' path for standalone execution
current_dir = os.path.dirname(os.path.abspath(__file__))
src_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if src_root not in sys.path:
    sys.path.insert(0, src_root)

from shellsense.services.brain_service import BrainService
from shellsense.services.executor import CommandExecutor

def run_cli():
    brain = BrainService()
    print("--- ShellSense CLI Bridge Active ---")
    print("Type 'quit' to exit.")
    
    while True:
        try:
            user_input = input("\nHow can I help you? ").strip()
            if not user_input:
                continue
            if user_input.lower() == 'quit':
                break
                
            intent, confidence = brain.predict(user_input)
            print(f"Detected intent: {intent} (Confidence: {confidence:.2f})")
            
            if intent == "QUIT_PROGRAM":
                break
                
            CommandExecutor.execute(intent, user_input)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    run_cli()
