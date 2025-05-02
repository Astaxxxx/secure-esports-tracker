import re
import html

def sanitize_input(data):
    if not data:
        return {}
        
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            clean_key = sanitize_string(key) if isinstance(key, str) else key
            if isinstance(value, dict):
                clean_value = sanitize_input(value)
            elif isinstance(value, list):
                clean_value = [sanitize_input(item) if isinstance(item, dict) else
                              sanitize_string(item) if isinstance(item, str) else item
                              for item in value]
            elif isinstance(value, str):
                clean_value = sanitize_string(value)
            else:
                clean_value = value
            sanitized[clean_key] = clean_value
        return sanitized
    else:
        return data

def sanitize_string(value):
    if not isinstance(value, str):
        return value
    
    clean_value = html.escape(value)
  
    clean_value = re.sub(r'<script.*?>.*?</script>', '', clean_value, flags=re.DOTALL | re.IGNORECASE)
    
    return clean_value

def is_safe_path(path):
    if not path:
        return False
    if '..' in path or '//' in path or '\\\\' in path:
        return False
    return bool(re.match(r'^[a-zA-Z0-9\-_\/\\]+$', path))