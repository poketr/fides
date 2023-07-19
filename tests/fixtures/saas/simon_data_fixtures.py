from typing import Any, Dict, Generator

import pydash
import pytest

from tests.ops.integration_tests.saas.connector_runner import (
    ConnectorRunner,
    generate_random_email,
)
from tests.ops.test_helpers.vault_client import get_secrets

secrets = get_secrets("simon_data")


@pytest.fixture(scope="session")
def simon_data_secrets(saas_config) -> Dict[str, Any]:
    return {
        "domain": pydash.get(saas_config, "simon_data.domain") or secrets["domain"],
        "api_key": pydash.get(saas_config, "simon_data.api_key") or secrets["api_key"],
    }


@pytest.fixture(scope="session")
def simon_data_identity_email(saas_config) -> str:
    return (
        pydash.get(saas_config, "simon_data.identity_email")
        or secrets["identity_email"]
    )


@pytest.fixture
def simon_data_erasure_identity_email() -> str:
    return generate_random_email()


@pytest.fixture
def simon_data_external_references() -> Dict[str, Any]:
    return {}


@pytest.fixture
def simon_data_erasure_external_references() -> Dict[str, Any]:
    return {}


@pytest.fixture
def simon_data_erasure_data(
    simon_data_erasure_identity_email: str,
) -> Generator:
    # create the data needed for erasure tests here
    yield {}


@pytest.fixture
def simon_data_runner(
    db,
    cache,
    simon_data_secrets,
    simon_data_external_references,
    simon_data_erasure_external_references,
) -> ConnectorRunner:
    return ConnectorRunner(
        db,
        cache,
        "simon_data",
        simon_data_secrets,
        external_references=simon_data_external_references,
        erasure_external_references=simon_data_erasure_external_references,
    )
