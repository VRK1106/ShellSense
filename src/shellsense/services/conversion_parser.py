import re
import urllib.request
import urllib.parse
import json
import threading
import os

# Currency rates cache relative to USD (1.0 USD = X Currency)
STATIC_CURRENCY_RATES = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "INR": 83.50,
    "JPY": 157.00,
    "CAD": 1.37,
    "AUD": 1.51,
    "CNY": 7.25,
    "SGD": 1.35,
    "CHF": 0.89,
    "AED": 3.67,
    "SAR": 3.75
}

CURRENCY_RATES = STATIC_CURRENCY_RATES.copy()
RATES_FILE = os.path.join(os.path.dirname(__file__), "currency_rates.json")

def load_cached_rates():
    global CURRENCY_RATES
    if os.path.exists(RATES_FILE):
        try:
            with open(RATES_FILE, 'r') as f:
                cached = json.load(f)
                CURRENCY_RATES.update(cached)
        except Exception:
            pass

def fetch_live_rates_async():
    def fetch():
        global CURRENCY_RATES
        try:
            # Fetch from free open-api (1.5s timeout to prevent thread blocking)
            url = "https://open.er-api.com/v6/latest/USD"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=1.5) as response:
                data = json.loads(response.read().decode())
                if data.get("result") == "success":
                    rates = data.get("rates", {})
                    # Filter and update only supported currencies
                    updated = {}
                    for code in CURRENCY_RATES.keys():
                        if code in rates:
                            updated[code] = rates[code]
                    
                    CURRENCY_RATES.update(updated)
                    # Cache to disk
                    with open(RATES_FILE, 'w') as f:
                        json.dump(updated, f)
        except Exception:
            pass

    thread = threading.Thread(target=fetch, daemon=True)
    thread.start()

# Load cached and fetch live rates asynchronously
load_cached_rates()
fetch_live_rates_async()

# Timezones relative to UTC
TIMEZONE_OFFSETS = {
    "UTC": 0.0, "GMT": 0.0,
    "EST": -5.0, "EDT": -4.0,
    "PST": -8.0, "PDT": -7.0,
    "MST": -7.0, "MDT": -6.0,
    "CST": -6.0, "CDT": -5.0,
    "IST": 5.5,
    "BST": 1.0,
    "CET": 1.0, "CEST": 2.0,
    "JST": 9.0,
    "AEST": 10.0
}

# Physical unit configurations
UNIT_CATEGORIES = {
    "length": {
        "base": "m",
        "factors": {
            "m": 1.0, "meter": 1.0, "meters": 1.0,
            "km": 1000.0, "kilometer": 1000.0, "kilometers": 1000.0,
            "cm": 0.01, "centimeter": 0.01, "centimeters": 0.01,
            "mm": 0.001, "millimeter": 0.001, "millimeters": 0.001,
            "mile": 1609.344, "miles": 1609.344, "mi": 1609.344,
            "yard": 0.9144, "yards": 0.9144, "yd": 0.9144,
            "foot": 0.3048, "feet": 0.3048, "ft": 0.3048,
            "inch": 0.0254, "inches": 0.0254, "in": 0.0254
        }
    },
    "area": {
        "base": "sq_m",
        "factors": {
            "sq_m": 1.0, "sq m": 1.0, "m2": 1.0, "m^2": 1.0, "square meter": 1.0, "square meters": 1.0,
            "sq_km": 1000000.0, "sq km": 1000000.0, "km2": 1000000.0, "km^2": 1000000.0, "square kilometer": 1000000.0, "square kilometers": 1000000.0,
            "sq_ft": 0.092903, "sq ft": 0.092903, "ft2": 0.092903, "ft^2": 0.092903, "square foot": 0.092903, "square feet": 0.092903,
            "sq_yard": 0.836127, "sq yard": 0.836127, "yard2": 0.836127, "square yard": 0.836127, "square yards": 0.836127,
            "sq_mile": 2589988.11, "sq mile": 2589988.11, "mile2": 2589988.11, "square mile": 2589988.11, "square miles": 2589988.11,
            "acre": 4046.85642, "acres": 4046.85642,
            "hectare": 10000.0, "hectares": 10000.0, "ha": 10000.0
        }
    },
    "volume": {
        "base": "l",
        "factors": {
            "l": 1.0, "liter": 1.0, "liters": 1.0, "litre": 1.0, "litres": 1.0,
            "ml": 0.001, "milliliter": 0.001, "milliliters": 0.001,
            "gal": 3.78541, "gallon": 3.78541, "gallons": 3.78541,
            "qt": 0.946353, "quart": 0.946353, "quarts": 0.946353,
            "pt": 0.473176, "pint": 0.473176, "pints": 0.473176,
            "cup": 0.236588, "cups": 0.236588,
            "fl_oz": 0.0295735, "fl oz": 0.0295735, "fluid ounce": 0.0295735, "fluid ounces": 0.0295735, "floz": 0.0295735
        }
    },
    "weight": {
        "base": "g",
        "factors": {
            "g": 1.0, "gram": 1.0, "grams": 1.0,
            "kg": 1000.0, "kilogram": 1000.0, "kilograms": 1000.0,
            "lb": 453.59237, "lbs": 453.59237, "pound": 453.59237, "pounds": 453.59237,
            "oz": 28.3495231, "ounce": 28.3495231, "ounces": 28.3495231,
            "ton": 907184.74, "tons": 907184.74
        }
    },
    "speed": {
        "base": "mps",
        "factors": {
            "m/s": 1.0, "mps": 1.0, "meter per second": 1.0, "meters per second": 1.0,
            "km/h": 0.277778, "kmh": 0.277778, "kilometer per hour": 0.277778, "kilometers per hour": 0.277778,
            "mph": 0.44704, "mile per hour": 0.44704, "miles per hour": 0.44704,
            "knot": 0.514444, "knots": 0.514444, "kt": 0.514444
        }
    },
    "pressure": {
        "base": "pa",
        "factors": {
            "pa": 1.0, "pascal": 1.0, "pascals": 1.0,
            "kpa": 1000.0, "kilopascal": 1000.0, "kilopascals": 1000.0,
            "bar": 100000.0, "bars": 100000.0,
            "psi": 6894.75729, "pound per square inch": 6894.75729, "pounds per square inch": 6894.75729,
            "atm": 101325.0, "atmosphere": 101325.0, "atmospheres": 101325.0
        }
    },
    "power": {
        "base": "w",
        "factors": {
            "w": 1.0, "watt": 1.0, "watts": 1.0,
            "kw": 1000.0, "kilowatt": 1000.0, "kilowatts": 1000.0,
            "hp": 745.699872, "horsepower": 745.699872
        }
    }
}

# Temperature mapping helper
TEMP_MAPPINGS = {
    "c": "c", "celsius": "c", "centigrade": "c", "°c": "c",
    "f": "f", "fahrenheit": "f", "°f": "f",
    "k": "k", "kelvin": "k", "°k": "k"
}

# Offline static dictionary for translations of common daily phrases/greetings
OFFLINE_TRANSLATIONS = {
    "es": {
        "hello": "hola", "hi": "hola", "good morning": "buenos días", "good afternoon": "buenas tardes",
        "good night": "buenas noches", "thank you": "gracias", "thanks": "gracias",
        "welcome": "bienvenido", "please": "por favor", "yes": "sí", "no": "no",
        "goodbye": "adiós", "bye": "adiós", "how are you": "¿cómo estás?", "sorry": "lo siento"
    },
    "fr": {
        "hello": "bonjour", "hi": "salut", "good morning": "bonjour", "good afternoon": "bon après-midi",
        "good night": "bonne nuit", "thank you": "merci", "thanks": "merci",
        "welcome": "bienvenue", "please": "s'il vous plaît", "yes": "oui", "no": "non",
        "goodbye": "au revoir", "bye": "salut", "how are you": "comment ça va?", "sorry": "désolé"
    },
    "de": {
        "hello": "hallo", "hi": "hallo", "good morning": "guten morgen", "good afternoon": "guten tag",
        "good night": "gute nacht", "thank you": "danke", "thanks": "danke",
        "welcome": "willkommen", "please": "bitte", "yes": "ja", "no": "nein",
        "goodbye": "auf wiedersehen", "bye": "tschüss", "how are you": "wie geht es dir?", "sorry": "entschuldigung"
    },
    "it": {
        "hello": "ciao", "hi": "ciao", "good morning": "buongiorno", "good afternoon": "buon pomeriggio",
        "good night": "buonanotte", "thank you": "grazie", "thanks": "grazie",
        "welcome": "benvenuto", "please": "per favore", "yes": "sì", "no": "no",
        "goodbye": "arrivederci", "bye": "ciao", "how are you": "come stai?", "sorry": "scusa"
    },
    "pt": {
        "hello": "olá", "hi": "oi", "good morning": "bom dia", "good afternoon": "boa tarde",
        "good night": "boa noite", "thank you": "obrigado", "thanks": "obrigado",
        "welcome": "bem-vindo", "please": "por favor", "yes": "sim", "no": "não",
        "goodbye": "adeus", "bye": "tchau", "how are you": "como vai?", "sorry": "desculpe"
    },
    "ja": {
        "hello": "こんにちは", "hi": "やあ", "good morning": "おはようございます", "good afternoon": "こんにちは",
        "good night": "おやすみなさい", "thank you": "ありがとう", "thanks": "どうも",
        "welcome": "ようこそ", "please": "おねがいします", "yes": "はい", "no": "いいえ",
        "goodbye": "さようなら", "bye": "じゃあね", "how are you": "お元気ですか？", "sorry": "ごめんなさい"
    },
    "zh": {
        "hello": "你好", "hi": "你好", "good morning": "早上好", "good afternoon": "下午好",
        "good night": "晚安", "thank you": "谢谢", "thanks": "谢谢",
        "welcome": "欢迎", "please": "请", "yes": "是", "no": "不",
        "goodbye": "再见", "bye": "拜拜", "how are you": "你好吗？", "sorry": "对不起"
    },
    "hi": {
        "hello": "नमस्ते", "hi": "नमस्ते", "good morning": "सुप्रभात", "good afternoon": "नमस्कार",
        "good night": "शुभ रात्रि", "thank you": "धन्यवाद", "thanks": "शुक्रिया",
        "welcome": "स्वागत", "please": "कृपया", "yes": "हाँ", "no": "नहीं",
        "goodbye": "अलविदा", "bye": "बाय", "how are you": "आप कैसे हैं?", "sorry": "माफ़ कीजिये"
    }
}

LANGUAGE_CODES = {
    "spanish": "es", "spain": "es", "es": "es",
    "french": "fr", "france": "fr", "fr": "fr",
    "german": "de", "germany": "de", "de": "de",
    "italian": "it", "italy": "it", "it": "it",
    "portuguese": "pt", "portugal": "pt", "pt": "pt",
    "japanese": "ja", "japan": "ja", "ja": "ja",
    "chinese": "zh", "china": "zh", "zh": "zh",
    "hindi": "hi", "india": "hi", "hi": "hi"
}

def evaluate_conversion(query: str):
    """
    Evaluates unit, timezone, currency, and base conversions.
    Returns (success, result_string)
    """
    q = query.lower().strip()
    q = re.sub(r'[?=\s]+$', '', q) # Strip trailing question marks/equals

    # 1. Base / Number System conversions (e.g. "hex ff to binary")
    base_match = re.match(
        r'^(decimal|dec|hex|hexadecimal|bin|binary|oct|octal|base\s*\d+)\s+([0-9a-fA-F]+)\s+(?:to|in)\s+(decimal|dec|hex|hexadecimal|bin|binary|oct|octal|base\s*\d+)',
        q
    )
    if base_match:
        src_base_str, val_str, dest_base_str = base_match.groups()
        
        # Helper to parse base value
        def get_base_int(b_str):
            b_str = b_str.replace("hexadecimal", "hex").replace("binary", "bin")
            if b_str in ["dec", "decimal"]: return 10
            if b_str == "hex": return 16
            if b_str == "bin": return 2
            if b_str in ["oct", "octal"]: return 8
            m = re.match(r'base\s*(\d+)', b_str)
            if m: return int(m.group(1))
            return None

        src_base = get_base_int(src_base_str)
        dest_base = get_base_int(dest_base_str)
        
        if src_base and dest_base:
            try:
                # Convert source string to integer
                val_int = int(val_str, src_base)
                
                # Format output base
                if dest_base == 10:
                    res = str(val_int)
                elif dest_base == 16:
                    res = hex(val_int)
                elif dest_base == 2:
                    res = bin(val_int)
                elif dest_base == 8:
                    res = oct(val_int)
                else:
                    # Generic base conversion formatting (up to base 36)
                    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
                    temp = val_int
                    digits = []
                    while temp:
                        digits.append(chars[temp % dest_base])
                        temp //= dest_base
                    res = "".join(reversed(digits)) if digits else "0"
                
                return True, f"{res} ({dest_base_str})"
            except Exception:
                return True, "Error: Invalid number for source base"

    # 2. Currency conversion (e.g. "100 usd to eur")
    curr_match = re.match(r'^(\d+(?:\.\d+)?)\s*([a-zA-Z]{3})\s+(?:to|in)\s+([a-zA-Z]{3})$', q)
    if curr_match:
        val_str, src_curr, dest_curr = curr_match.groups()
        src_curr, dest_curr = src_curr.upper(), dest_curr.upper()
        
        if src_curr in CURRENCY_RATES and dest_curr in CURRENCY_RATES:
            val = float(val_str)
            # Conversion relative to USD base
            usd_val = val / CURRENCY_RATES[src_curr]
            converted = usd_val * CURRENCY_RATES[dest_curr]
            rate = CURRENCY_RATES[dest_curr] / CURRENCY_RATES[src_curr]
            return True, f"{converted:.2f} {dest_curr} (1 {src_curr} = {rate:.4f} {dest_curr})"

    # 3. Timezone conversion (e.g. "10:30 am est to ist" or "4 pm pst to gmt" or "14 cet in gmt")
    tz_match = re.match(
        r'^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s+([a-zA-Z]{3,4})\s+(?:to|in)\s+([a-zA-Z]{3,4})$',
        q
    )
    if tz_match:
        hr_str, min_str, ampm, src_tz, dest_tz = tz_match.groups()
        src_tz, dest_tz = src_tz.upper(), dest_tz.upper()
        
        if src_tz in TIMEZONE_OFFSETS and dest_tz in TIMEZONE_OFFSETS:
            hr = int(hr_str)
            mn = int(min_str) if min_str is not None else 0
            
            # Convert to 24hr format
            if ampm:
                ampm = ampm.lower()
                if ampm == "pm" and hr < 12: hr += 12
                elif ampm == "am" and hr == 12: hr = 0
            
            # Minutes since UTC midnight for source
            total_mins = hr * 60 + mn
            # Subtract source offset to get UTC minutes
            utc_mins = total_mins - int(TIMEZONE_OFFSETS[src_tz] * 60)
            # Add target offset to get local minutes
            local_mins = utc_mins + int(TIMEZONE_OFFSETS[dest_tz] * 60)
            
            # Clamp minutes to 24hr cycle
            local_mins = local_mins % (24 * 60)
            dest_hr = int(local_mins // 60)
            dest_mn = int(local_mins % 60)
            
            # Format output in 12hr or 24hr format matching input
            if ampm:
                out_ampm = "AM"
                if dest_hr >= 12:
                    out_ampm = "PM"
                    if dest_hr > 12: dest_hr -= 12
                elif dest_hr == 0:
                    dest_hr = 12
                return True, f"{dest_hr:02d}:{dest_mn:02d} {out_ampm} {dest_tz}"
            else:
                return True, f"{dest_hr:02d}:{dest_mn:02d} {dest_tz}"

    # 4. Temperature conversions (e.g. "100 f to c", "37 celsius in kelvin")
    temp_match = re.match(
        r'^(\-?\d+(?:\.\d+)?)\s*([a-zA-Z°]+)\s+(?:to|in)\s+([a-zA-Z°]+)$',
        q
    )
    if temp_match:
        val_str, src_unit_str, dest_unit_str = temp_match.groups()
        src_unit = TEMP_MAPPINGS.get(src_unit_str)
        dest_unit = TEMP_MAPPINGS.get(dest_unit_str)
        
        if src_unit and dest_unit:
            val = float(val_str)
            # Standardize to Celsius
            if src_unit == "c": c_val = val
            elif src_unit == "f": c_val = (val - 32.0) * 5.0 / 9.0
            elif src_unit == "k": c_val = val - 273.15

            # Convert to target
            if dest_unit == "c": out_val = c_val
            elif dest_unit == "f": out_val = (c_val * 9.0 / 5.0) + 32.0
            elif dest_unit == "k": out_val = c_val + 273.15
            
            # Pretty symbols
            unit_syms = {"c": "°C", "f": "°F", "k": "K"}
            return True, f"{out_val:.2f} {unit_syms[dest_unit]}"

    # 5. General Unit Conversions (Length, Area, Volume, Weight, Speed, Pressure, Power)
    unit_match = re.match(
        r'^(\d+(?:\.\d+)?)\s*([a-zA-Z0-9\u00b2\u00b3^2^3/\s_]+?)\s+(?:to|in)\s+([a-zA-Z0-9\u00b2\u00b3^2^3/\s_]+?)$',
        q
    )
    if unit_match:
        val_str, src_unit, dest_unit = unit_match.groups()
        val = float(val_str)
        src_unit = src_unit.strip()
        dest_unit = dest_unit.strip()
        
        # Search across all categories
        for category, config in UNIT_CATEGORIES.items():
            factors = config["factors"]
            if src_unit in factors and dest_unit in factors:
                # Convert to base unit, then convert to destination unit
                base_val = val * factors[src_unit]
                converted = base_val / factors[dest_unit]
                
                # Format rounding nicely
                if converted.is_integer():
                    res_str = str(int(converted))
                else:
                    res_str = f"{converted:.4f}".rstrip('0').rstrip('.')
                
                return True, f"{res_str} {dest_unit}"

    return False, None

def evaluate_translation(query: str):
    """
    Evaluates offline-first translations by dynamically identifying target languages in the query.
    Returns (success, result_string)
    """
    q = query.lower().strip()
    q = re.sub(r'[?=\s]+$', '', q) # Strip trailing question marks/equals
    
    # 1. Identify target language
    target_lang = None
    lang_code = None
    
    # Supported full language names
    full_languages = ["spanish", "french", "german", "italian", "portuguese", "japanese", "chinese", "hindi"]
    # Supported codes (excluding 'it' to prevent false positives with English pronoun 'it')
    short_codes = ["es", "fr", "de", "pt", "ja", "zh", "hi"]
    
    # Search for full language names first
    for lang in full_languages:
        # Match as a whole word to avoid partial matches
        if re.search(r'\b' + lang + r'\b', q):
            target_lang = lang
            lang_code = LANGUAGE_CODES[lang]
            break
            
    # If not found, search for short codes or "it" with context
    if not target_lang:
        # Look for "to/in <short_code/it>" or "translate <phrase> <short_code/it>"
        for code in list(short_codes) + ["it"]:
            if re.search(r'\b(?:to|in)\s+' + code + r'\b', q):
                target_lang = code
                lang_code = LANGUAGE_CODES[code]
                break
        
        # If still not found, check if it ends with a short code (excluding 'it') and starts with 'translate'
        if not target_lang and q.startswith("translate"):
            for code in short_codes:
                if q.endswith(" " + code):
                    target_lang = code
                    lang_code = LANGUAGE_CODES[code]
                    break

    if not target_lang:
        return False, None

    # 2. Extract the phrase to translate by removing target language name/code
    phrase = re.sub(r'\b' + re.escape(target_lang) + r'\b', '', q).strip()
    
    # Clean common prefixes and suffixes
    phrase = re.sub(r'^(?:translate|translation of|how to say|what is|say)\s+', '', phrase)
    phrase = re.sub(r'\s+(?:to|in|of)$', '', phrase)
    phrase = re.sub(r'^(?:to|in|of)\s+', '', phrase)
    
    phrase = phrase.strip().strip("'\"")
    if not phrase:
        return False, None

    # Check offline dictionary first (extremely fast and lightweight for low-spec machines)
    if lang_code in OFFLINE_TRANSLATIONS:
        dict_lang = OFFLINE_TRANSLATIONS[lang_code]
        if phrase in dict_lang:
            return True, f"{dict_lang[phrase].capitalize()} ({lang_code.upper()})"
            
    # As a secondary fallback, run a fast network check if online (0.8s timeout, non-blocking)
    try:
        url_phrase = urllib.parse.quote(phrase)
        url = f"https://api.mymemory.translated.net/get?q={url_phrase}&langpair=en|{lang_code}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=0.8) as response:
            data = json.loads(response.read().decode())
            translated_text = data.get("responseData", {}).get("translatedText")
            if translated_text:
                return True, f"{translated_text} ({lang_code.upper()})"
    except Exception:
        pass
        
    # Final fallback if offline and word is not in static list
    return True, f"Error: '{phrase}' not in offline dict / network timeout"
