from django.conf import settings

# Paths that will allow field values to be searched for Ajax list filters.
# Each path is a tuple of the form (app_name, model_name, field_name).
settings.DAS_ALLOWED_AJAX_SEARCH_PATHS = getattr(
    settings,
    'DAS_ALLOWED_AJAX_SEARCH_PATHS',
    [])

# Convert our path list to a set so we can quickly check it for matches.
settings.DAS_ALLOWED_AJAX_SEARCH_PATHS = set(settings.DAS_ALLOWED_AJAX_SEARCH_PATHS)

settings.DAS_MAX_AJAX_SEARCH_RESULTS = getattr(
    settings,
    'DAS_MAX_AJAX_SEARCH_RESULTS',
    10)

settings.DAS_AJAX_SEARCH_DEFAULT_CACHE_SECONDS = getattr(
    settings,
    'DAS_AJAX_SEARCH_DEFAULT_CACHE_SECONDS',
    3600)

settings.DAS_AJAX_SEARCH_PATH_FIELDS = getattr(
    settings,
    'DAS_AJAX_SEARCH_PATH_FIELDS',
    {})
