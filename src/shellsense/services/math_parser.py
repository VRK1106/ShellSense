import re
import math
import os
import json

SAFE_MATH_DICT = {
    'abs': abs,
    'round': round,
    'pow': math.pow,
    'sqrt': math.sqrt,
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'log': math.log,
    'log10': math.log10,
    'exp': math.exp,
    'pi': math.pi,
    'e': math.e,
}

def clean_query(query: str) -> str:
    # Lowercase, strip punctuation like ? or = at the end
    q = query.lower().strip()
    q = re.sub(r'[?=\s]+$', '', q)
    # Remove fill words at the beginning
    q = re.sub(r'^(what is|calculate|compute|evaluate|please|do some math to verify|find|get)\s+', '', q)
    return q

def translate_to_expression(query: str) -> str:
    q = clean_query(query)
    
    # 1. Percentage: X % of Y or X percent of Y or X percentage of Y
    q = re.sub(r'(\d+(?:\.\d+)?)\s*(?:%|percent|percentage)\s+of\s+(\d+(?:\.\d+)?)', r'((\1 / 100) * \2)', q)
    
    # 2. Addition: add X and Y, sum of X and Y, sum X and Y
    q = re.sub(r'^(?:add|sum\s+of|sum)\s+(\d+(?:\.\d+)?)\s+and\s+(\d+(?:\.\d+)?)', r'(\1 + \2)', q)
    # X plus Y
    q = re.sub(r'(\d+(?:\.\d+)?)\s+plus\s+(\d+(?:\.\d+)?)', r'(\1 + \2)', q)
    
    # 3. Subtraction: subtract X from Y
    q = re.sub(r'^subtract\s+(\d+(?:\.\d+)?)\s+from\s+(\d+(?:\.\d+)?)', r'(\2 - \1)', q)
    # X minus Y / X subtract Y
    q = re.sub(r'(\d+(?:\.\d+)?)\s+(?:minus|subtract)\s+(\d+(?:\.\d+)?)', r'(\1 - \2)', q)
    
    # 4. Multiplication: multiply X by/and Y
    q = re.sub(r'^multiply\s+(\d+(?:\.\d+)?)\s+(?:by|and)\s+(\d+(?:\.\d+)?)', r'(\1 * \2)', q)
    # X times Y / X multiplied by Y
    q = re.sub(r'(\d+(?:\.\d+)?)\s*(?:times|multiplied\s+by)\s*(\d+(?:\.\d+)?)', r'(\1 * \2)', q)
    
    # 5. Division: divide X by Y
    q = re.sub(r'^divide\s+(\d+(?:\.\d+)?)\s+by\s+(\d+(?:\.\d+)?)', r'(\1 / \2)', q)
    # X divided by Y / X over Y
    q = re.sub(r'(\d+(?:\.\d+)?)\s*(?:divided\s+by|over)\s*(\d+(?:\.\d+)?)', r'(\1 / \2)', q)
    
    # 6. Power: X power Y, X raised to Y, X to the power of Y, X ^ Y
    q = re.sub(r'(\d+(?:\.\d+)?)\s*(?:\^|power|raised\s+to)\s*(\d+(?:\.\d+)?)', r'(\1 ** \2)', q)
    q = re.sub(r'(\d+(?:\.\d+)?)\s+to\s+the\s+power\s+of\s+(\d+(?:\.\d+)?)', r'(\1 ** \2)', q)
    
    # 7. Square root: square root of X, sqrt of X, sqrt X
    q = re.sub(r'(?:square\s+root\s+of|sqrt\s+of|sqrt)\s+(\d+(?:\.\d+)?)', r'sqrt(\1)', q)
    
    # 8. Logarithm: log of X
    q = re.sub(r'log\s+of\s+(\d+(?:\.\d+)?)', r'log(\1)', q)
    
    # 9. Trigonometry: sin of X, cos of X, tan of X
    q = re.sub(r'(?:sin|sine)\s+of\s+(\d+(?:\.\d+)?)', r'sin(\1)', q)
    q = re.sub(r'(?:cos|cosine)\s+of\s+(\d+(?:\.\d+)?)', r'cos(\1)', q)
    q = re.sub(r'(?:tan|tangent)\s+of\s+(\d+(?:\.\d+)?)', r'tan(\1)', q)
    
    return q

def is_math_expression(expression: str) -> bool:
    # Check if expression only contains valid math characters and function names
    clean_expr = expression.replace('**', '^')
    # Remove all safe function/constant names
    for name in SAFE_MATH_DICT.keys():
        clean_expr = clean_expr.replace(name, '')
    
    # Now check if it only contains digits, dots, spaces, and basic operators
    return bool(re.match(r'^[0-9+\-*/().\s^%]+$', clean_expr))

def evaluate_help(query: str):
    q = query.lower().strip()
    if q in ('help', 'commands', 'functions', '?', 'list'):
        snippets = load_snippets()
        snippet_keys = ", ".join(f"<code>{k}</code>" for k in snippets.keys()) if snippets else "None"
        help_html = (
            "<div style='line-height: 1.4; font-family: \"Segoe UI\", sans-serif; color: #00bcd4;'>"
            "<b style='color: #ffffff; font-size: 17px;'>✨ ShellSense Available Functions:</b><br>"
            "<span style='color: #ffffff;'>•</span> <b>Math</b>: <code>15% of 80</code>, <code>sqrt(144)</code>, <code>sin(pi/2)</code>, <code>5 * (3 + 2)</code><br>"
            "<span style='color: #ffffff;'>•</span> <b>Currency</b>: <code>100 usd to eur</code>, <code>50 gbp to inr</code>, <code>1000 jpy to usd</code><br>"
            "<span style='color: #ffffff;'>•</span> <b>Timezone</b>: <code>10:30 am est to ist</code>, <code>4 pm pst to gmt</code>, <code>12:00 cet in gmt</code><br>"
            "<span style='color: #ffffff;'>•</span> <b>Physical Units</b>: <code>10 miles to km</code>, <code>100 f to c</code>, <code>5 gallons to liters</code><br>"
            "<span style='color: #ffffff;'>•</span> <b>Number Bases</b>: <code>hex ff to binary</code>, <code>decimal 255 to hex</code><br>"
            "<span style='color: #ffffff;'>•</span> <b>Translation</b>: <code>hello in tamil</code>, <code>welcome german</code>, <code>vanakkam in english</code><br>"
            "<span style='color: #ffffff;'>•</span> <b>Snippets</b>: <code>copy/paste [key]</code> where key is: " + snippet_keys + "<br>"
            "<span style='color: #ffffff;'>•</span> <b>System (Press Enter)</b>: <code>lock screen</code>, <code>system details</code>, <code>ping google</code>, "
            "<code>shutdown in 1 hour</code>, <code>abort action</code>"
            "</div>"
        )
        return True, help_html
    return False, None

def load_snippets():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    snippets_path = os.path.join(base_dir, "snippets.json")
    
    if not os.path.exists(snippets_path):
        default_snippets = {
            "email": "user@example.com",
            "zoom": "https://zoom.us/j/1234567890",
            "address": "123 Main Street, City, Country",
            "phone": "+1-234-567-8900",
            "link": "https://github.com/VRK1106/ShellSense"
        }
        try:
            with open(snippets_path, 'w', encoding='utf-8') as f:
                json.dump(default_snippets, f, indent=4)
        except Exception:
            return default_snippets
        return default_snippets
        
    try:
        with open(snippets_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def evaluate_snippets(query: str):
    q = query.lower().strip()
    clean_q = re.sub(r'^(?:copy\s+my|paste\s+my|get\s+my|show\s+my|my|copy|paste|get)\s+', '', q)
    clean_q = clean_q.strip()
    norm_q = re.sub(r'[^a-z0-9]', '', clean_q)
    
    raw_snippets = load_snippets()
    # Map normalized key -> (original key, value)
    norm_snippets = {}
    for k, v in raw_snippets.items():
        norm_k = re.sub(r'[^a-z0-9]', '', k.lower())
        norm_snippets[norm_k] = (k, v)
        
    # 1. Exact match on normalized keys
    if norm_q in norm_snippets:
        orig_key, val = norm_snippets[norm_q]
        return True, f"Copied: {val}"
        
    # 2. Substring match on normalized keys
    matches = []
    for norm_key in norm_snippets:
        if norm_q in norm_key or norm_key in norm_q:
            matches.append(norm_key)
            
    if len(matches) == 1:
        orig_key, val = norm_snippets[matches[0]]
        return True, f"Copied: {val}"
    elif len(matches) > 1:
        keys_str = ", ".join(f"'{norm_snippets[m][0]}'" for m in matches)
        return True, f"Error: Multiple matches found ({keys_str}). Please be more specific."
        
    # 3. Fuzzy similarity match (for typos like "linkedin" -> "linkdin")
    import difflib
    best_match = None
    highest_ratio = 0.0
    for norm_key in norm_snippets:
        ratio = difflib.SequenceMatcher(None, norm_q, norm_key).ratio()
        if ratio > highest_ratio:
            highest_ratio = ratio
            best_match = norm_key
            
    if highest_ratio >= 0.75 and best_match:
        orig_key, val = norm_snippets[best_match]
        return True, f"Copied: {val}"
            
    return False, None

def evaluate_math(query: str):
    """
    Translates and evaluates a math query safely.
    Returns (success, result_or_error_msg)
    """
    is_help, help_res = evaluate_help(query)
    if is_help:
        return True, help_res

    # Try snippets next
    is_snippet, snippet_res = evaluate_snippets(query)
    if is_snippet:
        return True, snippet_res

    # Try unit/currency/timezone/base conversions first
    from shellsense.services.conversion_parser import evaluate_conversion, evaluate_translation
    
    is_conv, conv_res = evaluate_conversion(query)
    if is_conv:
        return True, conv_res
        
    is_trans, trans_res = evaluate_translation(query)
    if is_trans:
        return True, trans_res

    try:
        expr = translate_to_expression(query)
        if not is_math_expression(expr):
            return False, None
        
        # Replace '^' with '**' for evaluation if any remain
        expr_eval = expr.replace('^', '**')
        
        # Safe evaluation
        result = eval(expr_eval, {"__builtins__": None}, SAFE_MATH_DICT)
        
        # Format the result nicely
        if isinstance(result, float):
            if result.is_integer():
                result = int(result)
            else:
                result = round(result, 6)
                
        return True, str(result)
    except ZeroDivisionError:
        return True, "Error: Division by zero"
    except Exception:
        return False, None
