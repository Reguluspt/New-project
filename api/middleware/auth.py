from functools import wraps
from flask import request, jsonify, g, current_app
import jwt

COOKIE_NAME = "thamdinh_auth"

def login_required(f):
    """
    Decorator to protect API routes. Decodes and validates JWT token 
    from 'thamdinh_auth' cookie and assigns user info to g.current_user.
    """
    @wraps(f)
    def decorated_view(*args, **kwargs):
        token = request.cookies.get(COOKIE_NAME)
        if not token:
            return jsonify({
                "error": "Chưa đăng nhập"
            }), 401
            
        try:
            payload = jwt.decode(
                token, 
                current_app.config["SECRET_KEY"], 
                algorithms=["HS256"]
            )
            username = payload.get("sub")
            role = payload.get("role")
            
            if not username or not role:
                return jsonify({
                    "error": "Phiên đăng nhập không hợp lệ"
                }), 401
                
            # Populate flask.g object
            g.current_user = {
                "username": username,
                "role": role
            }
        except jwt.ExpiredSignatureError:
            return jsonify({
                "error": "Phiên đăng nhập đã hết hạn"
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                "error": "Phiên đăng nhập không hợp lệ"
            }), 401
            
        return f(*args, **kwargs)
    return decorated_view

def admin_required(f):
    """
    Decorator to restrict API routes to admin users only.
    Extends login_required.
    """
    @wraps(f)
    @login_required
    def decorated_view(*args, **kwargs):
        user = getattr(g, "current_user", None)
        if not user or user.get("role") != "admin":
            return jsonify({
                "error": "Bạn không có quyền thực hiện hành động này"
            }), 403
        return f(*args, **kwargs)
    return decorated_view
