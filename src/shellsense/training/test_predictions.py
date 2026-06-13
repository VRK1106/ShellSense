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
        ("show cpu utilization and load", "CHECK_RESOURCES"),

        ("what is my current ip address", "CHECK_IP"),
    ("check my local ipconfig", "CHECK_IP"),
    ("show my ethernet ipv4 address", "CHECK_IP"),
    ("reveal my internal network ip", "CHECK_IP"),
    ("get my machine's ip details", "CHECK_IP"),
    ("open cmd to show my ip configuration", "CHECK_IP"),  # Boundary: "cmd"
    ("check ipv4 gateway properties", "CHECK_IP"),  # Boundary: "properties"
    ("print local network adapter ip", "CHECK_IP"),

    # ==========================================
    # 5. DNS_LOOKUP (Domain resolution)
    # ==========================================
    ("run nslookup on google.com", "DNS_LOOKUP"),
    ("resolve the ip address for github.com", "DNS_LOOKUP"),
    ("do a dns query for microsoft.com", "DNS_LOOKUP"),
    ("check dns records for our domain", "DNS_LOOKUP"),
    ("find the hostname ip of yahoo.com", "DNS_LOOKUP"),
    ("resolve website dns information", "DNS_LOOKUP"),
    ("lookup dns resolution path to host", "DNS_LOOKUP"),  # Boundary: "path" vs traceroute

    # ==========================================
    # 6. TRACE_ROUTE (Path hops)
    # ==========================================
    ("run a traceroute connection to amazon.com", "TRACE_ROUTE"),
    ("tracert network path to github.com", "TRACE_ROUTE"),
    ("track the hop route to the web server", "TRACE_ROUTE"),
    ("perform a traceroute query to trace connection", "TRACE_ROUTE"),
    ("show path route for target host google", "TRACE_ROUTE"),
    ("trace connection route to see dns latency", "TRACE_ROUTE"),  # Boundary: "dns" vs DNS_LOOKUP
    ("calculate ping latency hops across networks", "TRACE_ROUTE"),  # Boundary: "ping" vs PING_GOOGLE

    # ==========================================
    # 7. PING_GOOGLE (Connectivity testing)
    # ==========================================
    ("ping google.com to test latency", "PING_GOOGLE"),
    ("run a quick ping check to google servers", "PING_GOOGLE"),
    ("test internet connection ping to google", "PING_GOOGLE"),
    ("check web connectivity using ping test", "PING_GOOGLE"),
    ("am i connected to internet ping 8.8.8.8", "PING_GOOGLE"),
    ("ping google dns properties to test route", "PING_GOOGLE"),  # Boundary: dns, route

    # ==========================================
    # 8. OPEN_NETWORK_SETTINGS (OS Settings Panel)
    # ==========================================
    ("open network and internet settings panel", "OPEN_NETWORK_SETTINGS"),
    ("show my active network connections properties", "OPEN_NETWORK_SETTINGS"),
    ("view my wifi adapter options", "OPEN_NETWORK_SETTINGS"),
    ("go to network adapter settings config", "OPEN_NETWORK_SETTINGS"),
    ("manage wifi sharing options window", "OPEN_NETWORK_SETTINGS"),
    ("open network properties to check connections", "OPEN_NETWORK_SETTINGS"),

    # ==========================================
    # 9. OPEN_TASK_MANAGER (GUI Launch)
    # ==========================================
    ("open task manager list", "OPEN_TASK_MANAGER"),
    ("open task manager window", "OPEN_TASK_MANAGER"),
    ("launch taskmgr application", "OPEN_TASK_MANAGER"),
    ("bring up task manager console", "OPEN_TASK_MANAGER"),
    ("open the active process monitor GUI", "OPEN_TASK_MANAGER"),
    ("start task manager to check frozen software", "OPEN_TASK_MANAGER"),

    # ==========================================
    # 10. SHOW_TASKS (CLI List output)
    # ==========================================
    ("list all active running tasks", "SHOW_TASKS"),
    ("show currently running background processes", "SHOW_TASKS"),
    ("get system process list in command prompt", "SHOW_TASKS"),
    ("print active tasks running right now", "SHOW_TASKS"),
    ("display currently running software services", "SHOW_TASKS"),
    ("show active process log in console", "SHOW_TASKS"),

    # ==========================================
    # 11. RESTART / LOCK_SCREEN / SYSTEM_INFO (System Controls)
    # ==========================================
    ("reboot my windows computer now", "RESTART"),
    ("restart the workstation system", "RESTART"),
    ("lock my computer screen right now", "LOCK_SCREEN"),
    ("log out of my current windows session", "LOCK_SCREEN"),
    ("display my computer specs details", "SHOW_SYSTEM_INFO"),
    ("view detailed system configuration information", "SHOW_SYSTEM_INFO"),

    # ==========================================
    # 12. UTILITIES (Browser, Calculator, Command Shell, Program Exit)
    # ==========================================
    ("launch default web browser", "OPEN_NET"),
    ("open default browser to run search", "OPEN_NET"),
    ("launch the default calculator app", "OPEN_CALCULATOR"),
    ("open the command prompt terminal", "OPEN_CMD"),
    ("start a new cmd window", "OPEN_CMD"),
    ("close shellsense application window", "QUIT_PROGRAM"),
    ("quit program operations now", "QUIT_PROGRAM")
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
