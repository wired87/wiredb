import datetime

def sp_timestamp():
    spanner_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
    return spanner_timestamp