"""system dictionary data migration

Revision ID: fd52d5f08c17
Revises: 39397820a0d5
Create Date: 2023-08-04 14:14:32.421414

"""
import json
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from alembic import op

# revision identifiers, used by Alembic.
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.sql.elements import TextClause

revision = "fd52d5f08c17"
down_revision = "39397820a0d5"
branch_labels = None
depends_on = None
from fides.config import CONFIG

JOINT_CONTROLLER_INFO = "joint_controller_info"
DOES_INTERNATIONAL_TRANSFERS = "does_international_transfers"
RESPONSIBILITY = "responsibility"
REQUIRES_DATA_PROTECTION_ASSESSMENTS = "requires_data_protection_assessments"
DPA_LOCATION = "dpa_location"
DPA_PROGRESS = "dpa_progress"
SOURCE = "source"
DESTINATION = "destination"
DATASET_REFERENCES = "dataset_references"

LEGAL_BASIS_FOR_PROCESSING = "legal_basis_for_processing"
IMPACT_ASSESSMENT_LOCATION = "impact_assessment_location"
PROCESSES_SPECIAL_CATEGORY_DATA = "processes_special_category_data"
SPECIAL_CATEGORY_LEGAL_BASIS = "special_category_legal_basis"
DATA_SHARED_WITH_THIRD_PARTIES = "data_shared_with_third_parties"
THIRD_PARTIES = "third_parties"


def _system_transform_joint_controller_info(
    joint_controller_decrypted: Optional[Dict],
    datasets_joint_controller_decrypted: List[Optional[Dict]],
) -> Optional[str]:
    """ Migrating systems.joint_controller and datasets.joint_controller encrypted json string fields to
    System.joint_controller_info which is just a string.

    Prioritizing system joint_controller info if it exists, or taking the first non-null entry from datasets
    otherwise.
    """
    new_joint_controller_info: Optional[str] = None
    joint_controller_data = (
        joint_controller_decrypted
        or next(  # Multiple datasets can be related to a system, so we use the first non null one if applicable
            (
                item
                for item in datasets_joint_controller_decrypted or []
                if item is not None
            ),
            None,
        )
    )  # Prioritize system data over dataset data
    if joint_controller_data and isinstance(joint_controller_data, dict):
        name = joint_controller_data.get("name")
        address = joint_controller_data.get("address")
        email = joint_controller_data.get("email")
        phone = joint_controller_data.get("phone")

        for i, item in enumerate([name, address, email, phone]):
            if item and item != "N/A":
                if not new_joint_controller_info:
                    new_joint_controller_info = ""
                new_joint_controller_info += item
                if i != 3:
                    new_joint_controller_info += " "
    return new_joint_controller_info


def _system_calculate_does_international_transfers(
    system_third_country_transfers: Optional[List[str]], dataset_third_country_transfers: Optional[List[str]]
) -> bool:
    """Migrating System.third_country_transfers and Dataset.third_country_transfers to System.does_international_transfers
    If any countries listed, System.does_international_transfers will be set to true
    """
    return bool(system_third_country_transfers) or bool(dataset_third_country_transfers)


def _system_transform_data_responsibility_title_type(
    dept_str: Optional[str],
) -> List[str]:
    """Migrating System.data_responsibility_title (str) to System.responsibility(list).  There can now be potentially many
    items listed here"""
    if not dept_str:
        return []
    return [dept_str]


def _consolidate_privacy_declaration_dataset_references(
    existing_references: List[str], privacy_declaration_references: List[str]
) -> List[str]:
    """Migrating PrivacyDeclaration.dataset_references to System.dataset_references:
    Take all dataset references across all of a system's privacy declarations and consolidate into a single list"""
    if not existing_references:
        existing_references = []
    for ref in privacy_declaration_references:
        if ref not in existing_references:
            existing_references.append(ref)
    return existing_references


def _flatten_data_protection_impact_assessment(
    data_protection_impact_assessment: Optional[Dict],
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Flattening data from System.data_protection_impact_assessment into three separate fields:
    System.requires_data_protection_assessments, System.dpa_location, and System.dpa_progress
    """
    if not data_protection_impact_assessment or not isinstance(
        data_protection_impact_assessment, dict
    ):
        return False, None, None

    requires_data_protection_assessments = data_protection_impact_assessment.get(
        "is_required", False
    )
    dpa_progress = data_protection_impact_assessment.get("progress", None)
    dpa_location = data_protection_impact_assessment.get("link", None)
    return requires_data_protection_assessments, dpa_progress, dpa_location


def system_dictionary_additive_migration(bind: Connection):
    """Copy and/or transform existing data in Datasets, PrivacyDeclarations and the System itself to new
     Systems fields to support dictionary work"""
    system_dict: Dict = defaultdict(lambda: {})
    get_systems_query: TextClause = text(
        """
        SELECT 
            ctl_systems.id,
            pgp_sym_decrypt(ctl_systems.joint_controller::bytea, :encryption_key) AS joint_controller_decrypted,
            ctl_systems.third_country_transfers,
            ctl_systems.data_responsibility_title,
            ctl_systems.data_protection_impact_assessment,
            ctl_systems.ingress,
            ctl_systems.egress,
            array_accum(ctl_datasets.third_country_transfers) as dataset_third_country_transfers,
            array_agg(pgp_sym_decrypt(ctl_datasets.joint_controller::bytea, :encryption_key)) AS datasets_joint_controller_decrypted
        FROM ctl_systems
        LEFT JOIN privacydeclaration ON ctl_systems.id = privacydeclaration.system_id 
        LEFT JOIN ctl_datasets ON ctl_datasets.fides_key = ANY(privacydeclaration.dataset_references) GROUP BY ctl_systems.id
        """
    )
    for row in bind.execute(
        get_systems_query, {"encryption_key": CONFIG.user.encryption_key}
    ):
        system_id: str = row["id"]
        # System.joint_controller_info populated from flattened data from either System.joint_controller
        # or any of the Datasets.joint_controller. New field isn't as rigid on structure required.
        system_dict[system_id][
            JOINT_CONTROLLER_INFO
        ] = _system_transform_joint_controller_info(
            json.loads(row["joint_controller_decrypted"] or "null"),
            [
                json.loads(item)
                for item in row["datasets_joint_controller_decrypted"] or "null"
                if item
            ],
        )
        # System.does_international_transfers is populated based on whether System.third_country_transfers or
        # Dataset.third_country_transfers exist
        system_dict[system_id][
            DOES_INTERNATIONAL_TRANSFERS
        ] = _system_calculate_does_international_transfers(
            row["third_country_transfers"], row["dataset_third_country_transfers"]
        )
        # Populate System.requires_data_protection_assessments, System.dpa_progress, and System.dpa_location from
        # nested fields in System.data_responsibility_title
        system_dict[system_id][
            RESPONSIBILITY
        ] = _system_transform_data_responsibility_title_type(
            row["data_responsibility_title"]
        )
        (
            requires_data_protection_assessments,
            dpa_progress,
            dpa_location,
        ) = _flatten_data_protection_impact_assessment(
            row["data_protection_impact_assessment"]
        )
        system_dict[system_id][
            REQUIRES_DATA_PROTECTION_ASSESSMENTS
        ] = requires_data_protection_assessments
        system_dict[system_id][DPA_LOCATION] = dpa_location
        system_dict[system_id][DPA_PROGRESS] = dpa_progress
        # Copying over System.ingress/egress to new Systems.source/destination fields as-is
        system_dict[system_id][SOURCE] = json.dumps(row["ingress"])
        system_dict[system_id][DESTINATION] = json.dumps(row["egress"])
        # Making dataset references on the system an empty list here for now, so we have a starting value,
        # even if the system doesn't have any privacy declarations in the next step
        system_dict[system_id][
            DATASET_REFERENCES
        ] = []

    privacy_declaration_query: TextClause = text(
        """
        SELECT 
            id,
            system_id,
            dataset_references
        FROM privacydeclaration;
        """
    )
    for row in bind.execute(privacy_declaration_query):
        # Consolidating all the dataset references across all of a System's Privacy Declarations into a single
        # System.dataset_references field.
        system_dict[row["system_id"]][
            DATASET_REFERENCES
        ] = _consolidate_privacy_declaration_dataset_references(
            system_dict[row["system_id"]].get(DATASET_REFERENCES),
            row["dataset_references"],
        )

    for system in system_dict:
        update_system_query: TextClause = text(
            """
                UPDATE ctl_systems
                SET 
                    joint_controller_info = :joint_controller_info,
                    does_international_transfers = :does_international_transfers,
                    responsibility = :responsibility,
                    requires_data_protection_assessments = :requires_data_protection_assessments,
                    dpa_location = :dpa_location,
                    dpa_progress = :dpa_progress,
                    source = :source,
                    destination = :destination,
                    dataset_references = :dataset_references
                WHERE id = :id;
            """
        )

        system_data: Dict[str, Any] = system_dict[system]
        bind.execute(
            update_system_query,
            {"id": system, **system_data},
        )


# Casing is changing
legal_basis_for_processing_map: Dict = {
    "Consent": "Consent",
    "Contract": "Contract",
    "Legal Obligation": "Legal obligations",
    "Legal obligations": "Legal obligations",
    "Vital Interest": "Vital interests",
    "Vital interests": "Vital interests",
    "Public Interest": "Public interest",
    "Legitimate Interests": "Legitimate interests",
    "Legitimate interests": "Legitimate interests",
}

# Language is changing
special_category_map: Dict = {
    "Consent": "Explicit consent",
    "Employment": "Employment, social security and social protection",
    "Vital Interests": "Vital interests",
    "Non-profit Bodies": "Not-for-profit bodies",
    "Public by Data Subject": "Made public by the data subject",
    "Legal Claims": "Legal claims or judicial acts",
    "Substantial Public Interest": "Reasons of substantial public interest (with a basis in law)",
    "Medical": "Health or social care (with a basis in law)",
    "Public Health Interest": "Public health (with a basis in law)",
}


def _get_privacy_declaration_legal_basis_for_processing(
    data_use_legal_basis: Optional[str],
    legitimate_interest_impact_assessment: Optional[str],
) -> Optional[str]:
    """Use DataUse.legal_basis or DataUse.legitimate_interest_impact_assessment to set the value of
    PrivacyDeclaration.legal_basis_for_processing """
    if legitimate_interest_impact_assessment:
        return "Legitimate interests"
    if data_use_legal_basis:
        return legal_basis_for_processing_map.get(data_use_legal_basis, None)
    return None


def _get_third_party_data(
    recipients: Optional[List[str]],
) -> Tuple[bool, Optional[str]]:
    """Migrate data from DataUse.recipients field to new PrivacyDeclaration.third_parties and PrivacyDeclaration.data_shared_with_third_parties
     be true
     """
    data_shared_with_third_parties: bool = False
    third_parties: Optional[str] = None

    if recipients:
        data_shared_with_third_parties = True

        third_parties = ""
        for i, recipient in enumerate(recipients):
            if i != 0:
                third_parties += " "
            third_parties += recipient

    return data_shared_with_third_parties, third_parties


def privacy_declaration_additive_migration(bind: Connection):
    """Migrate existing data to new Privacy Declaration fields"""
    privacy_declaration_dict: Dict = defaultdict(lambda: {})
    get_privacy_declarations_query: TextClause = text(
        """
        SELECT 
            privacydeclaration.id,
            legal_basis,
            legitimate_interest_impact_assessment,
            special_category,
            recipients
        FROM privacydeclaration, ctl_data_uses
        WHERE privacydeclaration.data_use = ctl_data_uses.fides_key;
        """
    )
    for row in bind.execute(get_privacy_declarations_query):
        privacy_declaration_id: str = row["id"]
        privacy_declaration_dict[privacy_declaration_id][
            LEGAL_BASIS_FOR_PROCESSING
        ] = _get_privacy_declaration_legal_basis_for_processing(
            row["legal_basis"], row["legitimate_interest_impact_assessment"]
        )
        privacy_declaration_dict[privacy_declaration_id][
            IMPACT_ASSESSMENT_LOCATION
        ] = row["legitimate_interest_impact_assessment"]
        privacy_declaration_dict[privacy_declaration_id][
            PROCESSES_SPECIAL_CATEGORY_DATA
        ] = bool(row["special_category"])
        privacy_declaration_dict[privacy_declaration_id][
            SPECIAL_CATEGORY_LEGAL_BASIS
        ] = special_category_map.get(row["special_category"], None)
        privacy_declaration_dict[privacy_declaration_id][
            SPECIAL_CATEGORY_LEGAL_BASIS
        ] = special_category_map.get(row["special_category"], None)

        data_shared_with_third_parties, third_parties = _get_third_party_data(
            row["recipients"]
        )
        privacy_declaration_dict[privacy_declaration_id][
            DATA_SHARED_WITH_THIRD_PARTIES
        ] = data_shared_with_third_parties
        privacy_declaration_dict[privacy_declaration_id][THIRD_PARTIES] = third_parties

    for privacy_declaration in privacy_declaration_dict:
        update_privacy_declarations_query: TextClause = text(
            """
                UPDATE privacydeclaration
                SET 
                    legal_basis_for_processing = :legal_basis_for_processing,
                    impact_assessment_location = :impact_assessment_location,
                    processes_special_category_data = :processes_special_category_data,
                    special_category_legal_basis = :special_category_legal_basis,
                    data_shared_with_third_parties = :data_shared_with_third_parties,
                    third_parties = :third_parties
                WHERE id = :id;
            """
        )

        bind.execute(
            update_privacy_declarations_query,
            {
                "id": privacy_declaration,
                **privacy_declaration_dict[privacy_declaration],
            },
        )


def upgrade():
    bind: Connection = op.get_bind()
    bind.execute(text("DROP AGGREGATE IF EXISTS array_accum(anyarray);"))
    bind.execute(
        text(
            """
            CREATE AGGREGATE array_accum (anyarray)
            (
                sfunc = array_cat,
                stype = anyarray,
                initcond = '{}'
            );  
             """
        )
    )
    system_dictionary_additive_migration(bind)
    privacy_declaration_additive_migration(bind)


def downgrade():
    pass
