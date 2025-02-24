/**
 * This file is responsible for all TCF specific logic. It does not get bundled in with
 * vanilla fides-js, since all of its actions are very TCF specific.
 *
 * In the future, this should hold interactions with the CMP API as well as string generation.
 */

import { CmpApi, TCData } from "@iabtechlabtcf/cmpapi";
import { TCModel, TCString, GVL } from "@iabtechlabtcf/core";
import { makeStub } from "./tcf/stub";

import { EnabledIds } from "./tcf/types";
import {
  decodeVendorId,
  vendorIsAc,
  vendorGvlEntry,
  uniqueGvlVendorIds,
} from "./tcf/vendors";
import { PrivacyExperience } from "./consent-types";
import { FIDES_SEPARATOR } from "./tcf/constants";
import { FidesEvent } from "./events";

// TCF
const CMP_ID = 407;
const CMP_VERSION = 1;
const FORBIDDEN_LEGITIMATE_INTEREST_PURPOSE_IDS = [1, 3, 4, 5, 6];

// AC
const AC_SPECIFICATION_VERSION = 1;

/**
 * Generate an AC String based on TCF-related info from privacy experience.
 */
const generateAcString = ({
  tcStringPreferences,
}: {
  tcStringPreferences: Pick<EnabledIds, "vendorsConsent" | "vendorsLegint">;
}) => {
  const uniqueIds = Array.from(
    new Set(
      [
        ...tcStringPreferences.vendorsConsent,
        ...tcStringPreferences.vendorsLegint,
      ]
        .filter((id) => vendorIsAc(id))
        // Convert gacp.42 --> 42
        .map((id) => decodeVendorId(id).id)
    )
  );
  const vendorIds = uniqueIds.sort((a, b) => Number(a) - Number(b)).join(".");

  return `${AC_SPECIFICATION_VERSION}~${vendorIds}`;
};

/**
 * Generate FidesString based on TCF and AC-related info from privacy experience.
 * Called when there is either a FidesInitialized or FidesUpdated event
 */
export const generateFidesString = async ({
  experience,
  tcStringPreferences,
}: {
  tcStringPreferences?: EnabledIds;
  experience: PrivacyExperience;
}): Promise<string> => {
  let encodedString = "";
  try {
    const tcModel = new TCModel(new GVL(experience.gvl));

    // Some fields will not be populated until a GVL is loaded
    await tcModel.gvl.readyPromise;

    tcModel.cmpId = CMP_ID;
    tcModel.cmpVersion = CMP_VERSION;
    tcModel.consentScreen = 1; // todo- On which 'screen' consent was captured; this is a CMP proprietary number encoded into the TC string

    // Narrow the GVL to say we've only showed these vendors provided by our experience
    tcModel.gvl.narrowVendorsTo(uniqueGvlVendorIds(experience));

    if (tcStringPreferences) {
      // Set vendors on tcModel
      tcStringPreferences.vendorsConsent.forEach((vendorId) => {
        if (vendorGvlEntry(vendorId, experience.gvl)) {
          const { id } = decodeVendorId(vendorId);
          tcModel.vendorConsents.set(+id);
        }
      });
      tcStringPreferences.vendorsLegint.forEach((vendorId) => {
        if (vendorGvlEntry(vendorId, experience.gvl)) {
          const thisVendor = experience.tcf_vendor_legitimate_interests?.filter(
            (v) => v.id === vendorId
          )[0];

          const vendorPurposes = thisVendor?.purpose_legitimate_interests;
          // Handle the case where a vendor has forbidden legint purposes set
          let skipSetLegInt = false;
          if (vendorPurposes) {
            const legIntPurposeIds = vendorPurposes.map((p) => p.id);
            if (
              legIntPurposeIds.filter((id) =>
                FORBIDDEN_LEGITIMATE_INTEREST_PURPOSE_IDS.includes(id)
              ).length
            ) {
              skipSetLegInt = true;
            }
            if (!skipSetLegInt) {
              const { id } = decodeVendorId(vendorId);
              tcModel.vendorLegitimateInterests.set(+id);
            }
          }
        }
      });

      // Set purposes on tcModel
      tcStringPreferences.purposesConsent.forEach((purposeId) => {
        tcModel.purposeConsents.set(+purposeId);
      });
      tcStringPreferences.purposesLegint.forEach((purposeId) => {
        const id = +purposeId;
        if (!FORBIDDEN_LEGITIMATE_INTEREST_PURPOSE_IDS.includes(id)) {
          tcModel.purposeLegitimateInterests.set(id);
        }
      });

      // Set special feature opt-ins on tcModel
      tcStringPreferences.specialFeatures.forEach((id) => {
        tcModel.specialFeatureOptins.set(+id);
      });

      // note that we cannot set consent for special purposes nor features because the IAB policy states
      // the user is not given choice by a CMP.
      // See https://iabeurope.eu/iab-europe-transparency-consent-framework-policies/
      // and https://github.com/InteractiveAdvertisingBureau/iabtcf-es/issues/63#issuecomment-581798996
      encodedString = TCString.encode(tcModel);

      // Attach the AC string
      const acString = generateAcString({ tcStringPreferences });
      encodedString = `${encodedString}${FIDES_SEPARATOR}${acString}`;
    }
  } catch (e) {
    // eslint-disable-next-line no-console
    console.error("Unable to instantiate GVL: ", e);
    return Promise.resolve("");
  }
  return Promise.resolve(encodedString);
};

/**
 * Extract just the TC string from a FidesEvent. This will also remove parts of the
 * TC string that we do not want to surface with our CMP API events, such as
 * `vendors_disclosed` and our own AC string addition.
 */
const fidesEventToTcString = (event: FidesEvent) => {
  const { fides_string: cookieString } = event.detail;
  if (cookieString) {
    // Remove the AC portion which is separated by FIDES_SEPARATOR
    const [tcString] = cookieString.split(FIDES_SEPARATOR);
    // We only want to return the first part of the tcString, which is separated by '.'
    // This means Publisher TC is not sent either, which is okay for now since we do not set it.
    // However, if we do one day set it, we would have to decode the string and encode it again
    // without vendorsDisclosed
    return tcString.split(".")[0];
  }
  return cookieString;
};

/**
 * Initializes the CMP API, including setting up listeners on FidesEvents to update
 * the CMP API accordingly.
 */
export const initializeCmpApi = () => {
  makeStub();
  const isServiceSpecific = true; // TODO: determine this from the backend?
  const cmpApi = new CmpApi(CMP_ID, CMP_VERSION, isServiceSpecific, {
    // Add custom command to support adding `addtlConsent` per AC spec
    getTCData: (next, tcData: TCData, status) => {
      /*
       * If using with 'removeEventListener' command, add a check to see if tcData is not a boolean. */
      if (typeof tcData !== "boolean") {
        const stringSplit = window.Fides.fides_string?.split(FIDES_SEPARATOR);
        const addtlConsent = stringSplit?.length === 2 ? stringSplit[1] : "";
        next({ ...tcData, addtlConsent }, status);
        return;
      }

      // pass data and status along
      next(tcData, status);
    },
  });

  // `null` value indicates that GDPR does not apply
  // Initialize api with TC str, we don't yet show UI, so we use false
  // see https://github.com/InteractiveAdvertisingBureau/iabtcf-es/tree/master/modules/cmpapi#dont-show-ui--tc-string-does-not-need-an-update
  window.addEventListener("FidesInitialized", (event) => {
    const tcString = fidesEventToTcString(event);
    cmpApi.update(tcString ?? null, false);
  });
  // UI is visible
  // see https://github.com/InteractiveAdvertisingBureau/iabtcf-es/tree/master/modules/cmpapi#show-ui--tc-string-needs-update
  // and https://github.com/InteractiveAdvertisingBureau/iabtcf-es/tree/master/modules/cmpapi#show-ui--new-user--no-tc-string
  window.addEventListener("FidesUIShown", (event) => {
    const tcString = fidesEventToTcString(event);
    cmpApi.update(tcString ?? null, true);
  });
  // UI is no longer visible
  // see https://github.com/InteractiveAdvertisingBureau/iabtcf-es/tree/master/modules/cmpapi#dont-show-ui--tc-string-does-not-need-an-update
  window.addEventListener("FidesModalClosed", (event) => {
    const tcString = fidesEventToTcString(event);
    cmpApi.update(tcString ?? null, false);
  });
  // User preference collected
  // see https://github.com/InteractiveAdvertisingBureau/iabtcf-es/tree/master/modules/cmpapi#show-ui--tc-string-needs-update
  window.addEventListener("FidesUpdated", (event) => {
    const tcString = fidesEventToTcString(event);
    cmpApi.update(tcString ?? null, false);
  });
};
