#!/usr/bin/env bash
#
# One-shot QA agent provisioning. Run once (or whenever you want to
# rotate the admin token). Idempotent — safe to re-run; existing
# secrets/SAs are detected and skipped instead of erroring.
#
# Prereqs (you do these once before this script):
#   1. `gcloud auth login --account=cvsubs@gmail.com`
#   2. `gcloud auth application-default login --account=cvsubs@gmail.com`
#      (needed for the firebase-admin step that looks up the test UID)
#
# What this script does:
#   1. Look up the test user UID via firebase-admin
#   2. Create/refresh three Secret Manager secrets:
#        - qa-test-user-uid
#        - qa-admin-token  (newly minted; saved to a file you read once)
#        - firebase-web-api-key  (from your existing frontend/.env)
#   3. Create the qa-agent service account if missing
#   4. Grant it the IAM roles it needs
#   5. Deploy qa-agent via ./deploy.sh qa-agent
#   6. Redeploy profile-manager-v2 to pick up /clear-test-data
#   7. Print the manual-trigger command you can run

set -euo pipefail

# ---- Pinned project + account ----------------------------------------------
export CLOUDSDK_CORE_ACCOUNT="cvsubs@gmail.com"
export CLOUDSDK_CORE_PROJECT="college-counselling-478115"
PROJECT_ID="$CLOUDSDK_CORE_PROJECT"
REGION="us-east1"

GREEN="\033[0;32m"; YELLOW="\033[1;33m"; RED="\033[0;31m"; CYAN="\033[0;36m"; NC="\033[0m"
say() { printf "${CYAN}[setup]${NC} %s\n" "$*"; }
ok()  { printf "${GREEN}[ ok ]${NC} %s\n" "$*"; }
warn(){ printf "${YELLOW}[warn]${NC} %s\n" "$*"; }
die() { printf "${RED}[fail]${NC} %s\n" "$*"; exit 1; }

# ---- Locate repo root + frontend/.env --------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_ENV="$REPO_ROOT/frontend/.env"

[[ -f "$FRONTEND_ENV" ]] || die "frontend/.env not found at $FRONTEND_ENV — needed for VITE_FIREBASE_API_KEY"

# ---- 0. Sanity check on auth + project -------------------------------------
say "verifying auth + project"
gcloud auth list --filter="account:$CLOUDSDK_CORE_ACCOUNT" --format='value(account)' \
    | grep -q "$CLOUDSDK_CORE_ACCOUNT" \
    || die "$CLOUDSDK_CORE_ACCOUNT not authenticated. Run: gcloud auth login --account=$CLOUDSDK_CORE_ACCOUNT"

ADC_FILE="$HOME/.config/gcloud/application_default_credentials.json"
[[ -f "$ADC_FILE" ]] \
    || die "Application Default Credentials missing. Run: gcloud auth application-default login --account=$CLOUDSDK_CORE_ACCOUNT"

ok "auth ready"

# ---- 1. Look up test user UID via firebase-admin ---------------------------
TEST_USER_EMAIL="duser8531@gmail.com"
say "looking up Firebase UID for $TEST_USER_EMAIL"

# Try Python from a few known venvs; fall back to system python
PY="${PYTHON:-/tmp/college-expert-test-venv/bin/python}"
if ! [[ -x "$PY" ]]; then PY="$(command -v python3)"; fi

UID_VALUE="$("$PY" - <<EOF
import firebase_admin
from firebase_admin import auth
firebase_admin.initialize_app(options={'projectId': '$PROJECT_ID'})
print(auth.get_user_by_email('$TEST_USER_EMAIL').uid)
EOF
)"

[[ -n "$UID_VALUE" ]] || die "could not look up UID. Check that firebase-admin is installed and ADC is set up."
ok "UID = $UID_VALUE"

# ---- 2. Secret Manager ------------------------------------------------------
upsert_secret() {
    local name="$1" value="$2"
    if gcloud secrets describe "$name" >/dev/null 2>&1; then
        printf "%s" "$value" | gcloud secrets versions add "$name" --data-file=- >/dev/null
        ok "rotated secret: $name"
    else
        printf "%s" "$value" | gcloud secrets create "$name" \
            --replication-policy=automatic --data-file=- >/dev/null
        ok "created secret: $name"
    fi
}

# qa-test-user-uid
upsert_secret "qa-test-user-uid" "$UID_VALUE"

# qa-admin-token — generate fresh
ADMIN_TOKEN="$(openssl rand -hex 32)"
upsert_secret "qa-admin-token" "$ADMIN_TOKEN"

# firebase-web-api-key — pull from frontend/.env (one-shot)
WEB_API_KEY="$(grep -E '^VITE_FIREBASE_API_KEY=' "$FRONTEND_ENV" | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d '\r')"
[[ -n "$WEB_API_KEY" ]] || die "VITE_FIREBASE_API_KEY not found in $FRONTEND_ENV"
upsert_secret "firebase-web-api-key" "$WEB_API_KEY"

# ---- 3. Service account -----------------------------------------------------
SA_EMAIL="qa-agent@${PROJECT_ID}.iam.gserviceaccount.com"
if gcloud iam service-accounts describe "$SA_EMAIL" >/dev/null 2>&1; then
    ok "service account exists: $SA_EMAIL"
else
    say "creating service account $SA_EMAIL"
    gcloud iam service-accounts create qa-agent --display-name="QA Agent" >/dev/null
    ok "service account created"
fi

# ---- 4. IAM grants ----------------------------------------------------------
say "granting IAM roles to $SA_EMAIL"

# Token-creator on itself (so the SA can mint custom tokens for the test user)
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/iam.serviceAccountTokenCreator" >/dev/null

# Secret accessor for each secret
for SECRET in qa-admin-token qa-test-user-uid firebase-web-api-key; do
    gcloud secrets add-iam-policy-binding "$SECRET" \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/secretmanager.secretAccessor" >/dev/null
done

# Firestore read+write
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/datastore.user" >/dev/null --condition=None 2>/dev/null || \
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/datastore.user" >/dev/null

ok "IAM grants applied"

# ---- 5. Deploys -------------------------------------------------------------
say "deploying profile-manager-v2 (picks up /clear-test-data + QA_ADMIN_TOKEN secret)"
warn "This deploy script does not yet wire QA_ADMIN_TOKEN into profile-manager-v2."
warn "Add the following flag to the deploy_profile_manager_v2 block in deploy.sh,"
warn "next to its existing --set-secrets line, then re-run:"
warn "    --set-secrets='QA_ADMIN_TOKEN=qa-admin-token:latest'"
warn "(Or add QA_TEST_USER_EMAIL/QA_ADMIN_TOKEN as env vars if Secret Manager wiring isn't ready.)"

cd "$REPO_ROOT"
bash deploy.sh profile-v2

say "deploying qa-agent"
bash deploy.sh qa-agent

# ---- 6. Final summary -------------------------------------------------------
QA_URL="$(gcloud functions describe qa-agent --region=$REGION --gen2 --format='value(serviceConfig.uri)')"

cat <<INFO

${GREEN}═══════════════════════════════════════════════════════════════════${NC}
${GREEN}  QA Agent ready.${NC}
${GREEN}═══════════════════════════════════════════════════════════════════${NC}

  Function URL : $QA_URL
  Test user    : $TEST_USER_EMAIL  (UID: $UID_VALUE)
  Admin token  : stored as secret qa-admin-token (latest)

Trigger a run from this shell:

  scripts/qa_agent_run.sh                  # full batch
  scripts/qa_agent_run.sh <archetype-id>   # single scenario

Sample archetype IDs:
  freshman_fall_starter
  junior_spring_5school
  senior_fall_application_crunch
  all_uc_only

INFO
