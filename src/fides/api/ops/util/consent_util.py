from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from fides.api.ctl.sql_models import System  # type: ignore[attr-defined]
from fides.api.ops.models.connectionconfig import ConnectionConfig
from fides.api.ops.models.privacy_notice import EnforcementLevel
from fides.api.ops.models.privacy_preference import (
    PrivacyPreferenceHistory,
    UserConsentPreference,
)
from fides.api.ops.models.privacy_request import ExecutionLogStatus, PrivacyRequest


def filter_privacy_preferences_for_propagation(
    system: Optional[System], privacy_preferences: List[PrivacyPreferenceHistory]
) -> List[PrivacyPreferenceHistory]:
    """Filter privacy preferences on a privacy request to just the ones that should be considered for third party
    consent propagation"""

    propagatable_preferences: List[PrivacyPreferenceHistory] = [
        pref
        for pref in privacy_preferences
        if pref.privacy_notice_history.enforcement_level == EnforcementLevel.system_wide
        and pref.preference != UserConsentPreference.acknowledge
    ]

    if not system:
        return propagatable_preferences

    filtered_on_use: List[PrivacyPreferenceHistory] = []
    for pref in propagatable_preferences:
        if pref.privacy_notice_history.applies_to_system(system):
            filtered_on_use.append(pref)
    return filtered_on_use


def should_opt_in_to_service(
    system: Optional[System], privacy_request: PrivacyRequest
) -> Tuple[Optional[bool], List[PrivacyPreferenceHistory]]:
    """
    For SaaS Connectors, examine the Privacy Preferences and collapse this information into a single should we opt in? (True),
    should we opt out? (False) or should we do nothing? (None).

    Email connectors should instead call "filter_privacy_preferences_for_propagation" directly, since we can have preferences with
    conflicting opt in/opt out values for those connector types.

    Also return filtered preferences here so we can cache affected systems and/or secondary identifiers directly on these
    filtered preferences for consent reporting.

    - If using the old workflow (privacyrequest.consent_preferences), return True if all attached consent preferences
    are opt in, otherwise False.  System check is ignored.

    - If using the new workflow (privacyrequest.privacy_preferences), there is more filtering here.  Privacy Preferences
    must have an enforcement level of system-wide and a data use must match a system data use.  If the connector is
    orphaned (no system), skip the data use check. If conflicts, prefer the opt-out preference.
    """

    # OLD WORKFLOW
    if privacy_request.consent_preferences:
        return (
            all(
                consent_pref["opt_in"]
                for consent_pref in privacy_request.consent_preferences
            ),
            [],  # Don't need to return the filtered preferences, this is just relevant for the new workflow
        )

    # NEW WORKFLOW
    relevant_preferences = filter_privacy_preferences_for_propagation(
        system, privacy_request.privacy_preferences
    )
    if not relevant_preferences:
        return None, []  # We should do nothing here

    # Collapse relevant preferences into whether we should opt-in or opt-out
    preference_to_propagate: UserConsentPreference = (
        UserConsentPreference.opt_out
        if any(
            filtered_pref.preference == UserConsentPreference.opt_out
            for filtered_pref in relevant_preferences
        )
        else UserConsentPreference.opt_in
    )

    # Hopefully rare final filtering in case there are conflicting preferences
    filtered_preferences: List[PrivacyPreferenceHistory] = [
        pref
        for pref in relevant_preferences
        if pref.preference == preference_to_propagate
    ]

    # Return whether we should opt in, and the filtered preferences so we can update those for consent reporting
    return preference_to_propagate == UserConsentPreference.opt_in, filtered_preferences


def cache_initial_status_and_identities_for_consent_reporting(
    db: Session,
    privacy_request: PrivacyRequest,
    connection_config: ConnectionConfig,
    relevant_preferences: List[PrivacyPreferenceHistory],
    relevant_user_identities: Dict[str, Any],
) -> None:
    """Add a pending system status and cache relevant identities on the applicable PrivacyPreferenceHistory
    records for consent reporting.

    Preferences that aren't relevant for the given system/connector are given a skipped status.

    Typically used when *some* but not all privacy preferences are relevant.  Otherwise,
    other methods just mark all the preferences as skipped.
    """
    for pref in privacy_request.privacy_preferences:
        if pref in relevant_preferences:
            pref.update_secondary_user_ids(db, relevant_user_identities)
            pref.cache_system_status(
                db, connection_config.system_key, ExecutionLogStatus.pending
            )
        else:
            pref.cache_system_status(
                db, connection_config.system_key, ExecutionLogStatus.skipped
            )


def add_complete_system_status_for_consent_reporting(
    db: Session,
    privacy_request: PrivacyRequest,
    connection_config: ConnectionConfig,
) -> None:
    """Cache a complete system status for consent reporting on just the subset
    of preferences that were deemed relevant for the connector on failure

    Deeming them relevant if they already had a "pending" log added to them.
    """
    for pref in privacy_request.privacy_preferences:
        if (
            pref.affected_system_status
            and pref.affected_system_status.get(connection_config.system_key)
            == ExecutionLogStatus.pending.value
        ):
            pref.cache_system_status(
                db,
                connection_config.system_key,
                ExecutionLogStatus.complete,
            )


def add_errored_system_status_for_consent_reporting(
    db: Session,
    privacy_request: PrivacyRequest,
    connection_config: ConnectionConfig,
) -> None:
    """Cache an errored system status for consent reporting on just the subset
    of preferences that were deemed relevant for the connector on failure

    Deeming them relevant if they already had a "pending" log added to them.
    """
    for pref in privacy_request.privacy_preferences:
        if (
            pref.affected_system_status
            and pref.affected_system_status.get(connection_config.system_key)
            == ExecutionLogStatus.pending.value
        ):
            pref.cache_system_status(
                db,
                connection_config.system_key,
                ExecutionLogStatus.error,
            )
