"""
Security middleware to add necessary security headers to all Flask responses
"""

def setup_security_headers(app):
    """
    Configure security headers for Flask application
    
    This adds essential security headers to every response to protect against:
    - Clickjacking (X-Frame-Options)
    - XSS attacks (Content-Security-Policy)
    - MIME type sniffing (X-Content-Type-Options)
    - Information disclosure (Server, X-Powered-By)
    """
    @app.after_request
    def add_security_headers(response):
        # Prevent clickjacking attacks
        response.headers['X-Frame-Options'] = 'DENY'
        
        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Disable browser caching for sensitive pages
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        # Cross-Origin Resource Sharing (CORS) configuration
        # More restrictive CORS policy instead of wildcard
        response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Client-ID, X-Request-Signature'
        
        # Content Security Policy to prevent XSS attacks
        # Strict policy that only allows resources from same origin
        csp_directives = [
            "default-src 'self'",
            "img-src 'self' data:",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline'",  # Allowing inline styles for dashboard UI
            "font-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'"
        ]
        response.headers['Content-Security-Policy'] = "; ".join(csp_directives)
        
        # Remove server information headers
        response.headers.pop('Server', None)
        response.headers.pop('X-Powered-By', None)
        
        return response
    
    return app