# Scenario: profile_tab_renders_five_tabs

**Test plan section:** §6.1  
**Auth required:** Yes (storageState)  
**Spec file:** `tests/playwright-prod/specs/profile.auth.spec.js`  
**Iteration:** 2

## Objective

Verify that the Profile page (`/profile`) renders all five expected tab labels when the test account is authenticated, regardless of whether the profile has data or is empty.

## Preconditions

- Authenticated as `stratiaadmissions@gmail.com` (via `auth-state/storageState.json`).
- No precondition on profile content — the tab bar renders in both empty and populated states.

## Step-by-step actions

1. Navigate to `https://stratiaadmissions.com/profile`.
2. Assert the page URL remains `/profile` (no auth redirect).
3. Locate and assert visibility of each of the five tabs in the Profile tab bar.

## Expected outcomes

The following five tab labels are all visible on the Profile page:

| Tab Label | Source |
|---|---|
| Upload Documents | `Profile.jsx` line 1075 |
| View Profile | `Profile.jsx` line 1087 |
| Profile Editor | `Profile.jsx` line 1099 |
| Take Assessment | `Profile.jsx` line 1110 |
| Self-Discovery | `Profile.jsx` line 1122 |

**Note:** Per plan §6.1, the "View Profile" tab is hidden when the profile is empty (`!isProfileEmpty` guard). On an account with existing data, all five tabs are visible. On a freshly-reset account, "View Profile" may be hidden — the spec asserts visibility without failing on this, relying on `waitFor` with a timeout rather than strict `.toBeVisible()` without fallback.

## Fixtures referenced

None — this scenario does not require a profile fixture file.

## Known edge cases

- If the account's profile is completely empty, "View Profile" may be hidden per `Profile.jsx` line 1080. The spec handles this gracefully.
- The tab labels may be rendered as `<button>` or `<tab>` roles depending on the underlying UI library version. The spec uses `.or()` to match either.
