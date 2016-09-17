from base64 import b64decode
import json
import logging
from dateutil import parser
from redash.query_runner import *
from redash.utils import JSONEncoder
from inflector import Inflector

logger = logging.getLogger(__name__)
inflector = Inflector()

try:
    from apiclient.discovery import build
    import httplib2
    from oauth2client.client import SignedJwtAssertionCredentials
    enabled = True
except ImportError:
    enabled = False


class GoogleAnalytics(BaseQueryRunner):
    @classmethod
    def annotate_query(cls):
        return False

    @classmethod
    def type(cls):
        return "google_analytics"

    @classmethod
    def enabled(cls):
        return enabled

    @classmethod
    def configuration_schema(cls):
        return {
            'type': 'object',
            'properties': {
                'serviceAccountJsonKeyFile': {
                    'type': 'string',
                    'title': 'serviceAccountJsonKeyFile'
                }
            },
            'required': ['serviceAccountJsonKeyFile'],
            'secret': ['serviceAccountJsonKeyFile']
        }

    def __init__(self, configuration):
        super(GoogleAnalytics, self).__init__(configuration)
        self.syntax = 'json'
    
    def _print_results(self, results):
        # Print data nicely for the user.
        if results:
            print 'View (Profile): %s' % results.get('profileInfo').get('profileName')
            print 'Total Sessions: %s' % results.get('rows')[0][0]
    
        else:
            print 'No results found'

    def get_service(self):
        return self._get_analytics_service()

    def _get_data(self,service,query):
        params = json.loads(query)
        return service.data().ga().get(**params).execute()

    def _format_column(self, column):
        name = column['name']
        print name 
        if name=='ga:date':
            column['type'] = 'date'
        column['friendly_name'] = inflector.humanize(name[3:])
        return column

    def _format_row(self, column, row):
        print column
        if column['type']=='date':
            row="{0}-{1}-{2}".format(row[:4],row[4:6],row[6:])
        return row

    def _format_data(self, results):
        headers = results.get('columnHeaders')
        columns = []
        
        for column in headers:
            columns.append(self._format_column({
                'name': column.get('name'),
                'type': column.get('dataType').lower(),
                'friendly_name': column.get('name')
            }))

        data = results.get('rows')
        rows = []

        for row in data:
            r = {}
            for idx,c in enumerate(row):
                col = columns[idx]
                r[col['name']] = self._format_row(col,c)

            rows.append(r)
            
        return {'columns': columns, 'rows': rows}

    def _get_analytics_service(self):
        api_name = 'analytics'
        api_version = 'v3'
        scope = [
            'https://www.googleapis.com/auth/analytics.readonly',
        ]

        key = json.loads(b64decode(self.configuration['serviceAccountJsonKeyFile']))
        credentials = SignedJwtAssertionCredentials(key['client_email'], key["private_key"], scope=scope)
        http = credentials.authorize(http=httplib2.Http())
        service = build(api_name, api_version, http=http)
        return service 

    def run_query(self, query):
        logger.debug("GoogleAnalytics is about to execute query: %s", query)

        service = self._get_analytics_service()
        try:
            result = self._get_data(service,query)
            result = self._format_data(result)
            json_data = json.dumps(result, cls=JSONEncoder)
            error = None
        except:
            json_data = None
            error = "Api access error"

        return json_data, error

register(GoogleAnalytics)
