# QA Agent — one-time setup

The QA agent expects three secrets in Secret Manager and one IAM grant
on its service account. Everything below is a one-shot — do it once,
forget about it. Subsequent deploys via `./deploy.sh qa-agent` pick up
the existing secrets automatically.

## 1. Test user UID

The agent authenticates as the dedicated test account
`duser8531@gmail.com`. Look up its UID once:

```bash
gcloud auth login --account=cvsubs@gmail.com
gcloud config set project college-counselling-478115

# UID lookup via Firebase Admin (one-shot from your laptop):
python3 - <<'EOF'
import firebase_admin
from firebase_admin import auth
firebase_admin.initialize_app()
print(auth.get_user_by_email("duser8531@gmail.com").uid)
EOF
```

Take the printed UID and stash it as a Secret Manager secret:

```bash
echo -n "<UID_FROM_ABOVE>" | gcloud secrets create qa-test-user-uid \
    --replication-policy=automatic \
    --data-file=-
```

## 2. QA admin token

The agent requires `X-Admin-Token` on every `/run` request. The same
token is the second gate on `profile_manager_v2`'s `/clear-test-data`
endpoint, so the same value goes into both env configurations.

Generate a fresh random token and stash it:

```bash
TOKEN="$(openssl rand -hex 32)"
echo -n "$TOKEN" | gcloud secrets create qa-admin-token \
    --replication-policy=automatic \
    --data-file=-
echo "TOKEN (save this — it's the X-Admin-Token for manual triggers): $TOKEN"
```

`profile_manager_v2` reads the same secret via the existing env
plumbing — add `--set-secrets="QA_ADMIN_TOKEN=qa-admin-token:latest"`
to its deploy block in `deploy.sh` (next to the existing
`--set-secrets` line, if any), or set it via the console.

## 3. Firebase web API key

Custom-token → ID-token exchange uses the project's Firebase web API
key (the same one the frontend uses, exposed as `VITE_FIREBASE_API_KEY`).
Find it in the Firebase Console → Project Settings → General → Web API
Key and stash it:

```bash
echo -n "<WEB_API_KEY>" | gcloud secrets create firebase-web-api-key \
    --replication-policy=automatic \
    --data-file=-
```

## 4. Service account permissions

The function deploys with a service account that needs:

- `iam.serviceAccountTokenCreator` on **itself** (so it can mint
  custom tokens).
- `secretmanager.secretAccessor` on the three secrets above.
- Read + write on Firestore (default for App Engine SA already; if
  using a custom SA, grant `datastore.user`).

```bash
SA="qa-agent@${PROJECT_ID}.iam.gserviceaccount.com"

# Self-grant for token creation
gcloud iam service-accounts add-iam-policy-binding $SA \
    --member="serviceAccount:$SA" \
    --role="roles/iam.serviceAccountTokenCreator"

# Secret access
for SECRET in qa-admin-token qa-test-user-uid firebase-web-api-key; do
    gcloud secrets add-iam-policy-binding $SECRET \
        --member="serviceAccount:$SA" \
        --role="roles/secretmanager.secretAccessor"
done

# Firestore
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA" \
    --role="roles/datastore.user"
```

If the `qa-agent` SA doesn't exist yet, create it first:

```bash
gcloud iam service-accounts create qa-agent --display-name="QA Agent"
```

Then in `deploy.sh` add `--service-account=qa-agent@$PROJECT_ID.iam.gserviceaccount.com`
to the `gcloud functions deploy qa-agent` block. (Default omitted from
the snippet so you can iterate without hard-coding the project ID.)

## 5. Cloud Scheduler (daily run)

Once the function is deployed, point Cloud Scheduler at it:

```bash
QA_URL="$(gcloud functions describe qa-agent --region=us-east1 --gen2 --format='value(serviceConfig.uri)')"

gcloud scheduler jobs create http qa-agent-daily \
    --location=us-east1 \
    --schedule="0 6 * * *" \
    --time-zone="America/Los_Angeles" \
    --uri="${QA_URL}/run" \
    --http-method=POST \
    --headers="Content-Type=application/json,X-Admin-Token=$(gcloud secrets versions access latest --secret=qa-admin-token)" \
    --message-body='{"trigger":"schedule","actor":"scheduler"}' \
    --oidc-service-account-email=qa-agent@${PROJECT_ID}.iam.gserviceaccount.com
```

## 6. Manual trigger from your laptop

Once the agent is live:

```bash
QA_URL="$(gcloud functions describe qa-agent --region=us-east1 --gen2 --format='value(serviceConfig.uri)')"
TOKEN="$(gcloud secrets versions access latest --secret=qa-admin-token)"

# Run a fresh batch
curl -X POST "${QA_URL}/run" \
    -H "Content-Type: application/json" \
    -H "X-Admin-Token: $TOKEN" \
    -d '{"trigger":"manual","actor":"cvsubs@gmail.com"}'

# Run a single archetype
curl -X POST "${QA_URL}/run" \
    -H "Content-Type: application/json" \
    -H "X-Admin-Token: $TOKEN" \
    -d '{"trigger":"manual","scenario":"junior_spring_5school"}'
```

Reports land in Firestore at `qa_runs/<run_id>`. The admin UI for
browsing them ships in a follow-up PR.

## 7. Rotating the admin token

When you want to rotate:

```bash
NEW="$(openssl rand -hex 32)"
echo -n "$NEW" | gcloud secrets versions add qa-admin-token --data-file=-
# Redeploy both functions to pick up the new latest version:
./deploy.sh qa-agent
./deploy.sh profile-v2
```
