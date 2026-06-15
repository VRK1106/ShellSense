import re

def evaluate_timer(query: str):
    q = query.lower().strip()
    
    # Cancellation checks
    if q in ('cancel timer', 'stop timer', 'clear timer', 'cancel timers', 'stop timers'):
        return True, "Cancel Timers"
        
    if q.startswith("cancel timer ") or q.startswith("stop timer ") or q.startswith("clear timer "):
        if q.startswith("cancel timer "):
            task_query = q[13:]
        elif q.startswith("stop timer "):
            task_query = q[11:]
        else:
            task_query = q[12:]
        task_query = task_query.strip()
        if task_query:
            return True, f"Cancel Timer Name: {task_query}"
            
    # Match: "remind me to [task] in [X] [units]"
    match_remind = re.match(
        r'^remind\s+me\s+to\s+(.+?)\s+in\s+(\d+(?:\.\d+)?)\s*(second|sec|minute|min|hour|hr)s?$',
        q
    )
    if match_remind:
        task = match_remind.group(1).strip()
        value = float(match_remind.group(2))
        unit = match_remind.group(3)
        
        duration_ms = calculate_ms(value, unit)
        time_desc = f"{value} {unit}" + ("s" if value != 1 else "")
        # Keep original casing of the task name if possible, or just capitalize the first letter
        task_display = task.capitalize()
        return True, f"Timer Created: {task_display}|{duration_ms}|{time_desc}"
        
    # Match: "timer [X] [units]" or "timer [X]"
    match_timer = re.match(
        r'^timer\s+(\d+(?:\.\d+)?)(?:\s*(second|sec|minute|min|hour|hr)s?)?$',
        q
    )
    if match_timer:
        value = float(match_timer.group(1))
        unit = match_timer.group(2) if match_timer.group(2) else "minute"
        
        duration_ms = calculate_ms(value, unit)
        time_desc = f"{value} {unit}" + ("s" if value != 1 else "")
        return True, f"Timer Created: Timer|{duration_ms}|{time_desc}"
        
    return False, None

def calculate_ms(value: float, unit: str) -> int:
    if unit in ('second', 'sec'):
        multiplier = 1000
    elif unit in ('minute', 'min'):
        multiplier = 60 * 1000
    else:  # 'hour', 'hr'
        multiplier = 3600 * 1000
    return int(value * multiplier)
