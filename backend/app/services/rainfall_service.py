import os
from datetime import datetime, timezone
from typing import Any

import requests

from backend.app.models.rainfall import RainfallData


# =========================================================
# CONFIGURATION
# =========================================================

IMD_BASE_URL = os.getenv(
    "IMD_BASE_URL",
    "https://api.imd.gov.in/api/v1",
).rstrip("/")

IMD_API_KEY = os.getenv("IMD_API_KEY")

DEFAULT_STATION = os.getenv(
    "IMD_DEFAULT_STATION",
    "Mumbai",
)

REQUEST_TIMEOUT_SECONDS = 15


# =========================================================
# DEVELOPMENT / FALLBACK RESPONSE
# =========================================================

def _development_response(
    status: str,
    rainfall_mm: float = 0.0,
    station: str = DEFAULT_STATION,
) -> RainfallData:
    """
    Create a clearly marked non-live rainfall response.

    IMPORTANT:
    rainfall_mm=0.0 here does NOT mean that actual Mumbai
    rainfall is zero. It means live rainfall is unavailable.
    """

    return RainfallData(
        timestamp=datetime.now(timezone.utc),
        station=station,
        rainfall_mm=max(0.0, float(rainfall_mm)),
        unit="mm",
        status=status,
    )


# =========================================================
# API KEY
# =========================================================

def _get_api_key() -> str | None:
    """
    Read the IMD API key at request time.

    Reading it dynamically makes local development easier
    if the environment variable is configured after the
    application starts.
    """

    key = os.getenv("IMD_API_KEY")

    if key:
        key = key.strip()

    return key or None


# =========================================================
# GENERIC IMD REQUEST
# =========================================================

def _imd_get(
    endpoint: str,
    params: dict[str, Any] | None = None,
) -> Any:
    """
    Send a GET request to an IMD endpoint.

    The endpoint must be supplied by the approved IMD API
    documentation/account configuration.
    """

    api_key = _get_api_key()

    if not api_key:
        raise RuntimeError(
            "IMD_API_KEY is not configured"
        )

    endpoint = endpoint.strip("/")

    url = f"{IMD_BASE_URL}/{endpoint}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    response.raise_for_status()

    return response.json()


# =========================================================
# NORMALIZE RECORDS
# =========================================================

def _extract_records(
    raw_data: Any,
) -> list[dict[str, Any]]:
    """
    Normalize common JSON container structures.

    Supported shapes:

        [...]
        {"data": [...]}
        {"data": {...}}

    Unknown structures return an empty list instead of
    causing the application to crash.
    """

    if isinstance(raw_data, list):

        return [
            item
            for item in raw_data
            if isinstance(item, dict)
        ]

    if isinstance(raw_data, dict):

        data = raw_data.get("data")

        if isinstance(data, list):

            return [
                item
                for item in data
                if isinstance(item, dict)
            ]

        if isinstance(data, dict):

            return [data]

    return []


# =========================================================
# TEXT HELPERS
# =========================================================

def _clean_text(value: Any) -> str:
    """
    Convert a value to normalized text.
    """

    if value is None:
        return ""

    return str(value).strip()


# =========================================================
# FIND MUMBAI RECORD
# =========================================================

def _find_mumbai_record(
    records: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """
    Find a record associated with Mumbai.

    This is intentionally conservative.

    If no Mumbai-specific record can be identified,
    None is returned instead of silently selecting a
    random station.
    """

    location_keys = [
        "Station",
        "STATION",
        "station",
        "District",
        "DISTRICT",
        "district",
        "City",
        "CITY",
        "city",
        "Location",
        "LOCATION",
        "location",
        "Name",
        "NAME",
        "name",
    ]

    for record in records:

        values = [
            record.get(key)
            for key in location_keys
        ]

        text = " ".join(
            _clean_text(value)
            for value in values
            if value is not None
        ).upper()

        if "MUMBAI" in text:
            return record

    return None


# =========================================================
# NUMBER PARSER
# =========================================================

def _to_float(
    value: Any,
) -> float | None:
    """
    Safely convert a value to float.

    Handles values such as:

        12.5
        "12.5"
        "12.5 mm"
        "1,234.5"
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    try:

        text = str(value).strip()

        if not text:
            return None

        # Remove common formatting.
        text = (
            text
            .replace(",", "")
            .replace("mm", "")
            .replace("MM", "")
            .strip()
        )

        return float(text)

    except (TypeError, ValueError):

        return None


# =========================================================
# FIND RAINFALL FIELD
# =========================================================

def _extract_rainfall_from_record(
    record: dict[str, Any],
) -> float | None:
    """
    Look for rainfall only in explicitly known field names.

    IMPORTANT:
    These are compatibility candidates, not a claim about
    the final approved IMD schema.

    Once the approved IMD response is available, this list
    should be narrowed to the exact documented field.
    """

    rainfall_keys = [
        "RAINFALL",
        "Rainfall",
        "rainfall",
        "RAIN",
        "rain",
        "RF",
        "rf",
        "rainfall_mm",
        "rainfallMm",
        "rainfall_mm_24h",
        "Last 24 hrs Rainfall",
        "LAST_24_HRS_RAINFALL",
        "LAST_24_HOURS_RAINFALL",
    ]

    for key in rainfall_keys:

        if key not in record:
            continue

        rainfall = _to_float(
            record.get(key)
        )

        if rainfall is None:
            continue

        # Rainfall cannot physically be negative.
        if rainfall < 0:
            return None

        return rainfall

    return None


# =========================================================
# FIND STATION NAME
# =========================================================

def _extract_station_name(
    record: dict[str, Any],
) -> str:
    """
    Extract a station name from commonly used fields.
    """

    station_keys = [
        "STATION",
        "Station",
        "station",
        "CALL_SIGN",
        "Call Sign",
        "call_sign",
        "NAME",
        "Name",
        "name",
    ]

    for key in station_keys:

        value = record.get(key)

        if value is not None:

            text = _clean_text(value)

            if text:
                return text

    return DEFAULT_STATION


# =========================================================
# FETCH CURRENT AWS DATA
# =========================================================

def _fetch_aws_data() -> Any:
    """
    Fetch AWS data using the currently configured endpoint.

    IMPORTANT:
    The exact endpoint must match the endpoint granted to
    your IMD API credentials.
    """

    return _imd_get(
        "aws_data",
    )


# =========================================================
# PARSE LIVE IMD RESPONSE
# =========================================================

def _parse_imd_rainfall(
    raw_data: Any,
) -> RainfallData:
    """
    Convert an IMD response into RainfallData.

    This function deliberately refuses to mark data as live
    unless a Mumbai record and a recognizable rainfall value
    are actually present.
    """

    records = _extract_records(
        raw_data
    )

    if not records:

        return _development_response(
            status="imd_no_records",
        )

    # -----------------------------------------------------
    # Prefer Mumbai
    # -----------------------------------------------------

    selected_record = _find_mumbai_record(
        records
    )

    if selected_record is None:

        return _development_response(
            status="imd_mumbai_record_not_found",
        )

    # -----------------------------------------------------
    # Rainfall
    # -----------------------------------------------------

    rainfall_mm = _extract_rainfall_from_record(
        selected_record
    )

    if rainfall_mm is None:

        return _development_response(
            status=(
                "imd_connected_"
                "rainfall_field_not_found"
            ),
        )

    # -----------------------------------------------------
    # Station
    # -----------------------------------------------------

    station_name = _extract_station_name(
        selected_record
    )

    # -----------------------------------------------------
    # Timestamp
    #
    # Until the exact IMD timestamp field is confirmed,
    # use processing time rather than inventing an
    # observation timestamp.
    # -----------------------------------------------------

    timestamp = datetime.now(
        timezone.utc
    )

    return RainfallData(
        timestamp=timestamp,
        station=station_name,
        rainfall_mm=float(rainfall_mm),
        unit="mm",
        status="imd_live",
    )


# =========================================================
# PUBLIC SERVICE
# =========================================================

def get_latest_rainfall() -> RainfallData:
    """
    Return the latest rainfall observation.

    Possible states:

        waiting_for_imd_api_key
        imd_api_error:...
        imd_no_records
        imd_mumbai_record_not_found
        imd_connected_rainfall_field_not_found
        imd_live
        rainfall_processing_error:...

    Only "imd_live" is treated as live rainfall by the
    flood-model pipeline.
    """

    # =====================================================
    # 1. CHECK API KEY
    # =====================================================

    api_key = _get_api_key()

    if not api_key:

        return _development_response(
            status="waiting_for_imd_api_key",
        )

    # =====================================================
    # 2. REQUEST IMD
    # =====================================================

    try:

        raw_data = _fetch_aws_data()

    except requests.HTTPError as exc:

        status_code = (
            exc.response.status_code
            if exc.response is not None
            else "unknown"
        )

        return _development_response(
            status=(
                f"imd_http_error:{status_code}"
            ),
        )

    except requests.Timeout:

        return _development_response(
            status="imd_api_error:timeout",
        )

    except requests.ConnectionError:

        return _development_response(
            status="imd_api_error:connection",
        )

    except requests.RequestException as exc:

        return _development_response(
            status=(
                "imd_api_error:"
                f"{type(exc).__name__}"
            ),
        )

    except RuntimeError as exc:

        return _development_response(
            status=(
                "imd_configuration_error:"
                f"{str(exc)}"
            ),
        )

    # =====================================================
    # 3. PARSE RESPONSE
    # =====================================================

    try:

        return _parse_imd_rainfall(
            raw_data
        )

    except Exception as exc:

        return _development_response(
            status=(
                "rainfall_processing_error:"
                f"{type(exc).__name__}"
            ),
        )