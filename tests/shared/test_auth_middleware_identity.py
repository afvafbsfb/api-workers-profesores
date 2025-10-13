import pytest
import os
import jwt
import json
from src.shared.middleware import auth

# Helper to create HS256 token
def make_token(payload, secret):
    return jwt.encode(payload, secret, algorithm='HS256')

@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    monkeypatch.setenv('JWT_SECRET_KEY', 'primary-secret-0123456789012345')
    monkeypatch.setenv('JWT_DELEGATION_SECRET', 'deleg-secret-012345678901234')
    # ensure debug true for clearer logs
    from config import Config
    monkeypatch.setattr(Config, 'DEBUG', True)


def test_delegated_token_with_json_sub():
    secret = os.getenv('JWT_DELEGATION_SECRET')
    sub = json.dumps({'usuario_id': 123, 'token_version': 5})
    payload = {'sub': sub, 'actor': 'chat-backend', 'token_version': 5}
    token = make_token(payload, secret)
    # call helper directly
    identity = auth.build_identity_from_payload(payload, True)
    assert identity['usuario_id'] == 123
    assert identity['token_version'] == 5


def test_delegated_token_with_numeric_sub():
    secret = os.getenv('JWT_DELEGATION_SECRET')
    payload = {'sub': '456', 'actor': 'chat-backend', 'token_version': 2}
    token = make_token(payload, secret)
    identity = auth.build_identity_from_payload(payload, True)
    assert identity['usuario_id'] == 456
    assert identity['token_version'] == 2


def test_primary_token_requires_json_sub():
    primary = os.getenv('JWT_SECRET_KEY')
    payload = {'sub': json.dumps({'usuario_id': 77, 'token_version': 3}), 'token_version': 3}
    token = make_token(payload, primary)
    identity = auth.build_identity_from_payload(payload, False)
    assert identity['usuario_id'] == 77
    assert identity['token_version'] == 3


def test_delegated_numeric_sub_without_token_version():
    delegated = os.getenv('JWT_DELEGATION_SECRET')
    payload = {'sub': '999', 'actor': 'chat-backend'}
    token = make_token(payload, delegated)
    identity = auth.build_identity_from_payload(payload, True)
    assert identity['usuario_id'] == 999
    assert identity['token_version'] is None
