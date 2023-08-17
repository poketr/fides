import pytest

from fides.api.schemas.tcf import EmbeddedVendor
from fides.api.util.tcf_util import get_tcf_contents
from tests.fixtures.saas.connection_template_fixtures import instantiate_connector


class TestGetTCFPurposesAndVendors:
    def test_load_tcf_data_uses_no_applicable_systems(self, db):
        get_tcf_contents.cache_clear()

        tcf_contents = get_tcf_contents(db)
        assert tcf_contents.tcf_purposes == []
        assert tcf_contents.tcf_vendors == []
        assert tcf_contents.tcf_special_purposes == []
        assert tcf_contents.tcf_features == []
        assert tcf_contents.tcf_special_features == []

    @pytest.mark.usefixtures("system")
    def test_load_tcf_data_uses_systems_but_no_overlapping_use(self, db):
        get_tcf_contents.cache_clear()

        tcf_contents = get_tcf_contents(db)
        assert tcf_contents.tcf_purposes == []
        assert tcf_contents.tcf_vendors == []
        assert tcf_contents.tcf_special_purposes == []
        assert tcf_contents.tcf_features == []
        assert tcf_contents.tcf_special_features == []

    @pytest.mark.usefixtures("tcf_system")
    def test_system_exists_with_tcf_data_use_but_no_official_vendor_linked(
        self, db, tcf_system
    ):
        get_tcf_contents.cache_clear()

        tcf_system.vendor_id = None
        tcf_system.save(db)

        tcf_contents = get_tcf_contents(db)
        assert len(tcf_contents.tcf_purposes) == 1
        assert tcf_contents.tcf_purposes[0].id == 8
        assert tcf_contents.tcf_vendors == []
        assert tcf_contents.tcf_features == []
        assert tcf_contents.tcf_special_features == []

    @pytest.mark.usefixtures("tcf_system")
    def test_system_exists_with_tcf_purpose_and_vendor(self, db, tcf_system):
        get_tcf_contents.cache_clear()

        tcf_contents = get_tcf_contents(db)
        assert len(tcf_contents.tcf_purposes) == 1
        assert tcf_contents.tcf_purposes[0].id == 8
        assert tcf_contents.tcf_purposes[0].data_uses == [
            "analytics.reporting.content_performance"
        ]
        assert tcf_contents.tcf_purposes[0].vendors == [
            EmbeddedVendor(id="sendgrid", name="TCF System Test")
        ]

        assert len(tcf_contents.tcf_vendors) == 1
        assert tcf_contents.tcf_vendors[0].id == "sendgrid"
        assert tcf_contents.tcf_vendors[0].name == "TCF System Test"
        assert tcf_contents.tcf_vendors[0].description == "My TCF System Description"
        assert len(tcf_contents.tcf_vendors[0].purposes) == 1
        assert tcf_contents.tcf_vendors[0].purposes[0].id == 8
        assert tcf_contents.tcf_features == []
        assert tcf_contents.tcf_special_features == []

    @pytest.mark.usefixtures("tcf_system")
    def test_system_matches_subset_of_purpose_data_uses(self, db, tcf_system):
        get_tcf_contents.cache_clear()

        decl = tcf_system.privacy_declarations[0]
        decl.data_use = "marketing.advertising.first_party.contextual"
        tcf_system.privacy_declarations[0].save(db)

        decl_2 = tcf_system.privacy_declarations[1]
        decl_2.delete(db)

        tcf_contents = get_tcf_contents(db)

        assert len(tcf_contents.tcf_purposes) == 1
        assert tcf_contents.tcf_purposes[0].id == 2
        assert tcf_contents.tcf_purposes[0].data_uses == [
            "marketing.advertising.first_party.contextual",
            "marketing.advertising.frequency_capping",
            "marketing.advertising.negative_targeting",
        ]
        assert tcf_contents.tcf_purposes[0].vendors == [
            EmbeddedVendor(id="sendgrid", name="TCF System Test")
        ]

        assert len(tcf_contents.tcf_vendors) == 1
        assert tcf_contents.tcf_vendors[0].id == "sendgrid"
        assert len(tcf_contents.tcf_vendors[0].purposes) == 1
        assert tcf_contents.tcf_vendors[0].purposes[0].id == 2
        assert tcf_contents.tcf_features == []
        assert tcf_contents.tcf_special_features == []

    @pytest.mark.usefixtures("tcf_system")
    def test_special_purposes(self, db):
        get_tcf_contents.cache_clear()

        tcf_contents = get_tcf_contents(db)
        assert len(tcf_contents.tcf_special_purposes) == 1
        assert tcf_contents.tcf_special_purposes[0].id == 1
        assert (
            tcf_contents.tcf_special_purposes[0].name
            == "Ensure security, prevent and detect fraud, and fix errors\n"
        )
        assert tcf_contents.tcf_special_purposes[0].vendors == [
            EmbeddedVendor(id="sendgrid", name="TCF System Test")
        ]

        assert len(tcf_contents.tcf_purposes) == 1

        assert len(tcf_contents.tcf_vendors) == 1
        assert tcf_contents.tcf_vendors[0].id == "sendgrid"
        assert len(tcf_contents.tcf_vendors[0].purposes) == 1
        assert tcf_contents.tcf_vendors[0].purposes[0].id == 8
        assert len(tcf_contents.tcf_vendors[0].special_purposes) == 1
        assert tcf_contents.tcf_vendors[0].special_purposes[0].id == 1
        assert tcf_contents.tcf_features == []
        assert tcf_contents.tcf_special_features == []
