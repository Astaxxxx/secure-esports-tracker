def setup_security_headers(app):

    @app.after_request
    def add_security_headers(response):
 
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'"

        response.headers['X-XSS-Protection'] = '1; mode=block'

        response.headers['X-Content-Type-Options'] = 'nosniff'

        response.headers['X-Frame-Options'] = 'DENY'

        if not app.debug:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response
    
    return app