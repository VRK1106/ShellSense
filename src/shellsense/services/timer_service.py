import re

def evaluate_timer(query: str):
    q = query.lower().strip()
    
    # Help formats check / pane triggers
    if q in ('timer', 'timers', 'set timer', 'set a timer', 'timer pane'):
        return True, "Open Timer: timer"
        
    if q in ('alarm', 'alarms', 'set alarm', 'set a alarm', 'set an alarm', 'alarm pane'):
        return True, "Open Alarm: alarm"

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
            
    # Pattern 1: (remind me to |set [a/an/the] timer to |timer to ) [task] (in |after ) [time] [unit]
    # e.g., set a timer to sleep after 10 minutes
    match1 = re.match(
        r'^(?:remind\s+me\s+to|set\s+(?:a\s+|an\s+|the\s+)?timer\s+to|timer\s+to)\s+(.+?)\s+(?:in|after)\s+(\d+(?:\.\d+)?)\s*(second|sec|minute|min|hour|hr)s?$',
        q
    )
    if match1:
        task = match1.group(1).strip()
        value = float(match1.group(2))
        unit = match1.group(3)
        duration_ms = calculate_ms(value, unit)
        time_desc = f"{value} {unit}" + ("s" if value != 1 else "")
        return True, f"Timer Created: {task.capitalize()}|{duration_ms}|{time_desc}"

    # Pattern 2: (set [a/an/the] timer for |timer for ) [time] to [task]
    # e.g., set a timer for 10 minutes to eat
    match2 = re.match(
        r'^(?:set\s+(?:a\s+|an\s+|the\s+)?timer\s+for|timer\s+for)\s+(\d+(?:\.\d+)?)\s*(second|sec|minute|min|hour|hr)s?\s+to\s+(.+?)$',
        q
    )
    if match2:
        value = float(match2.group(1))
        unit = match2.group(2)
        task = match2.group(3).strip()
        duration_ms = calculate_ms(value, unit)
        time_desc = f"{value} {unit}" + ("s" if value != 1 else "")
        return True, f"Timer Created: {task.capitalize()}|{duration_ms}|{time_desc}"

    # Pattern 3: (set [a/an/the] timer for |timer for ) [time]
    # e.g., set a timer for 10 minutes
    match3 = re.match(
        r'^(?:set\s+(?:a\s+|an\s+|the\s+)?timer\s+for|timer\s+for)\s+(\d+(?:\.\d+)?)\s*(second|sec|minute|min|hour|hr)s?$',
        q
    )
    if match3:
        value = float(match3.group(1))
        unit = match3.group(2)
        duration_ms = calculate_ms(value, unit)
        time_desc = f"{value} {unit}" + ("s" if value != 1 else "")
        return True, f"Timer Created: Timer|{duration_ms}|{time_desc}"

    # Pattern 4: timer [time] to [task]
    # e.g., timer 10 minutes to eat
    match4 = re.match(
        r'^timer\s+(\d+(?:\.\d+)?)\s*(second|sec|minute|min|hour|hr)s?\s+to\s+(.+?)$',
        q
    )
    if match4:
        value = float(match4.group(1))
        unit = match4.group(2)
        task = match4.group(3).strip()
        duration_ms = calculate_ms(value, unit)
        time_desc = f"{value} {unit}" + ("s" if value != 1 else "")
        return True, f"Timer Created: {task.capitalize()}|{duration_ms}|{time_desc}"

    # Pattern 5: timer [time]
    # e.g., timer 10 minutes
    match5 = re.match(
        r'^timer\s+(\d+(?:\.\d+)?)(?:\s*(second|sec|minute|min|hour|hr)s?)?$',
        q
    )
    if match5:
        value = float(match5.group(1))
        unit = match5.group(2) if match5.group(2) else "minute"
        duration_ms = calculate_ms(value, unit)
        time_desc = f"{value} {unit}" + ("s" if value != 1 else "")
        return True, f"Timer Created: Timer|{duration_ms}|{time_desc}"

    # Pattern 6: (remind me to |set [a/an/the] timer to |timer to ) [task] (in |after ) [time] (default unit: minutes)
    # e.g., set a timer to sleep after 10
    match6 = re.match(
        r'^(?:remind\s+me\s+to|set\s+(?:a\s+|an\s+|the\s+)?timer\s+to|timer\s+to)\s+(.+?)\s+(?:in|after)\s+(\d+(?:\.\d+)?)$',
        q
    )
    if match6:
        task = match6.group(1).strip()
        value = float(match6.group(2))
        unit = "minute"
        duration_ms = calculate_ms(value, unit)
        time_desc = f"{value} {unit}" + ("s" if value != 1 else "")
        return True, f"Timer Created: {task.capitalize()}|{duration_ms}|{time_desc}"

    return False, None

def calculate_ms(value: float, unit: str) -> int:
    if unit in ('second', 'sec'):
        multiplier = 1000
    elif unit in ('minute', 'min'):
        multiplier = 60 * 1000
    else:  # 'hour', 'hr'
        multiplier = 3600 * 1000
    return int(value * multiplier)
