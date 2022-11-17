from typing import Generator

import pytest
from fastapi.testclient import TestClient
from slowapi.extension import Limiter
from slowapi.util import get_remote_address

from fides.api.main import app
from fides.api.ops.api.v1.urn_registry import HEALTH
from fides.ctl.core.config import SecuritySettings, get_config

CONFIG = get_config()
LIMIT = 2


@pytest.fixture(scope="function")
def api_client_for_rate_limiting() -> Generator:
    """
    Return a client used to make API requests ratelimited at 2/minute.
    """
    app.state.limiter = Limiter(
        default_limits=[f"{LIMIT}/minute"],
        headers_enabled=True,
        key_prefix=CONFIG.security.rate_limit_prefix,
        key_func=get_remote_address,
        retry_after="http-date",
        storage_uri=CONFIG.redis.connection_url,
    )
    with TestClient(app) as c:
        yield c
        app.state.limiter = Limiter(
            default_limits=[CONFIG.security.request_rate_limit],
            headers_enabled=True,
            key_prefix=CONFIG.security.rate_limit_prefix,
            key_func=get_remote_address,
            retry_after="http-date",
            storage_uri=CONFIG.redis.connection_url,
        )


def test_requests_rate_limited(api_client_for_rate_limiting, cache):
    """
    Asserts that incremental HTTP requests above the ratelimit threshold are
    rebuffed from the API with a 429 response.

    A theoretical failure condition exists in this test should the container
    running it not be able to execute 100 requests against the client in a
    one minute period.
    """
    for _ in range(0, LIMIT):
        response = api_client_for_rate_limiting.get(HEALTH)
        assert response.status_code == 200

    response = api_client_for_rate_limiting.get(HEALTH)
    assert response.status_code == 429

    ratelimiter_cache_keys = [key for key in cache.keys() if key.startswith("LIMITER/")]
    for key in ratelimiter_cache_keys:
        # Depending on what requests have been stored previously, the ratelimtier will
        # store keys in the format `LIMITER/fides-/127.0.0.1//health/100/1/minute`
        assert key.startswith(f"LIMITER/{CONFIG.security.rate_limit_prefix}")
        # Reset the cache to not interere with any other tests
        cache.delete(key)


def test_rate_limit_validation():
    """Tests `SecuritySettings.validate_request_rate_limit`"""
    VALID_VALUES = [
        "10 per hour",
        "10/hour",
        "10/hour;100/day;2000 per year",
        "100/day, 500/7days",
    ]
    for value in VALID_VALUES:
        assert SecuritySettings.validate_request_rate_limit(v=value)

    INVALID_VALUE = "invalid-value"
    with pytest.raises(ValueError) as exc:
        SecuritySettings.validate_request_rate_limit(v=INVALID_VALUE)
