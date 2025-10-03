"""
Dump OpenAPI spec generated from the running Flask app to docs/openapi-auto.json and docs/openapi-auto.yml
Run with: python scripts/dump_openapi.py
"""
import json
import yaml
import os

from app import create_app
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from src.schemas.auth import LoginRequestSchema, LoginResponseSchema
from src.schemas.academia import AcademiaSchema


def dump():
    app = create_app()
    with app.app_context():
        # Try to obtain the apispec extension (flask-smorest)
        ext = app.extensions.get('apispec') if hasattr(app, 'extensions') else None
        if ext:
            spec = ext.spec.to_dict()
        else:
            # Build a minimal APISpec using apispec + marshmallow for two endpoints
            spec = None
            try:
                apispec = APISpec(
                    title="API Workers Profesores",
                    version="1.0.0",
                    openapi_version="3.0.2",
                    info={"description": "Spec generated from code (partial)"},
                    plugins=[MarshmallowPlugin()],
                )

                # Register schemas
                apispec.components.schema('LoginRequest', schema=LoginRequestSchema)
                apispec.components.schema('LoginResponse', schema=LoginResponseSchema)
                apispec.components.schema('Academia', schema=AcademiaSchema)

                # Register a bearer (JWT) security scheme so Swagger UI can authorize
                apispec.components.security_scheme('bearerAuth', {
                    'type': 'http',
                    'scheme': 'bearer',
                    'bearerFormat': 'JWT',
                })

                # Add POST /auth/login
                apispec.path(path='/auth/login', operations={
                    'post': {
                        'summary': 'Login usuario',
                        'description': 'Inicio de sesión con email y password',
                        'requestBody': {
                            'content': {
                                'application/json': {'schema': {'$ref': '#/components/schemas/LoginRequest'}}
                            },
                            'required': True,
                        },
                        'responses': {
                            '200': {
                                'description': 'Login exitoso',
                                'content': {'application/json': {'schema': {'$ref': '#/components/schemas/LoginResponse'}}},
                            },
                            '401': {'description': 'Credenciales inválidas'},
                        },
                    }
                })

                # Add GET /academias
                apispec.path(path='/academias', operations={
                    'get': {
                        'summary': 'Listar academias',
                        'description': 'Obtener lista de academias',
                        'security': [{ 'bearerAuth': [] }],
                        'responses': {
                            '200': {
                                'description': 'Lista de academias',
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'array',
                                            'items': {'$ref': '#/components/schemas/Academia'},
                                        }
                                    }
                                },
                            }
                        }
                    }
                })

                spec = apispec.to_dict()
            except Exception as e:
                print('Could not build apispec programmatically:', e)
                spec = {}

        os.makedirs('docs', exist_ok=True)
        with open('docs/openapi-auto.json', 'w', encoding='utf-8') as f:
            json.dump(spec, f, indent=2, ensure_ascii=False)
        with open('docs/openapi-auto.yml', 'w', encoding='utf-8') as f:
            yaml.safe_dump(spec, f, allow_unicode=True)
        print('Wrote docs/openapi-auto.json and docs/openapi-auto.yml')


if __name__ == '__main__':
    dump()
