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
