# fpAppConfig.py
# Michael Kirk 2013
#
# Configuration for web service for FieldPrime browser login.
# For use by flask: app.config.from_object()
# Can be used to customize a server installation
#


# Flask config params:
MAX_CONTENT_LENGTH = 16 * 1024 * 1024             # Limit the size of file uploads

# Our app config params:
PHOTO_UPLOAD_FOLDER = '***REMOVED***/photos/'
DATA_ACCESS_MODULE = 'fp_common.models'      # Name of the py file providing the data access layer.
CATEGORY_IMAGE_FOLDER = '***REMOVED***/htdocs/fpt/categoryImages/'
CATEGORY_IMAGE_URL_BASE = 'https://***REMOVED***/fpt/categoryImages/'
# DEBUG = True

# Log file to write to:
FPLOG_FILE = '***REMOVED***/fplog/fp.log'
