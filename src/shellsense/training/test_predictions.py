import sys
import os

# Resolve paths
current_dir = os.path.dirname(os.path.abspath(__file__))
src_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if src_root not in sys.path:
    sys.path.insert(0, src_root)

from shellsense.services.brain_service import BrainService

def main():
    brain = BrainService()
    if not brain.is_loaded:
        print("Failed to load brain.")
        return

    test_cases = [
        # Network settings & connectivity
        ("open wifi settings panel", "OPEN_NETWORK_SETTINGS"),
        ("am I online? ping google", "PING_GOOGLE"),
        ("what is my current network local ip?", "CHECK_IP"),
        ("run traceroute to 8.8.8.8", "TRACE_ROUTE"),
        ("resolve the ip for wikipedia.org", "DNS_LOOKUP"),

        # System operations
        ("turn off the computer right now", "POWER_OFF"),
        ("reboot my computer", "RESTART"),
        ("lock my screen for safety", "LOCK_SCREEN"),
        ("schedule shutdown in 45 minutes", "POWER_OFF_TIMER"),
        
        # Tools & Utilities
        ("open the calculator app", "OPEN_CALCULATOR"),
        ("open command prompt console", "OPEN_CMD"),
        ("exit shellsense program", "QUIT_PROGRAM"),
        
        # Process and Resources (formerly weak classes)
        ("open task manager list", "OPEN_TASK_MANAGER"),
        ("kill chrome process immediately", "PROCESS_KILL"),
        ("force quit slack with PID 9920", "PROCESS_KILL"),
        ("how much space is left on my C drive?", "STORAGE_INFO"),
        ("check hard disk storage capacity", "STORAGE_INFO"),
        ("how much ram is currently free?", "CHECK_RESOURCES"),
        ("show cpu utilization and load", "CHECK_RESOURCES")
    ]

    print("--- ShellSense Brain Prediction Verification ---")
    passed = 0
    for query, expected in test_cases:
        intent, confidence = brain.predict(query)
        status = "PASS" if intent == expected else "FAIL"
        if intent == expected:
            passed += 1
        print(f"Query: '{query}'")
        print(f"  Expected: {expected}")
        print(f"  Predicted: {intent} (Confidence: {confidence * 100:.2f}%) -> {status}")
        print("-" * 50)

    print(f"\nResults: {passed}/{len(test_cases)} tests passed ({passed/len(test_cases)*100:.1f}%)")

if __name__ == "__main__":
    main()
