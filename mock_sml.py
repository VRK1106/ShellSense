import time

def query_qwen_raw(prompt):
    """
    Mimics query_qwen_raw(prompt) in generate_qwen_dataset.py.
    Returns a hardcoded text response instead of querying the actual SML (Qwen) model.
    """
    print(f"[MOCK SML] Received prompt: {prompt[:100]}...")
    
    # Simulate a small network delay
    time.sleep(0.1)
    
    # Hardcoded mock response mimicking Qwen's output format (newline-separated phrases)
    mock_phrases = [
        "check the local ip address",
        "show my network ip configuration",
        "what is my current ip",
        "display network settings",
        "ping the google server"
    ]
    
    return "\n".join(mock_phrases)

if __name__ == "__main__":
    test_prompt = "Generate exactly 5 phrases for Intent: CHECK_IP"
    response = query_qwen_raw(test_prompt)
    print("\n--- Mock Response ---")
    print(response)
