import json
import os
import pytest


def test_logout_request_body_in_openapi():
    """Prueba: docs/openapi-auto.json POST /auth/logout -> requestBody -> refresh_token.
    """
    # locate project root and open generated spec
    tests_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(tests_dir, '..'))
    spec_path = os.path.join(project_root, 'docs', 'openapi-auto.json')

    assert os.path.exists(spec_path), f'OpenAPI file not found: {spec_path}'

    with open(spec_path, 'r', encoding='utf-8') as fh:
        spec = json.load(fh)

    paths = spec.get('paths', {})
    assert '/auth/logout' in paths, '/auth/logout not present in OpenAPI paths'

    logout_ops = paths['/auth/logout']
    # prefer explicit POST operation
    assert 'post' in logout_ops, 'POST operation for /auth/logout not documented'
    post_op = logout_ops['post']

    assert 'requestBody' in post_op, 'requestBody missing for POST /auth/logout'
    rb = post_op['requestBody']
    assert isinstance(rb, dict)
    content = rb.get('content', {})
    assert 'application/json' in content, 'application/json not present in requestBody content'
    schema = content['application/json'].get('schema', {})
    assert '$ref' in schema, 'schema.$ref missing for /auth/logout requestBody'
    assert schema['$ref'] == '#/components/schemas/RefreshRequest', f"Unexpected $ref: {schema.get('$ref')}"

    # Check components.schemas.RefreshRequest exists and has refresh_token property
    components = spec.get('components', {})
    schemas = components.get('schemas', {})
    assert 'RefreshRequest' in schemas, 'RefreshRequest schema not registered in components'
    rr = schemas['RefreshRequest']
    props = rr.get('properties', {})
    assert 'refresh_token' in props, 'refresh_token property missing in RefreshRequest schema'
