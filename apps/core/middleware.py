class AppendSlashNoRedirectMiddleware:
    """Silently append a trailing slash to the path before URL resolution,
    instead of issuing a 301 redirect. Prevents POST-body loss on clients
    (e.g. Flutter/Dio) that don't resubmit POST bodies across redirects."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        if not path.endswith("/") and "." not in path.split("/")[-1]:
            request.path_info = path + "/"
            request.META["PATH_INFO"] = request.path_info
        return self.get_response(request)
