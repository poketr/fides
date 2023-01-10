from datetime import datetime, timedelta, timezone
from time import sleep
from typing import List
from unittest import mock
from uuid import uuid4

import pytest

from fides.api.ctl.database.seed import DEFAULT_CONSENT_POLICY
from fides.api.ops.api.v1.endpoints.consent_request_endpoints import (
    CONFIG_JSON_PATH,
    load_executable_consent_options,
    queue_privacy_request_to_propagate_consent,
)
from fides.api.ops.graph.config import CollectionAddress
from fides.api.ops.models.privacy_request import (
    Consent,
    ConsentRequest,
    PrivacyRequestStatus,
    ProvidedIdentity,
)
from fides.api.ops.schemas.policy import PolicyResponse
from fides.api.ops.schemas.privacy_request import (
    BulkPostPrivacyRequests,
    ConsentPreferences,
    PrivacyRequestResponse,
)
from fides.core.config import get_config

paused_location = CollectionAddress("test_dataset", "test_collection")

CONFIG = get_config()


def test_consent(db):
    provided_identity_data = {
        "privacy_request_id": None,
        "field_name": "email",
        "encrypted_value": {"value": "test@email.com"},
    }
    provided_identity = ProvidedIdentity.create(db, data=provided_identity_data)

    consent_data_1 = {
        "provided_identity_id": provided_identity.id,
        "data_use": "user.biometric_health",
        "opt_in": True,
    }
    consent_1 = Consent.create(db, data=consent_data_1)

    consent_data_2 = {
        "provided_identity_id": provided_identity.id,
        "data_use": "user.browsing_history",
        "opt_in": False,
    }
    consent_2 = Consent.create(db, data=consent_data_2)
    data_uses = [x.data_use for x in provided_identity.consent]

    assert consent_data_1["data_use"] in data_uses
    assert consent_data_2["data_use"] in data_uses

    provided_identity.delete(db)

    assert Consent.get(db, object_id=consent_1.id) is None
    assert Consent.get(db, object_id=consent_2.id) is None


def test_consent_request(db):
    provided_identity_data = {
        "privacy_request_id": None,
        "field_name": "email",
        "encrypted_value": {"value": "test@email.com"},
    }
    provided_identity = ProvidedIdentity.create(db, data=provided_identity_data)

    consent_request_1 = {
        "provided_identity_id": provided_identity.id,
    }
    consent_1 = ConsentRequest.create(db, data=consent_request_1)

    consent_request_2 = {
        "provided_identity_id": provided_identity.id,
    }
    consent_2 = ConsentRequest.create(db, data=consent_request_2)

    assert consent_1.provided_identity_id in provided_identity.id
    assert consent_2.provided_identity_id in provided_identity.id

    provided_identity.delete(db)

    assert Consent.get(db, object_id=consent_1.id) is None
    assert Consent.get(db, object_id=consent_2.id) is None


class TestLoadExecutableConsentOptionsHelper:
    def test_load_executable_consent_options(self):
        options: List[str] = load_executable_consent_options(CONFIG_JSON_PATH)
        assert options == ["advertising", "advertising.first_party", "improve"]

    def test_load_options_some_not_executable(self):
        other_options: List[str] = load_executable_consent_options(
            "tests/ops/fixtures/privacy_center_config/test_config.json"
        )
        assert other_options == ["advertising.first_party"]

    def test_load_invalid_config_json(self):
        other_options: List[str] = load_executable_consent_options(
            "tests/ops/fixtures/privacy_center_config/bad_test_config.json"
        )
        assert other_options == []

    def test_config_json_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_executable_consent_options("bad_path.json")


class TestQueuePrivacyRequestToPropagateConsentHelper:
    @mock.patch(
        "fides.api.ops.api.v1.endpoints.consent_request_endpoints.create_privacy_request_func"
    )
    def test_queue_privacy_request_to_propagate_consent(
        self, mock_create_privacy_request, db, consent_policy
    ):
        mock_create_privacy_request.return_value = BulkPostPrivacyRequests(
            succeeded=[
                PrivacyRequestResponse(
                    id="fake_privacy_request_id",
                    status=PrivacyRequestStatus.pending,
                    policy=PolicyResponse.from_orm(consent_policy),
                )
            ],
            failed=[],
        )
        provided_identity_data = {
            "privacy_request_id": None,
            "field_name": "email",
            "encrypted_value": {"value": "test@email.com"},
        }
        provided_identity = ProvidedIdentity.create(db, data=provided_identity_data)

        consent_preferences = ConsentPreferences(
            consent=[{"data_use": "advertising", "opt_in": False}]
        )

        queue_privacy_request_to_propagate_consent(
            db=db,
            provided_identity=provided_identity,
            policy=DEFAULT_CONSENT_POLICY,
            consent_preferences=consent_preferences,
        )

        assert mock_create_privacy_request.called
        call_kwargs = mock_create_privacy_request.call_args[1]
        assert call_kwargs["db"] == db
        assert call_kwargs["data"][0].identity.email == "test@email.com"
        assert len(call_kwargs["data"][0].consent_preferences) == 1
        assert call_kwargs["data"][0].consent_preferences[0].data_use == "advertising"
        assert call_kwargs["data"][0].consent_preferences[0].opt_in is False
        assert (
            call_kwargs["authenticated"] is True
        ), "We already validated identity with a verification code earlier in the request"

        provided_identity.delete(mock_create_privacy_request)

    @mock.patch(
        "fides.api.ops.api.v1.endpoints.consent_request_endpoints.create_privacy_request_func"
    )
    def test_do_not_queue_privacy_request_if_no_executable_preferences(
        self, mock_create_privacy_request, db, consent_policy
    ):
        mock_create_privacy_request.return_value = BulkPostPrivacyRequests(
            succeeded=[
                PrivacyRequestResponse(
                    id="fake_privacy_request_id",
                    status=PrivacyRequestStatus.pending,
                    policy=PolicyResponse.from_orm(consent_policy),
                )
            ],
            failed=[],
        )
        provided_identity_data = {
            "privacy_request_id": None,
            "field_name": "email",
            "encrypted_value": {"value": "test@email.com"},
        }
        provided_identity = ProvidedIdentity.create(db, data=provided_identity_data)

        queue_privacy_request_to_propagate_consent(
            db=db,
            provided_identity=provided_identity,
            policy=DEFAULT_CONSENT_POLICY,
            consent_preferences=ConsentPreferences(consent=[]),
        )

        assert not mock_create_privacy_request.called
