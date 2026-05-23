// GCP Secret Manager helper for the autonomous QA loop.
//
// Per docs/qa-autonomous-loop-spec.md:
// - Fetch the test password from STRATIA_TEST_PASSWORD at runtime.
// - NEVER log, print, cache to disk, screenshot, or include in errors/issues.
// - Fail loudly on retrieval errors; do NOT fall back to prompting or hardcoded values.

import { SecretManagerServiceClient } from '@google-cloud/secret-manager';

const GCP_PROJECT_ID = 'college-counselling-478115';
const SECRET_NAME = 'STRATIA_TEST_PASSWORD';

let client = null;

function getClient() {
  if (!client) {
    client = new SecretManagerServiceClient();
  }
  return client;
}

/**
 * Fetch the Stratia test-user password from GCP Secret Manager.
 * Returns the plaintext password string in memory only. Never persists.
 *
 * Throws on any access failure (no fallback, no prompt).
 */
export async function getTestPassword() {
  const name = `projects/${GCP_PROJECT_ID}/secrets/${SECRET_NAME}/versions/latest`;
  try {
    const [version] = await getClient().accessSecretVersion({ name });
    const payload = version.payload?.data?.toString('utf8');
    if (!payload) {
      throw new Error('Secret payload is empty');
    }
    return payload;
  } catch (err) {
    // Re-throw with a sanitized message — never include the raw secret value
    // even if the payload partially leaked through.
    throw new Error(
      `Failed to access ${SECRET_NAME} from Secret Manager in ${GCP_PROJECT_ID}: ` +
        `${err.message || err.code || 'unknown error'}. ` +
        `Ensure ADC is configured (gcloud auth application-default login as cvsubs@gmail.com) ` +
        `or a service account with roles/secretmanager.secretAccessor is attached.`,
    );
  }
}

/**
 * Quickly verify the secret is accessible without retrieving the value.
 * Useful as a pre-flight check before spec runs.
 *
 * Returns true on success; throws on failure (matching getTestPassword).
 */
export async function verifySecretAccess() {
  // We still need to call accessSecretVersion to confirm access (no separate "metadata-only" call
  // exists for a specific version). The value is fetched into memory and immediately discarded.
  await getTestPassword();
  return true;
}
