"""Bounded Supabase reads; never load or write a local transit/history file."""
from functools import lru_cache
import json
import os

import requests

MAX_RESPONSE_BYTES = 192 * 1024
MAX_RESULTS = 200


class TransitUnavailable(Exception):
    """A safe public error without response bodies, keys, or coordinates."""


def _rpc(name: str, parameters: dict) -> dict:
    url = os.environ.get('SUPABASE_URL', '').rstrip('/')
    key = os.environ.get('SUPABASE_PUBLISHABLE_KEY', '')
    if not url.startswith('https://') or not key:
        raise TransitUnavailable('Transit service is not configured.')
    try:
        with requests.post(
            url + '/rest/v1/rpc/' + name,
            headers={'apikey': key, 'Content-Type': 'application/json'},
            json=parameters, timeout=(2, 5), stream=True,
        ) as response:
            response.raise_for_status()
            body = bytearray()
            for chunk in response.iter_content(8192):
                body.extend(chunk)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise TransitUnavailable('Transit response exceeded its size limit.')
            result = json.loads(body)
            if not isinstance(result, dict):
                raise TransitUnavailable('Transit response is unavailable.')
            return result
    except (requests.RequestException, ValueError) as exc:
        raise TransitUnavailable('Transit service is temporarily unavailable.') from None


def search(latitude: float, longitude: float, radius: float) -> dict:
    result = _rpc('bus_search', {'p_lat': latitude, 'p_lon': longitude, 'p_radius': radius})
    rows = result.get('results')
    if not isinstance(rows, list) or len(rows) > MAX_RESULTS or type(result.get('has_more')) is not bool:
        raise TransitUnavailable('Transit response is unavailable.')
    try:
        for row in rows:
            row['walkdistance'] = f"{int(row.pop('distance') * 1000)}m"
            row['board_busstopdescription'] = row['board_busstopdescription'].title()
            row['alight_busstopdescription'] = row['alight_busstopdescription'].title()
            row['mrt_color'] = next((color for line, color in (
                ('North-South', '#d42e12'), ('East-West', '#009645'),
                ('North-East', '#9900aa'), ('Circle', '#fa9e0d'),
                ('Downtown', '#005ec4'), ('Thomson', '#9d5b25'),
            ) if line in row['mrt_line']), '#64748b')
    except (KeyError, TypeError, ValueError, AttributeError):
        raise TransitUnavailable('Transit response is unavailable.') from None
    return result


@lru_cache(maxsize=1)
def facts() -> dict:
    """The imported historical facts are immutable within a deployment."""
    result = _rpc('bus_facts', {})
    if not all(isinstance(result.get(company), dict) and type(result.get(company+'_len')) is int
               for company in ('smrt', 'sbst', 'tts', 'gas')):
        raise TransitUnavailable('Transit facts are unavailable.')
    return result
