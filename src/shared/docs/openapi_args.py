from functools import wraps


def openapi_query_args(args_map):
    """Decorator that attaches an `openapi_query_args` attribute to a view function.

    Usage:
        @openapi_query_args({'id': fields.Int(...), ...})
        def listar(...):
            ...

    The decorator preserves the original function metadata using functools.wraps.
    """

    def decorator(fn):
        # attach attribute to the original function object
        setattr(fn, 'openapi_query_args', args_map)

        @wraps(fn)
        def wrapped(*args, **kwargs):
            return fn(*args, **kwargs)

        # also attach attribute to the wrapper to be safe
        setattr(wrapped, 'openapi_query_args', args_map)

        return wrapped

    return decorator
