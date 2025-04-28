import re
import html
import os

def sanitize_input(data):
    """Sanitize user input to prevent injection attacks"""
    if isinstance(data, str):
        # Basic sanitization for strings
        return html.escape(data)
    elif isinstance(data, dict):
        # Recursively sanitize dictionary values
        return {k: sanitize_input(v) for k, v in data.items()}
    elif isinstance(data, list):
        # Recursively sanitize list items
        return [sanitize_input(i) for i in data]
    else:
        return data

def sanitize_filename(filename):
    """Sanitize filename to prevent path traversal attacks"""
    # Remove path components and allow only alphanumeric chars, dash, underscore, and dot
    return re.sub(r'[^a-zA-Z0-9_.-]', '', os.path.basename(filename))

def is_safe_path(base_dir, path):
    """Validate that a path is within a safe directory"""
    # Get absolute paths
    base_dir = os.path.abspath(base_dir)
    path = os.path.abspath(path)
    
    # Check if path is within base_dir
    return os.path.commonpath([base_dir, path]) == base_dir

def sanitize_url(url):
    """Sanitize URL to prevent open redirect and injection attacks"""
    # Whitelist of allowed protocols
    allowed_protocols = ['http:', 'https:']
    
    # Try to parse URL
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        # Check if scheme is allowed
        if parsed.scheme and parsed.scheme not in allowed_protocols:
            return '#'
            
        return url
    except:
        # If parsing fails, return safe default
        return '#'