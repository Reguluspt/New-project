from flask import jsonify

def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({
            "status": "error",
            "code": 400,
            "error": "Bad Request",
            "message": str(getattr(e, 'description', e))
        }), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({
            "status": "error",
            "code": 401,
            "error": "Unauthorized",
            "message": str(getattr(e, 'description', e))
        }), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({
            "status": "error",
            "code": 403,
            "error": "Forbidden",
            "message": str(getattr(e, 'description', e))
        }), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            "status": "error",
            "code": 404,
            "error": "Not Found",
            "message": str(getattr(e, 'description', e))
        }), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({
            "status": "error",
            "code": 500,
            "error": "Internal Server Error",
            "message": "An unexpected error occurred on the server."
        }), 500
