import json

from django.utils.cache import patch_response_headers
from functools import wraps

from .utils import hash_key
from django.core.cache import cache


def _cache_page(
        timeout,
        key_func,
        lock_object=None
):
    def _cache(view_func):
        @wraps(view_func)
        def __cache(self, request, *args, **kwargs):
            if request.method not in ["GET", "HEAD"]:
                return view_func(self, request, *args, **kwargs)
            if lock_object is not None and not lock_object(self, request, *args, **kwargs):
                return view_func(self, request, *args, **kwargs)

            # cache_key = hash_key(key_func(request, self))
            cache_key = key_func(request, self)
            if getattr(request, 'do_not_cache', False):
                return view_func(self, request, *args, **kwargs)
            if json.loads(request.GET.get("delete_cache", "false")):
                group = key_func(request, self, only_group=True)
                for key in cache.keys(group + "*"):
                    cache.delete(key)
                return view_func(self, request, *args, **kwargs)
            response = cache.get(cache_key)
            process_caching = not response or getattr(request, '_bust_cache', False)
            if process_caching:
                response = view_func(self, request, *args, **kwargs)
                if response.status_code == 200:
                    # patch_response_headers(response, timeout)
                    if hasattr(response, 'render') and callable(response.render):
                        def set_cache(val) -> None:
                            cache.set(cache_key, val, timeout)
                        response.add_post_render_callback(set_cache)
                    else:
                        cache.set(cache_key, response, timeout)
            setattr(request, '_cache_update_cache', False)
            return response
        return __cache
    return _cache


def cache_page(
    timeout,
    key_func,
    lock_object=None
):
    return _cache_page(
        timeout,
        key_func,
        lock_object=lock_object
    )
