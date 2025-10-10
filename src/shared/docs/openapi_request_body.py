from typing import Any, Callable


def openapi_request_body(schema_ref: Any):
    """Attach `openapi_request_body` attribute to the view function.

    Usage:
        @openapi_request_body('RefreshRequest')
        def logout():
            ...

    The `dump_openapi.py` script will look for this attribute and emit a
    requestBody referencing the registered component schema.
    """

    def decorator(fn: Callable):
        setattr(fn, 'openapi_request_body', schema_ref)

        # If the function is wrapped (e.g. by decorators like jwt_required), try to
        # set the attribute on the wrapped function too so dump_openapi can find it.
        wrapped = getattr(fn, '__wrapped__', None)
        if wrapped is not None:
            setattr(wrapped, 'openapi_request_body', schema_ref)

        return fn

    return decorator
