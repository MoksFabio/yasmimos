import decimal
from django.utils.deprecation import MiddlewareMixin

class DecimalSessionSanitizerMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        if not hasattr(request, 'session'):
            return response
            
        if request.session.modified:
            # Recursively convert decimals to strings in session data
            self._sanitize_session(request.session)
        return response

    def _sanitize_session(self, data):
        if isinstance(data, dict) or hasattr(data, 'keys'):
            # Iterate over a copy of the keys to avoid modification issues
            for key, value in list(data.items()):
                if isinstance(value, decimal.Decimal):
                    data[key] = str(value)
                elif hasattr(value, '_meta') and hasattr(value, 'pk'):
                    # Django Model Instance -> Store ID string
                    data[key] = str(value.pk)
                elif isinstance(value, (dict, list)):
                    self._sanitize_structure(value)
                    
    def _sanitize_structure(self, data):
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, decimal.Decimal):
                    data[key] = str(value)
                elif hasattr(value, '_meta') and hasattr(value, 'pk'):
                     data[key] = str(value.pk)
                elif isinstance(value, (dict, list)):
                    self._sanitize_structure(value)
        elif isinstance(data, list):
            for i, value in enumerate(data):
                if isinstance(value, decimal.Decimal):
                    data[i] = str(value)
                elif hasattr(value, '_meta') and hasattr(value, 'pk'):
                     data[i] = str(value.pk)
                elif isinstance(value, (dict, list)):
                    self._sanitize_structure(value)
