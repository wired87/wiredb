import os

import requests


def get_creds(
        types:list =["HEAD"]
):
    # Fetch server
    key = os.environ.get("SERVER_ACCESS_KEY")

    # Get request url
    endpoint = os.environ.get("CREDS_REQUEST_ENDPOINT")
    domain = os.environ.get("DOMAIN")

    if os.name == "nt":
        request_url = "http://127.0.0.1:8001" + endpoint
    else:
        request_url = f"https://{domain}{endpoint}"

        #RELAY_ENDPOINT
        os.environ["RELAY_ENDPOINT"] = request_url

    response = requests.get(
        request_url,
        data={"key": key, "types": types}
    )

    if not response.ok:
        return None

    creds = response.json()

    if isinstance(creds, dict):
        return creds

    return None