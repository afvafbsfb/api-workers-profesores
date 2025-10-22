"""
Dump OpenAPI spec generated from the running Flask app to docs/openapi-auto.json and docs/openapi-auto.yml
Run with: python scripts/dump_openapi.py
"""
import json
import yaml
import os
import sys

# Ensure the project root is on sys.path so `from app import create_app` works
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from src.schemas.auth import LoginRequestSchema, LoginResponseSchema
from src.schemas.academia import AcademiaSchema
# New: register refresh request schema
from src.schemas.refresh import RefreshRequestSchema
import re

# Basic programmatic schemas for Usuario and Rol derived from models.py
from marshmallow import Schema, fields


class RolSchema(Schema):
    id = fields.Int(dump_only=True)
    nombre = fields.Str()


class UsuarioSchema(Schema):
    id = fields.Int(dump_only=True)
    academia_id = fields.Int(allow_none=True)
    nombre = fields.Str()
    email = fields.Email()
    rol = fields.Nested(RolSchema)
    estado = fields.Str()
    fecha_alta = fields.DateTime()


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
                apispec.components.schema('RefreshRequest', schema=RefreshRequestSchema)
                apispec.components.schema('Rol', schema=RolSchema)
                apispec.components.schema('Usuario', schema=UsuarioSchema)

                # Register a bearer (JWT) security scheme so Swagger UI can authorize
                apispec.components.security_scheme('bearerAuth', {
                    'type': 'http',
                    'scheme': 'bearer',
                    'bearerFormat': 'JWT',
                })

                # Add POST /auth/login (explicit so requestBody is preserved)
                # Ensure operationId matches the decorator used in the route source (login.login)
                apispec.path(path='/auth/login', operations={
                    'post': {
                        'summary': 'Login usuario',
                        'description': 'Inicio de sesión con email y password',
                        'tags': ['login'],
                        'operationId': 'login.login',
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
                # Heuristic: iterate registered Flask routes and generate minimal operations
                # Translate Flask rules like '/usuarios/<int:id>' -> '/usuarios/{id}'
                def flask_rule_to_openapi_path(rule):
                    # Replace Flask variable patterns <converter:name> or <name> with {name}
                    return re.sub(r"<(?:(?:[^:>]+):)?([^>]+)>", r"{\1}", rule)

                # Paths that should be public / not require authentication
                PUBLIC_PREFIXES = (
                    '/static',
                    '/docs',
                    '/openapi',
                    '/auth/login',
                    '/health',
                )

                # Tag descriptions (can be extended)
                TAG_DESCRIPTIONS = {
                    'login': 'Inicio de sesión (email/password).',
                    'jwt': 'Refresh, logout y gestión de tokens JWT.',
                    'Usuarios': 'Gestión de usuarios, perfiles y credenciales.',
                    'Academias': 'Operaciones relacionadas con academias y su configuración.',
                    'Cursos': 'Gestión de cursos, horarios e inscripciones.',
                    'Alumnos': 'Operaciones sobre alumnos y sus inscripciones.',
                    'Admin': 'Operaciones administrativas de la plataforma.',
                    'Docs/Health': 'Documentación y endpoints de salud.',
                    'Default': 'Otros endpoints sin clasificación específica.',
                }

                tags_found = set()

                def choose_tag(path, endpoint):
                    # Explicit mappings for blueprints or exact paths
                    bp_map = {
                        # Blueprint 'login_bp' contains multiple auth endpoints; treat them as jwt
                        'login_bp': 'jwt',
                        'auth': 'jwt',
                        'usuarios': 'Usuarios',
                        'academias': 'Academias',
                        'cursos': 'Cursos',
                        'alumnos': 'Alumnos',
                        'docs': 'Docs/Health',
                    }

                    # Exact path overrides: /auth/login -> 'login'
                    try:
                        if path == '/auth/login':
                            tags_found.add('login')
                            return 'login'
                    except Exception:
                        pass

                    # Prefer blueprint name from endpoint (format 'blueprint.endpoint_func')
                    try:
                        if isinstance(endpoint, str) and '.' in endpoint:
                            bp = endpoint.split('.', 1)[0].lower()
                            mapped = bp_map.get(bp)
                            if mapped:
                                tags_found.add(mapped)
                                return mapped
                            # normalize generic blueprint name (capitalize)
                            tag = bp.capitalize()
                            tags_found.add(tag)
                            return tag
                    except Exception:
                        pass

                    # Map common prefixes to tags
                    try:
                        # /auth/* except /auth/login -> jwt
                        if path.startswith('/auth'):
                            # already handled /auth/login above
                            tags_found.add('jwt')
                            return 'jwt'
                        if path.startswith('/login'):
                            tags_found.add('login')
                            return 'login'
                        if path.startswith('/usuarios'):
                            tags_found.add('Usuarios')
                            return 'Usuarios'
                        if path.startswith('/academias'):
                            tags_found.add('Academias')
                            return 'Academias'
                        if path.startswith('/cursos'):
                            tags_found.add('Cursos')
                            return 'Cursos'
                        if path.startswith('/alumnos'):
                            tags_found.add('Alumnos')
                            return 'Alumnos'
                        if path in ('/openapi.json', '/openapi.yml') or path.startswith('/docs') or path.startswith('/health'):
                            tags_found.add('Docs/Health')
                            return 'Docs/Health'
                    except Exception:
                        pass

                    # Fallback: take first path segment
                    try:
                        parts = [p for p in path.split('/') if p]
                        if parts:
                            tag = parts[0].capitalize()
                            tags_found.add(tag)
                            return tag
                    except Exception:
                        pass

                    tags_found.add('Default')
                    return 'Default'

                for rule in app.url_map.iter_rules():
                    # Skip static and internal endpoints
                    if rule.endpoint == 'static' or rule.rule.startswith('/static'):
                        continue

                    path = flask_rule_to_openapi_path(rule.rule)
                    # If we already added a detailed entry for /auth/login above, skip it here
                    if path == '/auth/login':
                        continue
                    operations = {}
                    methods = [m for m in rule.methods if m in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE')]
                    view_fn = app.view_functions.get(rule.endpoint)

                    for m in methods:
                        op = {
                            'summary': f'{m} {path}',
                            'description': f'Auto-generated operation for {rule.endpoint}',
                            'responses': {
                                '200': {'description': 'Successful response'},
                                '401': {'description': 'Unauthorized'},
                                '403': {'description': 'Forbidden'},
                            }
                        }

                        # Attempt to set a deterministic operationId:
                        # 1) If the view function has an explicit 'operation_id' attribute (set via decorator), use it.
                        # 2) Else derive from rule.endpoint which is usually 'blueprint.func' or 'module.func'.
                        try:
                            op_id = None
                            # prefer attribute on the original view function
                            if view_fn is not None:
                                op_id = getattr(view_fn, 'operation_id', None)
                                if not op_id:
                                    wrapped = getattr(view_fn, '__wrapped__', None)
                                    op_id = getattr(wrapped, 'operation_id', None) if wrapped is not None else None

                            # If op_id is a dict mapping methods -> id, pick the one for this method
                            if isinstance(op_id, dict):
                                try:
                                    op_method_key = m.lower()
                                    chosen = op_id.get(op_method_key)
                                    if chosen:
                                        op['operationId'] = chosen
                                        op_id = chosen
                                    else:
                                        # no explicit mapping for this method; fallthrough to derive
                                        op_id = None
                                except Exception:
                                    op_id = None

                            if not op_id and isinstance(rule.endpoint, str):
                                # rule.endpoint often has format 'blueprint.endpoint'; normalize to blueprint.endpoint
                                ep = rule.endpoint
                                # sanitize: lowercase and replace invalid chars with '_'
                                ep_clean = re.sub(r'[^A-Za-z0-9_.]', '_', ep)
                                op_id = ep_clean.lower()
                                op['operationId'] = op_id
                            elif op_id and not isinstance(op_id, dict):
                                # if op_id is a string, use it
                                op['operationId'] = op_id
                        except Exception:
                            # best-effort: do not prevent spec generation
                            pass

                        # Determine if this path is public (no auth) by prefix or exact match
                        is_public = False
                        try:
                            for p in PUBLIC_PREFIXES:
                                if path == p or path.startswith(p):
                                    is_public = True
                                    break
                        except Exception:
                            is_public = False

                        # If view function explicitly marks auth requirement, respect it
                        try:
                            view_requires = getattr(view_fn, '_requires_auth', False) or (
                                getattr(view_fn, '__wrapped__', None) and getattr(view_fn.__wrapped__, '_requires_auth', False)
                            )
                        except Exception:
                            view_requires = False

                        # Security policy: public paths -> no security. Otherwise, if view declares it
                        # requires auth, or by default (most endpoints require auth), add bearerAuth.
                        if not is_public:
                            if view_requires:
                                op['security'] = [{ 'bearerAuth': [] }]
                            else:
                                # Default to requiring auth for non-public endpoints
                                op['security'] = [{ 'bearerAuth': [] }]

                        # Assign a tag to the operation based on blueprint, path or prefix
                        try:
                            tag = choose_tag(path, rule.endpoint)
                            op['tags'] = [tag]
                        except Exception:
                            pass

                        # Add path parameters if any {param} present
                        path_params = re.findall(r"\{([^}]+)\}", path)
                        if path_params:
                            params = []
                            for p in path_params:
                                # Heuristic: treat anything containing 'id' as integer
                                p_type = 'integer' if 'id' in p.lower() else 'string'
                                params.append({
                                    'name': p,
                                    'in': 'path',
                                    'required': True,
                                    'schema': {'type': p_type}
                                })
                            op['parameters'] = params

                        # Add query parameters if view function exposes them via attribute
                        try:
                            qargs = None
                            if view_fn is not None:
                                qargs = getattr(view_fn, 'openapi_query_args', None)
                                if not qargs:
                                    wrapped = getattr(view_fn, '__wrapped__', None)
                                    qargs = getattr(wrapped, 'openapi_query_args', None) if wrapped is not None else None

                            if qargs:
                                params = op.get('parameters', []) or []
                                # qargs may be a mapping name->field or name->dict
                                for qname, qfield in (qargs.items() if isinstance(qargs, dict) else []):
                                    schema = {}
                                    # If it's a marshmallow Field instance, map basic types
                                    try:
                                        from marshmallow import fields as mfields
                                        if isinstance(qfield, mfields.Integer) or qfield.__class__.__name__.lower().startswith('int'):
                                            schema['type'] = 'integer'
                                        elif isinstance(qfield, mfields.String) or qfield.__class__.__name__.lower().startswith('str'):
                                            schema['type'] = 'string'
                                        elif isinstance(qfield, mfields.Boolean) or qfield.__class__.__name__.lower().startswith('bool'):
                                            schema['type'] = 'boolean'
                                        else:
                                            # default to string
                                            schema['type'] = 'string'
                                    except Exception:
                                        # If qfield is a simple dict with 'type'
                                        if isinstance(qfield, dict) and 'type' in qfield:
                                            schema['type'] = qfield['type']
                                        else:
                                            schema['type'] = 'string'

                                    # If the query parameter is `page` or `size`, inject pagination
                                    # metadata (defaults/min/max) so the generated OpenAPI shows limits.
                                    try:
                                        # import here to avoid import-time side-effects of project packages
                                        from src.shared.pagination import DEFAULT_PAGE, DEFAULT_SIZE, MAX_PAGE_SIZE
                                        if qname == 'page':
                                            schema.setdefault('type', 'integer')
                                            schema.setdefault('minimum', 1)
                                            schema.setdefault('default', DEFAULT_PAGE)
                                        if qname == 'size':
                                            schema.setdefault('type', 'integer')
                                            schema.setdefault('minimum', 1)
                                            schema.setdefault('default', DEFAULT_SIZE)
                                            schema.setdefault('maximum', MAX_PAGE_SIZE)
                                    except Exception:
                                        # best-effort: if import fails, continue without pagination metadata
                                        pass

                                    params.append({
                                        'name': qname,
                                        'in': 'query',
                                        'required': False,
                                        'schema': schema
                                    })
                                op['parameters'] = params
                        except Exception:
                            pass

                        # Add requestBody heuristics for certain resources
                        if m.lower() in ('post', 'put', 'patch'):
                            # If the view function explicitly declares a request body schema via
                            # the openapi_request_body attribute, emit that as requestBody.
                            try:
                                body_schema = None
                                if view_fn is not None:
                                    body_schema = getattr(view_fn, 'openapi_request_body', None)
                                    if not body_schema:
                                        wrapped = getattr(view_fn, '__wrapped__', None)
                                        body_schema = getattr(wrapped, 'openapi_request_body', None) if wrapped is not None else None

                                if body_schema:
                                    # body_schema may be a string name of the component schema
                                    schema_ref = body_schema if isinstance(body_schema, str) else str(body_schema)
                                    op['requestBody'] = {
                                        'content': {
                                            'application/json': {
                                                'schema': {'$ref': f"#/components/schemas/{schema_ref}"}
                                            }
                                        },
                                        'required': True
                                    }
                                else:
                                    if path.startswith('/usuarios'):
                                        # Use Usuario schema as request/response body for create/update (simple heuristic)
                                        op['requestBody'] = {
                                            'content': {
                                                'application/json': {
                                                    'schema': {'$ref': '#/components/schemas/Usuario'}
                                                }
                                            },
                                            'required': True
                                        }
                                    elif path.startswith('/academias') and m.lower() in ('post', 'patch', 'put'):
                                        op['requestBody'] = {
                                            'content': {
                                                'application/json': {
                                                    'schema': {'$ref': '#/components/schemas/Academia'}
                                                }
                                            },
                                            'required': True
                                        }
                            except Exception:
                                # fall back to previous heuristics if anything goes wrong
                                pass

                        operations[m.lower()] = op

                    # Only add path if we found any operations
                    if operations:
                        # If this is the /usuarios/me path, attach a response schema for 200
                        if path == '/usuarios/me' and 'get' in operations:
                            operations['get']['responses'] = {
                                '200': {
                                    'description': 'Perfil del usuario autenticado',
                                    'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Usuario'}}}
                                },
                                '401': {'description': 'Unauthorized'},
                                '403': {'description': 'Forbidden'},
                            }
                        apispec.path(path=path, operations=operations)

                # Register tags metadata in the spec
                try:
                    # Preferred ordering: login first, jwt second, Docs/Health last
                    preferred = []
                    if 'login' in tags_found:
                        preferred.append('login')
                    if 'jwt' in tags_found:
                        preferred.append('jwt')

                    # Middle tags: everything except preferred/start/end
                    middle = sorted([t for t in tags_found if t not in preferred and t != 'Docs/Health'])

                    # End tag
                    end = []
                    if 'Docs/Health' in tags_found:
                        end.append('Docs/Health')

                    ordered = preferred + middle + end

                    # Ensure uniqueness while preserving order (avoid repeated apispec.tag calls)
                    seen = set()
                    unique_ordered = []
                    for t in ordered:
                        if t not in seen:
                            seen.add(t)
                            unique_ordered.append(t)

                    for t in unique_ordered:
                        desc = TAG_DESCRIPTIONS.get(t, '')
                        try:
                            apispec.tag({'name': t, 'description': desc})
                        except Exception:
                            pass
                except Exception:
                    pass

                spec = apispec.to_dict()

                # --- Post-process: ensure PaginatedEnvelope schema and /usuarios/export path ---
                try:
                    auto_path = os.path.join(ROOT, 'docs', 'openapi-auto.json')
                    if os.path.exists(auto_path):
                        with open(auto_path, 'r', encoding='utf-8') as f:
                            auto_spec = json.load(f)

                        # Ensure components.schemas.PaginatedEnvelope
                        comps = auto_spec.setdefault('components', {}).setdefault('schemas', {})
                        comps.setdefault('PaginatedEnvelope', {
                            'type': 'object',
                            'properties': {
                                'items': {'type': 'array', 'items': {'type': 'object'}},
                                'page': {'type': 'integer'},
                                'size': {'type': 'integer'},
                                'returned': {'type': 'integer'},
                                'has_more': {'type': 'boolean'},
                                'next_page': {'type': ['integer', 'null']},
                                'prev_page': {'type': ['integer', 'null']},
                                'total': {'type': ['integer', 'null']},
                                'meta': {'type': ['object', 'null']},
                            }
                        })

                        paths = auto_spec.setdefault('paths', {})
                        # Try to copy x-permissions from /usuarios get if present
                        x_perms = None
                        usuario_entry = paths.get('/usuarios') or paths.get('/usuarios/')
                        if usuario_entry and isinstance(usuario_entry, dict):
                            get_op = usuario_entry.get('get')
                            if get_op and isinstance(get_op, dict):
                                x_perms = get_op.get('x-permissions')

                        # Add /usuarios/export if missing
                        if '/usuarios/export' not in paths:
                            paths['/usuarios/export'] = {
                                'get': {
                                    'summary': 'GET /usuarios/export',
                                    'description': 'Exportar usuarios (CSV/XLSX)',
                                    'operationId': 'usuarios.exportar_usuarios',
                                    'parameters': [
                                        {'name': 'format', 'in': 'query', 'schema': {'type': 'string', 'enum': ['csv', 'xlsx']}, 'description': 'Formato de export'},
                                        {'name': 'academia_id', 'in': 'query', 'schema': {'type': 'integer'}, 'description': 'Filtrar por academia_id'},
                                        {'name': 'rol', 'in': 'query', 'schema': {'type': 'string'}, 'description': 'Filtrar por rol'},
                                        {'name': 'nombre', 'in': 'query', 'schema': {'type': 'string'}, 'description': 'Buscar por parte del nombre (ilike)'},
                                    ],
                                    'responses': {
                                        '200': {'description': 'File attachment or stream'},
                                        '202': {'description': 'Export accepted and processing (async)'}
                                    },
                                    'security': [{'bearerAuth': []}],
                                }
                            }
                            if x_perms:
                                paths['/usuarios/export']['get']['x-permissions'] = x_perms

                        # Persist modified auto_spec so downstream pipeline picks it up
                        with open(auto_path, 'w', encoding='utf-8') as f:
                            json.dump(auto_spec, f, indent=2, ensure_ascii=False)

                        # Merge into generated spec in memory so final output includes changes
                        spec.setdefault('components', {}).setdefault('schemas', {}).update(comps)
                        spec.setdefault('paths', {}).update(paths)
                except Exception:
                    # best-effort; do not abort dump if postprocess fails
                    pass

                # Post-process tags: ensure ordering and uniqueness
                try:
                    if isinstance(spec, dict):
                        # Gather tag descriptions from existing top-level tags (if any)
                        existing = spec.get('tags', []) if isinstance(spec.get('tags', []), list) else []
                        tag_map = {}
                        for t in existing:
                            if isinstance(t, dict) and 'name' in t:
                                tag_map[t['name']] = t.get('description', '')

                        # Also collect tags used in paths/operations (ensure we don't miss ones set only at operation level)
                        paths = spec.get('paths', {}) if isinstance(spec.get('paths', {}), dict) else {}
                        for path_item in paths.values():
                            if isinstance(path_item, dict):
                                for op in path_item.values():
                                    if isinstance(op, dict):
                                        for tn in op.get('tags', []):
                                            if tn not in tag_map:
                                                # Try TAG_DESCRIPTIONS fallback
                                                tag_map[tn] = TAG_DESCRIPTIONS.get(tn, '')

                        ordered_names = []
                        # Preferred start
                        for name in ('login', 'jwt'):
                            if name in tag_map and name not in ordered_names:
                                ordered_names.append(name)

                        # Middle: sorted other tags (exclude Docs/Health)
                        middle = [n for n in sorted(tag_map.keys()) if n not in ordered_names and n != 'Docs/Health']
                        ordered_names.extend(middle)

                        # End: Docs/Health if present
                        if 'Docs/Health' in tag_map and 'Docs/Health' not in ordered_names:
                            ordered_names.append('Docs/Health')

                        # Build new tags list preserving descriptions
                        new_tags = [{'name': n, 'description': tag_map.get(n, '')} for n in ordered_names]
                        spec['tags'] = new_tags
                except Exception:
                    pass
            except Exception as e:
                print('Could not build apispec programmatically:', e)
                spec = {}

        os.makedirs('docs', exist_ok=True)
        with open('docs/openapi-auto.json', 'w', encoding='utf-8') as f:
            # Sort keys to make output deterministic between runs/environments
            json.dump(spec, f, indent=2, ensure_ascii=False, sort_keys=True)
        with open('docs/openapi-auto.yml', 'w', encoding='utf-8') as f:
            # PyYAML sort_keys=True makes YAML keys deterministic (PyYAML >=5.1)
            yaml.safe_dump(spec, f, allow_unicode=True, sort_keys=True)
        print('Wrote docs/openapi-auto.json and docs/openapi-auto.yml')


if __name__ == '__main__':
    dump()
