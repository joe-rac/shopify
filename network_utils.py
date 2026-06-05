import json
import time
import pprint
from datetime import datetime
# install with
# pip install requests
import requests

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

def _ts():
    return datetime.now().strftime("%H:%M:%S")

def post_and_json_decode_with_retry(url, headers, data=None, json_data=None, largest_valid_status=299, timeout=None):
    """
    Perform a requests.post with retry if transient failures. can still return error if res.get('errors') exists.
    Must pass in only one of data or json.

    Returns:
        (response, error)

    Success:
        response is a requests.Response in json format with no res.get('errors')
        error == ""

    Failure:
        response may be None or a requests.Response
        error is a non-empty descriptive message

    Retry policy:
        - Initial try
        - If retryable failure: sleep 2s, retry
        - If retryable failure: sleep 4s, retry
        - If retryable failure: sleep 8s, retry
        - Then give up

    Notes:
        - for now timeout is left as None meaning it does nothing. can be number of seconds before requests.post raises exception requests.exceptions.Timeout.
        - It is assumed results are in JSON form. If not then error.
        - Response object is always returned unchanged on success
        - No exceptions are intentionally raised for expected network/HTTP/JSON failures
    """

    response = None

    sleep_schedule = [2, 4, 8]   # after attempt 1, 2, 3
    total_attempts = len(sleep_schedule) + 1
    sleep_secs_tot = 0
    if not 200 <= largest_valid_status <= 299:
        raise Exception(f'largest_valid_status:{largest_valid_status} passed to post_and_json_decode_with_retry is invalid. Must be from 200 to 299.')
    if json_data and data:
        raise Exception('Both json_data and data passed to post_and_json_decode_with_retry. Can only pass one.')

    for attempt_num in range(1, total_attempts + 1):
        retryable = False

        try:
            response = requests.post(url,headers=headers,data=data,json=json_data,timeout=timeout)
            status = response.status_code
            reason = ''

            # Retryable HTTP statuses
            if status in RETRYABLE_STATUS_CODES:
                retryable = True
                reason = f"HTTP status:{status}"

            # Non-retryable HTTP failures
            elif not 200 <= status <= largest_valid_status:
                if largest_valid_status == 200:
                    error = f"{url} failed on attempt {attempt_num}: HTTP status:{status} not 200."
                else:
                    error = f"{url} failed on attempt {attempt_num}: HTTP status:{status} not in range 200 to {largest_valid_status}."
                print(f"{_ts()} {error}")
                return response,error

            body = response.text

            if body is None or body.strip() == "":
                retryable = True
                reason = "Empty response body when JSON expected."
            else:
                try:
                    # 5/19/2026. convert to json and validate.
                    res = response.json()
                except (ValueError, json.JSONDecodeError):
                    res = None
                    retryable = True
                    reason = "Response body not in JSON form."

            # XXX 5/19/2026. successfully avoided the need for retry
            if not retryable:
                if attempt_num > 1:
                    print(f'\nWe got lucky. After sleeping total of {sleep_secs_tot} secs request for url {url} miraculously succeeded.\n')
                errors = res.get('errors')
                error = pprint.pformat(errors,width=200) if errors else ''
                return res,error

        except requests.exceptions.Timeout as e:
            retryable = True
            reason = f"Timeout passed to post_and_json_decode_with_retry as {timeout}. Timeout exception:\n{e}."

        except requests.exceptions.SSLError as e:
            retryable = True
            reason = f"SSL error:\n{e}."

        except requests.exceptions.ConnectionError as e:
            retryable = True
            reason = f"Connection error:\n{e}."

        except requests.exceptions.RequestException as e:
            # Catch-all for other requests-layer failures.
            retryable = True
            reason = f"Request exception:\n{e}."

        # If retryable and retries remain, log and sleep
        if retryable and attempt_num < total_attempts:
            sleep_secs = sleep_schedule[attempt_num - 1]
            print(f"{_ts()} {url} attempt {attempt_num} failed with reason:\n{reason}\nRetrying in {sleep_secs} secs.")
            sleep_secs_tot += sleep_secs
            time.sleep(sleep_secs)
            continue

        # Final failure after exhausting retries
        error = f"{url} failed after {attempt_num} attempts. Total retry sleep time for all attempts:{sleep_secs_tot}. {reason}"
        print(f"{_ts()} {error}")
        return response,error

    # Should never get here, but keep a safe fallback.
    error = f"{url} failed: unexpected wrapper fallthrough in post_and_json_decode_with_retry. This code should never be executed. REPAIR."
    print(f"{_ts()} {error}")
    return response,error
