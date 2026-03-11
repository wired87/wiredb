import logging
import os
from datetime import datetime, timezone

LOG_LEVEL = os.environ.get('DJANGO_LOG_LEVEL', 'INFO').upper()

logging.basicConfig(
    level=LOG_LEVEL, # Setzen Sie die gewünschte Log-Stufe
    format='%(asctime)s - %(name)s - %(levelname)s - %(threadName)s - %(message)s', # Format mit Thread-Name
    handlers=[
        logging.StreamHandler()
    ]
)
LOGGER = logging.getLogger(__name__)


def get_log_id(nid):
    # Get the current time in UTC with microseconds
    utc_now = datetime.now(timezone.utc)

    # Format the time to an ISO 8601 string including milliseconds and 'Z'
    formatted_string = utc_now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

    #print(f"Key set: {formatted_string}")#
    return f"{nid}__{formatted_string.replace('.', '_').replace(':', '_').replace('-', '_')}"
