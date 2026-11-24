#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# One-time Jenkins setup for the step-by-step AWS pipeline (run it in Git Bash).
#
#   1. Stores the AWS keys of an AWS CLI profile in Jenkins as the credential
#      "aws-mani-dev" (kind "Username with password": username = access key ID,
#      password = secret access key). Jenkins encrypts it and masks it in logs.
#   2. Creates (or updates) the pipeline job "product-app-aws-terraform" from
#      jenkins/Jenkinsfile.
#   3. With --sonar-token: stores a SonarQube analysis token as the credential
#      "sonar-token" (kind "Secret text"), used by STEP = code-quality and step 06.
#
#   ./scripts/jenkins-setup.sh                 # 1 + 2
#   ./scripts/jenkins-setup.sh --job-only      # only 2: update the job after editing the Jenkinsfile
#   ./scripts/jenkins-setup.sh --sonar-token   # 3 + 2
#
# Settings (environment variables, all optional):
#   JENKINS_URL       default http://localhost:8090
#   JENKINS_USER      asked if missing
#   JENKINS_PASSWORD  asked (hidden) if missing
#   AWS_CLI_PROFILE   AWS CLI profile whose keys go to Jenkins, default "default" (IAM user mani-dev)
#   CREDENTIAL_ID     default aws-mani-dev
#   JOB_NAME          default product-app-aws-terraform
#   SONAR_URL         SonarQube as seen from your PC, default http://localhost:9000 (only to check the token)
#   SONAR_CREDENTIAL_ID      default sonar-token
#   SONAR_TOKEN_FOR_JENKINS  asked (hidden) if missing; Enter = SONAR_TOKEN from product-app/.env
#
# Secrets never appear on a command line or in the output: curl reads them from a
# private config file in a temporary folder that is deleted when the script ends.
# -----------------------------------------------------------------------------
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
JENKINS_URL="${JENKINS_URL:-http://localhost:8090}"
AWS_CLI_PROFILE="${AWS_CLI_PROFILE:-default}"
CREDENTIAL_ID="${CREDENTIAL_ID:-aws-mani-dev}"
JOB_NAME="${JOB_NAME:-product-app-aws-terraform}"
SONAR_URL="${SONAR_URL:-http://localhost:9000}"
SONAR_CREDENTIAL_ID="${SONAR_CREDENTIAL_ID:-sonar-token}"
MODE="${1:-all}"
case "$MODE" in
    all|--job-only|--sonar-token) ;;
    *) printf 'Unknown option: %s (use --job-only or --sonar-token)\n' "$MODE" >&2; exit 1 ;;
esac

TMP="$(mktemp -d)"; chmod 700 "$TMP"; trap 'rm -rf "$TMP"' EXIT
die() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }
# Git Bash's curl is a Windows program: give it Windows-style paths
native() { if command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else printf '%s' "$1"; fi; }
b64() { printf '%s' "$1" | base64 | tr -d '\n\r'; }
cq() { local s=${1//\\/\\\\}; s=${s//\"/\\\"}; printf '"%s"' "$s"; }   # quote for a curl config file

# ---- Jenkins login ----------------------------------------------------------
[ -n "${JENKINS_USER:-}" ] || read -rp "Jenkins user name: " JENKINS_USER
[ -n "${JENKINS_PASSWORD:-}" ] || { read -rsp "Jenkins password (hidden): " JENKINS_PASSWORD; echo; }
printf 'user = %s\n' "$(cq "$JENKINS_USER:$JENKINS_PASSWORD")" > "$TMP/auth.cfg"
: > "$TMP/cookies"
jcurl() { curl -sS -K "$(native "$TMP/auth.cfg")" -b "$(native "$TMP/cookies")" -c "$(native "$TMP/cookies")" "$@"; }

[ "$(jcurl -o /dev/null -w '%{http_code}' "$JENKINS_URL/whoAmI/api/json")" = 200 ] \
    || die "Jenkins at $JENKINS_URL rejects this user name / password."
echo "Jenkins: logged in to $JENKINS_URL as $JENKINS_USER"

# CSRF protection: every POST needs a "crumb" from the same session (cookie)
CRUMB="$(jcurl "$JENKINS_URL/crumbIssuer/api/json" \
         | sed -n 's/.*"crumb":"\([^"]*\)".*"crumbRequestField":"\([^"]*\)".*/\2: \1/p')"
[ -n "$CRUMB" ] || die "Jenkins did not return a CSRF crumb."

# ---- 1. AWS credential ------------------------------------------------------
if [ "$MODE" = all ]; then
    KEY_ID="$(aws configure get aws_access_key_id --profile "$AWS_CLI_PROFILE" || true)"
    SECRET="$(aws configure get aws_secret_access_key --profile "$AWS_CLI_PROFILE" || true)"
    [ -n "$KEY_ID" ] && [ -n "$SECRET" ] || die "AWS CLI profile '$AWS_CLI_PROFILE' has no access keys (run: aws configure)."
    ARN="$(aws sts get-caller-identity --profile "$AWS_CLI_PROFILE" --query Arn --output text)" \
        || die "AWS rejects the keys of profile '$AWS_CLI_PROFILE'."
    echo "AWS: profile '$AWS_CLI_PROFILE' is $ARN"

    cat > "$TMP/credential.groovy" <<GROOVY
import com.cloudbees.plugins.credentials.CredentialsScope
import com.cloudbees.plugins.credentials.SystemCredentialsProvider
import com.cloudbees.plugins.credentials.domains.Domain
import com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl
def d = { String s -> new String(Base64.decoder.decode(s), 'UTF-8') }
def store = SystemCredentialsProvider.instance.store
def domain = Domain.global()
def c = new UsernamePasswordCredentialsImpl(CredentialsScope.GLOBAL, '$CREDENTIAL_ID',
        d('$(b64 "AWS keys of $ARN (product-app Terraform pipeline)")'), d('$(b64 "$KEY_ID")'), d('$(b64 "$SECRET")'))
c.usernameSecret = true   // mask the access key ID in build logs as well
def old = store.getCredentials(domain).find { it.id == c.id }
if (old) { store.updateCredentials(domain, old, c); println "credential '\${c.id}': updated" }
else     { store.addCredentials(domain, c);         println "credential '\${c.id}': added" }
GROOVY
    printf 'header = %s\ndata-urlencode = %s\n' "$(cq "$CRUMB")" "$(cq "script@$(native "$TMP/credential.groovy")")" > "$TMP/post.cfg"
    OUT="$(jcurl -K "$(native "$TMP/post.cfg")" "$JENKINS_URL/scriptText")"
    rm -f "$TMP/credential.groovy" "$TMP/post.cfg"
    echo "Jenkins: $OUT"
    [[ "$OUT" == *"credential '$CREDENTIAL_ID'"* ]] || die "Jenkins did not store the credential."
fi

# ---- 3. SonarQube token (only with --sonar-token) ---------------------------
if [ "$MODE" = --sonar-token ]; then
    echo "Tip: give Jenkins its own token (SonarQube > My Account > Security: name 'jenkins',"
    echo "     type Global Analysis Token). Then you can revoke it without breaking your own scans."
    if [ -z "${SONAR_TOKEN_FOR_JENKINS:-}" ]; then
        read -rsp "SonarQube token for Jenkins (hidden; Enter = SONAR_TOKEN from product-app/.env): " SONAR_TOKEN_FOR_JENKINS
        echo
    fi
    if [ -z "$SONAR_TOKEN_FOR_JENKINS" ] && [ -f "$ROOT/product-app/.env" ]; then
        SONAR_TOKEN_FOR_JENKINS="$(grep -E '^SONAR_TOKEN=' "$ROOT/product-app/.env" | tail -n 1 | cut -d= -f2- | tr -d "\r\"'" || true)"
        [ -z "$SONAR_TOKEN_FOR_JENKINS" ] || echo "SonarQube: using SONAR_TOKEN from product-app/.env"
    fi
    [ -n "$SONAR_TOKEN_FOR_JENKINS" ] || die "No SonarQube token given."

    # Check the token with SonarQube before Jenkins stores it (the token is the user name, no password)
    printf 'user = %s\n' "$(cq "$SONAR_TOKEN_FOR_JENKINS:")" > "$TMP/sonar.cfg"
    VALID="$(curl -sS -K "$(native "$TMP/sonar.cfg")" "$SONAR_URL/api/authentication/validate" || true)"
    rm -f "$TMP/sonar.cfg"
    [[ "$VALID" == *'"valid":true'* ]] \
        || die "SonarQube at $SONAR_URL does not accept this token (SonarQube not running, or token mistyped/revoked)."
    echo "SonarQube: token accepted by $SONAR_URL"

    cat > "$TMP/sonar.groovy" <<GROOVY
import com.cloudbees.plugins.credentials.CredentialsScope
import com.cloudbees.plugins.credentials.SystemCredentialsProvider
import com.cloudbees.plugins.credentials.domains.Domain
import org.jenkinsci.plugins.plaincredentials.impl.StringCredentialsImpl
import hudson.util.Secret
def d = { String s -> new String(Base64.decoder.decode(s), 'UTF-8') }
def store = SystemCredentialsProvider.instance.store
def domain = Domain.global()
def c = new StringCredentialsImpl(CredentialsScope.GLOBAL, '$SONAR_CREDENTIAL_ID',
        'SonarQube analysis token (product-app code quality)', Secret.fromString(d('$(b64 "$SONAR_TOKEN_FOR_JENKINS")')))
def old = store.getCredentials(domain).find { it.id == c.id }
if (old) { store.updateCredentials(domain, old, c); println "credential '\${c.id}': updated" }
else     { store.addCredentials(domain, c);         println "credential '\${c.id}': added" }
GROOVY
    printf 'header = %s\ndata-urlencode = %s\n' "$(cq "$CRUMB")" "$(cq "script@$(native "$TMP/sonar.groovy")")" > "$TMP/post.cfg"
    OUT="$(jcurl -K "$(native "$TMP/post.cfg")" "$JENKINS_URL/scriptText")"
    rm -f "$TMP/sonar.groovy" "$TMP/post.cfg"
    echo "Jenkins: $OUT"
    [[ "$OUT" == *"credential '$SONAR_CREDENTIAL_ID'"* ]] || die "Jenkins did not store the SonarQube credential."
fi

# ---- 2. Pipeline job --------------------------------------------------------
JENKINSFILE="$ROOT/jenkins/Jenkinsfile"
[ -f "$JENKINSFILE" ] || die "$JENKINSFILE not found."
{
    cat <<'XML'
<?xml version='1.1' encoding='UTF-8'?>
<flow-definition plugin="workflow-job">
  <description>product-app: create the AWS infrastructure one step at a time with Terraform (docs/11), and STEP code-quality: tests, JaCoCo coverage, SonarQube Quality Gate (docs/13). Pipeline source: jenkins/Jenkinsfile (update with scripts/jenkins-setup.sh --job-only).</description>
  <keepDependencies>false</keepDependencies>
  <properties/>
  <definition class="org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition" plugin="workflow-cps">
    <script>
XML
    sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g' "$JENKINSFILE"
    cat <<'XML'
</script>
    <sandbox>true</sandbox>
  </definition>
  <disabled>false</disabled>
</flow-definition>
XML
} > "$TMP/config.xml"

printf 'header = %s\nheader = "Content-Type: application/xml"\n' "$(cq "$CRUMB")" > "$TMP/xml.cfg"
if [ "$(jcurl -o /dev/null -w '%{http_code}' "$JENKINS_URL/job/$JOB_NAME/api/json")" = 200 ]; then
    URL="$JENKINS_URL/job/$JOB_NAME/config.xml"; WHAT=updated
else
    URL="$JENKINS_URL/createItem?name=$JOB_NAME"; WHAT=created
fi
CODE="$(jcurl -K "$(native "$TMP/xml.cfg")" -o "$TMP/resp.txt" -w '%{http_code}' -X POST --data-binary "@$(native "$TMP/config.xml")" "$URL")"
[ "$CODE" = 200 ] || { cat "$TMP/resp.txt" >&2; die "Jenkins answered HTTP $CODE while saving the job."; }
echo "Jenkins: job '$JOB_NAME' $WHAT -> $JENKINS_URL/job/$JOB_NAME/"
echo
if [ "$MODE" = --sonar-token ]; then
    echo "Next: open the job, click 'Build with Parameters', STEP = code-quality."
else
    echo "Next: open the job, click 'Build with Parameters', STEP = 00-preflight."
fi
echo "(The very first build of a new job runs with the default parameters, which is 00-preflight / plan.)"
