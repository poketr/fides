/**
 * Fides.js: Javascript library for Fides (https://github.com/ethyca/fides)
 *
 * This JS module provides easy access to interact with Fides from a webpage, including the ability to:
 * - initialize the page with default consent options (e.g. opt-out of advertising cookies, opt-in to analytics, etc.)
 * - read/write the current user's consent preferences to their browser as a cookie
 * - push the current user's consent preferences to other systems via integrations (Google Tag Manager, Meta, etc.)
 *
 * See https://fid.es for more information!
 *
 * Basic usage of this module in an HTML page is:
 * ```
 * <script src="https://privacy.{company}.com/fides.js"></script>
 * <script>
 *   window.Fides.init({
 *     consent: {
 *       options: [{
 *         cookieKeys: ["data_sales"],
 *         default: true,
 *         fidesDataUseKey: "advertising"
 *       }]
 *     },
 *     experience: {},
 *     geolocation: {},
 *     options: {
 *           debug: true,
 *           isDisabled: false,
 *           isGeolocationEnabled: false,
 *           geolocationApiUrl: "",
 *           overlayParentId: null,
 *           privacyCenterUrl: "http://localhost:3000"
 *         }
 *   });
 * </script>
 * ```
 *
 * ...and later:
 * ```
 * <script>
 *   // Query user consent preferences
 *   if (window.Fides.consent.data_sales) {
 *     // ...enable advertising scripts
 *   }
 * ```
 */
import { gtm } from "./integrations/gtm";
import { meta } from "./integrations/meta";
import { shopify } from "./integrations/shopify";
import { getConsentContext } from "./lib/consent-context";
import { initOverlay } from "./lib/consent";
import {
  CookieKeyConsent,
  CookieIdentity,
  CookieMeta,
  getOrMakeFidesCookie,
  makeConsentDefaultsLegacy,
  buildCookieConsentForExperiences,
} from "./lib/cookie";
import {
  PrivacyExperience,
  FidesConfig,
  FidesOptions,
  UserGeolocation,
  ComponentType,
} from "./lib/consent-types";
import {
  constructFidesRegionString,
  debugLog,
  validateOptions,
} from "./lib/consent-utils";
import { fetchExperience } from "./services/fides/api";
import { getGeolocation } from "./services/external/geolocation";
import { OverlayProps } from "~/components/Overlay";

export type Fides = {
  consent: CookieKeyConsent;
  experience?: PrivacyExperience;
  geolocation?: UserGeolocation;
  options: FidesOptions;
  fides_meta: CookieMeta;
  gtm: typeof gtm;
  identity: CookieIdentity;
  init: typeof init;
  initialized: boolean;
  meta: typeof meta;
  shopify: typeof shopify;
};

declare global {
  interface Window {
    Fides: Fides;
  }
}

// The global Fides object; this is bound to window.Fides if available
// eslint-disable-next-line no-underscore-dangle,@typescript-eslint/naming-convention
let _Fides: Fides;

const retrieveEffectiveRegionString = async (
  geolocation: UserGeolocation | undefined,
  options: FidesOptions
) => {
  // Prefer the provided geolocation if available and valid; otherwise, fallback to automatically
  // geolocating the user by calling the geolocation API
  const fidesRegionString = constructFidesRegionString(geolocation);
  if (!fidesRegionString) {
    // we always need a region str so that we can PATCH privacy preferences to Fides Api
    return constructFidesRegionString(
      // Call the geolocation API
      await getGeolocation(
        options.isGeolocationEnabled,
        options.geolocationApiUrl,
        options.debug
      )
    );
  }
  return fidesRegionString;
};

/**
 * Determines whether experience is valid and relevant notices exist within the experience
 */
const experienceIsValid = (
  effectiveExperience: PrivacyExperience | undefined | null,
  options: FidesOptions
): boolean => {
  if (!effectiveExperience) {
    debugLog(
      options.debug,
      `No relevant experience found. Skipping overlay initialization.`
    );
    return false;
  }
  if (
    !(
      effectiveExperience.privacy_notices &&
      effectiveExperience.privacy_notices.length >= 0
    )
  ) {
    debugLog(
      options.debug,
      `No relevant notices in the privacy experience. Skipping overlay initialization.`,
      effectiveExperience
    );
    return false;
  }
  if (effectiveExperience.component !== ComponentType.OVERLAY) {
    debugLog(
      options.debug,
      "No experience found with overlay component. Skipping overlay initialization."
    );
    return false;
  }
  if (!effectiveExperience.experience_config) {
    debugLog(
      options.debug,
      "No experience config found with for experience. Skipping overlay initialization."
    );
    return false;
  }
  return true;
};

/**
 * Initialize the global Fides object with the given configuration values
 */
const init = async ({
  consent,
  experience,
  geolocation,
  options,
}: FidesConfig) => {
  // Configure the default legacy consent values
  const context = getConsentContext();
  const consentDefaults = makeConsentDefaultsLegacy(
    consent,
    context,
    options.debug
  );

  // Load any existing user preferences from the browser cookie
  const cookie = getOrMakeFidesCookie(consentDefaults, options.debug);

  let shouldInitOverlay: boolean = !options.isOverlayDisabled;

  if (!validateOptions(options)) {
    debugLog(
      options.debug,
      "Invalid overlay options. Skipping overlay initialization.",
      options
    );
    shouldInitOverlay = false;
  }

  const fidesRegionString = await retrieveEffectiveRegionString(
    geolocation,
    options
  );
  let effectiveExperience: PrivacyExperience | undefined | null = experience;

  if (!fidesRegionString) {
    debugLog(
      options.debug,
      `User location could not be obtained. Skipping overlay initialization.`
    );
    shouldInitOverlay = false;
  } else if (!effectiveExperience) {
    effectiveExperience = await fetchExperience(
      fidesRegionString,
      options.fidesApiUrl,
      cookie.identity.fides_user_device_id,
      options.debug
    );
  }

  if (effectiveExperience && experienceIsValid(effectiveExperience, options)) {
    // Overwrite cookie consent with experience-based consent values
    cookie.consent = buildCookieConsentForExperiences(
      effectiveExperience,
      context,
      options.debug
    );

    if (shouldInitOverlay) {
      // Check if there are any notices within the experience that do not have a user preference
      const noticesWithNoUserPreferenceExist: boolean = Boolean(
        effectiveExperience?.privacy_notices?.some(
          (notice) => notice.current_preference == null
        )
      );
      if (noticesWithNoUserPreferenceExist) {
        await initOverlay(<OverlayProps>{
          experience: effectiveExperience,
          fidesRegionString,
          cookie,
          options,
        }).catch(() => {});
      }
    }
  }

  // Initialize the window.Fides object
  _Fides.consent = cookie.consent;
  _Fides.fides_meta = cookie.fides_meta;
  _Fides.identity = cookie.identity;
  _Fides.experience = experience;
  _Fides.geolocation = geolocation;
  _Fides.options = options;
  _Fides.initialized = true;

  if (getConsentContext().globalPrivacyControl) {
    effectiveExperience?.privacy_notices?.forEach((notice) => {
      if (notice.has_gpc_flag) {
        // todo- write cookie with user preference
        // todo- send consent request downstream automatically with saveUserPreference()
      }
    });
  }
};

// The global Fides object; this is bound to window.Fides if available
_Fides = {
  consent: {},
  experience: undefined,
  geolocation: {},
  options: {
    debug: true,
    isOverlayDisabled: true,
    isGeolocationEnabled: false,
    geolocationApiUrl: "",
    overlayParentId: null,
    privacyCenterUrl: "",
    fidesApiUrl: "",
  },
  fides_meta: {},
  identity: {},
  gtm,
  init,
  initialized: false,
  meta,
  shopify,
};

if (typeof window !== "undefined") {
  window.Fides = _Fides;
}

// Export everything from ./lib/* to use when importing fides.mjs as a module
// TODO: pretty sure we need ./services/* too?
export * from "./lib/consent";
export * from "./components";
export * from "./lib/consent-context";
export * from "./lib/consent-types";
export * from "./lib/consent-links";
export * from "./lib/consent-utils";
export * from "./lib/consent-value";
export * from "./lib/cookie";

// DEFER: this default export isn't very useful, it's just the Fides type
export default Fides;
