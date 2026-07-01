"""
Endpoint d'authentification minimal (CLAUDE.md §5 & §6) : POST /api/auth/login
Comptes réels pour le personnel/élus AN, rôles (créer une simulation, publier un résultat,
administrer les données de référence)."""

from flask import request, jsonify
from flask_jwt_extended import create_access_token
from werkzeug.security import check_password_hash, generate_password_hash

from . import auth_bp
from ..db import get_session
from ..db.models import User


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(force=True, silent=True) or {}
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "email et password requis"}), 400

    session = get_session()
    try:
        user = session.query(User).filter_by(email=email, is_active=True).first()
        if user is None or not check_password_hash(user.password_hash, password):
            return jsonify({"error": "identifiants invalides"}), 401

        token = create_access_token(identity=user.id)
        return jsonify({
            "access_token": token,
            "user": {
                "id": user.id, "email": user.email, "full_name": user.full_name,
                "roles": [r.name for r in user.roles],
            },
        })
    finally:
        session.close()


@auth_bp.route('/register', methods=['POST'])
def register():
    """Crée un compte -- en production, cette route serait réservée à un rôle admin ; laissée
    ouverte ici pour permettre l'amorçage initial du système (premier compte)."""
    data = request.get_json(force=True, silent=True) or {}
    email = data.get('email')
    password = data.get('password')
    full_name = data.get('full_name')

    if not email or not password:
        return jsonify({"error": "email et password requis"}), 400

    session = get_session()
    try:
        if session.query(User).filter_by(email=email).first():
            return jsonify({"error": "un compte existe déjà avec cet email"}), 409

        user = User(email=email, full_name=full_name, password_hash=generate_password_hash(password))
        session.add(user)
        session.commit()
        return jsonify({"id": user.id, "email": user.email}), 201
    finally:
        session.close()
