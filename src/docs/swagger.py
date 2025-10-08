from flask import Blueprint, current_app, send_from_directory, jsonify
import os

swagger_bp = Blueprint('docs', __name__)


@swagger_bp.route('/openapi.json')
def openapi_json():
    """Return the generated OpenAPI JSON from the app if available.
    If flask-smorest is not installed or the app doesn't expose the spec,
    try to serve a pre-generated `docs/openapi-auto.json` file.
    """
    # If the app has apispec or openapi generation available, attempt to use it
    try:
        # flask-smorest exposes spec via current_app.extensions['apispec']
        ext = current_app.extensions.get('apispec')
        if ext:
            spec = ext.spec.to_dict()
            return jsonify(spec)
    except Exception:
        pass

    # Fallback to serve generated file
    generated = os.path.join(current_app.root_path, 'docs', 'openapi-auto.json')
    if os.path.exists(generated):
        return send_from_directory(os.path.dirname(generated), os.path.basename(generated))
    return jsonify({}), 404


@swagger_bp.route('/docs')
def docs_ui():
    """Serve a minimal Swagger UI page that points to `/openapi.json`.
    Uses the official CDN for Swagger UI assets.
    """
    # If the repository provides a pre-built docs/index.html prefer it; otherwise
    # fall back to the embedded swagger-ui that points to /openapi.json
    try:
        from flask import current_app
        candidate = current_app.open_instance_path and None
    except Exception:
        candidate = None

    # Try serving docs/index.html if present in the project docs folder
    import os
    project_docs_index = os.path.join(os.path.dirname(__file__), '..', '..', 'docs', 'index.html')
    project_docs_index = os.path.normpath(project_docs_index)
    if os.path.exists(project_docs_index):
        return send_from_directory(os.path.dirname(project_docs_index), os.path.basename(project_docs_index), mimetype='text/html')

    # Otherwise serve a lightweight Swagger UI page that loads /openapi.json
    html = """
    <!DOCTYPE html>
    <html>
    <head>
      <title>API Docs</title>
      <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@4/swagger-ui.css">
    </head>
    <body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@4/swagger-ui-bundle.js"></script>
    <script>
      const ui = SwaggerUIBundle({
        url: '/openapi.json',
        dom_id: '#swagger-ui',
        presets: [SwaggerUIBundle.presets.apis],
      })
    </script>
    </body>
    </html>
    """
    return html
