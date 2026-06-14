import re
import math

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

def evaluate_math(query: str):
    """
    Translates and evaluates a math query safely.
    Returns (success, result_or_error_msg)
    """
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
