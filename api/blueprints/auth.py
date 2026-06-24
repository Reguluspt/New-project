from flask import Blueprint, request, jsonify, make_response, current_app
import jwt
import datetime
import os
from src.auth import authenticate, _configured_guest_credentials

auth_bp = Blueprint("auth", __name__)

COOKIE_NAME = "thamdinh_auth"
COOKIE_MAX_AGE = 30 * 24 * 60 * 60
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() in ("1", "true", "yes")

def get_user_role(username: str) -> str:
    guest_username, _ = _configured_guest_credentials()
    if username == guest_username:
        return "guest"
    return "admin"

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    
    if not username or not password:
        return jsonify({"error": "Tên tài khoản hoặc mật khẩu không đúng"}), 401
        
    if authenticate(username, password):
        role = get_user_role(username)
        
        # JWT payload: { "sub": username, "role": role, "exp": now + 30 days }
        payload = {
            "sub": username,
            "role": role,
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
        }
        token = jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")
        
        response = make_response(jsonify({
            "user": {
                "username": username,
                "role": role
            }
        }))
        
        response.set_cookie(
            COOKIE_NAME,
            token,
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="Lax",
            secure=COOKIE_SECURE
        )
        return response

    return jsonify({"error": "Tên tài khoản hoặc mật khẩu không đúng"}), 401

@auth_bp.route("/logout", methods=["POST"])
def logout():
    response = make_response(jsonify({"message": "Đã đăng xuất"}))
    response.set_cookie(
        COOKIE_NAME,
        "",
        expires=0,
        httponly=True,
        samesite="Lax",
        secure=COOKIE_SECURE
    )
    return response

@auth_bp.route("/me", methods=["GET"])
def me():
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return jsonify({"error": "Chưa đăng nhập"}), 401
        
    try:
        payload = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
        username = payload.get("sub")
        role = payload.get("role")
        if not username or not role:
            return jsonify({"error": "Phiên đăng nhập không hợp lệ"}), 401
            
        return jsonify({
            "user": {
                "username": username,
                "role": role
            }
        })
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Phiên đăng nhập đã hết hạn"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Phiên đăng nhập không hợp lệ"}), 401
