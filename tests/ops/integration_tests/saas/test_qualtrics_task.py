import pytest

from fides.api.models.policy import Policy
from tests.ops.integration_tests.saas.connector_runner import ConnectorRunner


@pytest.mark.integration_saas
class TestQualtricsConnector:
    def test_connection(self, qualtrics_runner: ConnectorRunner):
        qualtrics_runner.test_connection()

    async def test_access_request(
        self, qualtrics_runner: ConnectorRunner, policy, qualtrics_identity_email: str
    ):
        access_results = await qualtrics_runner.access_request(
            access_policy=policy, identities={"email": qualtrics_identity_email}
        )

        assert access_results["qualtrics_instance:search_directory_contact"][0]["email"] == qualtrics_identity_email

    # async def test_strict_erasure_request(
    #     self,
    #     qualtrics_runner: ConnectorRunner,
    #     policy: Policy,
    #     erasure_policy_string_rewrite: Policy,
    #     qualtrics_erasure_identity_email: str,
    #     qualtrics_erasure_data,
    # ):
    #     (
    #         access_results,
    #         erasure_results,
    #     ) = await qualtrics_runner.strict_erasure_request(
    #         access_policy=policy,
    #         erasure_policy=erasure_policy_string_rewrite,
    #         identities={"email": qualtrics_erasure_identity_email},
    #     )

    async def test_non_strict_erasure_request(
        self,
        qualtrics_runner: ConnectorRunner,
        policy: Policy,
        erasure_policy_string_rewrite: Policy,
        qualtrics_erasure_identity_email: str,
        qualtrics_erasure_data,
        qualtrics_client,
    ):
        (
            access_results,
            erasure_results,
        ) = await qualtrics_runner.non_strict_erasure_request(
            access_policy=policy,
            erasure_policy=erasure_policy_string_rewrite,
            identities={"email": qualtrics_erasure_identity_email},
        )

        assert erasure_results == {
            "qualtrics_instance:search_directory_contact": 0,
            "qualtrics_instance:directory_contacts": 1,
        }

        response = qualtrics_client.get_directory_contacts(qualtrics_erasure_identity_email)
        # Check whether user details updated or not
        directory_contacts_response = response.json()
        assert directory_contacts_response['result']['elements'][0]["firstName"] == "MASKED"
        assert directory_contacts_response['result']['elements'][0]["lastName"]  == "MASKED"