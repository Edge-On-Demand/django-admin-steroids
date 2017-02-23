
# Just here so our default settings are inserted into django.conf.settings.
from . import settings as _settings # pylint: disable=unused-import

# {(app_label, model_name, field_name): callable}
_modelsearch_callbacks = {}

def register_modelsearcher(app_label, model_name, field_name, cb):
    _modelsearch_callbacks[
        (app_label.lower(), model_name.lower(), field_name.lower())] = cb

def get_modelsearcher(app_label, model_name, field_name):
    return _modelsearch_callbacks.get(
        (app_label.lower(), model_name.lower(), field_name.lower()))
