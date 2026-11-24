# 13 — Code quality on your PC: SonarQube + JaCoCo

## 1. What are we implementing?

A local code-quality check you run **before you push**, so the CI/CD pipeline is not the first place
where problems show up:

```
 sonarqube/docker-compose.yml  (start once, leave running)     product-app/pom.xml  (runs in every build)
┌──────────────────────────────────────────┐        ┌─────────────────────────────────────────────────────┐
│ sonarqube      sonarqube:26.11...community│◄───────│ mvn clean verify sonar:sonar                        │
│                http://localhost:9000      │ upload │  1. tests run with the JaCoCo agent attached        │
│                rules, dashboard, history  │ report │  2. jacoco:report -> target/site/jacoco/index.html  │
│      │ JDBC                               │        │                    target/site/jacoco/jacoco.xml    │
│      ▼                                    │        │  3. jacoco:check  -> FAIL if line coverage < 80 %   │
│ sonarqube-db   postgres:17.12-alpine      │───────►│  4. sonar:sonar   -> analyse code + jacoco.xml,     │
│                (no host port)             │  gate  │                      wait for the Quality Gate      │
└──────────────────────────────────────────┘ result └─────────────────────────────────────────────────────┘
```

| Tool | What it does | Where it runs |
|---|---|---|
| **JaCoCo** | Measures which lines and branches your tests execute (test coverage) | Inside Maven, as a plugin. **Not a container** (see below) |
| **SonarQube** | Finds bugs, vulnerabilities, code smells, duplicated code and hard-coded secrets; shows coverage; decides pass/fail with a *Quality Gate* | Docker container, http://localhost:9000 |
| **PostgreSQL** | SonarQube's own database (projects, issues, users, tokens, history) | Docker container, internal only |

**Why JaCoCo is not a container.** JaCoCo is a Java agent: it has to run *inside the JVM that runs your
tests*, where it records every line that is executed. There is no JaCoCo server to start. The
`jacoco-maven-plugin` attaches the agent during `mvn test` and turns the result into a report. SonarQube
(the container) then **reads** that report. So: SonarQube in Docker Compose, JaCoCo in `pom.xml`.

## 2. Why do we need it?

- **Faster feedback.** A failed check on your PC takes a minute; a failed pipeline costs a push, a wait and
  a fix-up commit.
- **Coverage you can see.** JaCoCo's HTML report colours every line green (tested), yellow (some branches
  tested) or red (never executed), so you know exactly which test is missing.
- **Issues explained.** Every SonarQube issue links to a rule page that says why it is a problem and how
  to fix it. This is a good way to learn Java best practices.
- **The same rules as CI.** The settings live in `pom.xml`, so a pipeline runs exactly the same checks
  (section 10).
- **Free and private.** SonarQube Community Build runs on your PC; your code never leaves it.

## 3. How does it work?

### JaCoCo (three goals in `pom.xml`)

1. **`prepare-agent`** runs before the tests. It sets the Maven property `argLine` to
   `-javaagent:...org.jacoco.agent-0.8.16-runtime.jar=destfile=...target/jacoco.exec`. Surefire (the
   plugin that runs tests) passes `argLine` to the test JVM, so the agent records every executed line
   into `target/jacoco.exec`.

   The test JVM also gets a second agent, **Mockito's**. Surefire is configured with
   `<argLine>@{argLine} "-javaagent:${org.mockito:mockito-core:jar}"</argLine>`: `@{argLine}` is
   replaced with JaCoCo's value just before the tests start, then Mockito's agent is added after it.
   `dependency:properties` provides the Mockito jar path. Loading Mockito at JVM start removes the
   *"Mockito is currently self-attaching"* and *"A Java agent has been loaded dynamically"* warnings.
   It also keeps the tests working on future JDKs, which will block agents that attach themselves later.
   If you ever replace Surefire's `<argLine>`, keep `@{argLine}` in it; otherwise coverage drops to 0 %.
2. **`report`** runs right after the tests (we bound it to the `test` phase, so even `mvn test` writes it).
   It combines `jacoco.exec` with the compiled classes and writes:
   - `target/site/jacoco/index.html`: the report for you (open it in a browser);
   - `target/site/jacoco/jacoco.xml`: the report for SonarQube;
   - `target/site/jacoco/jacoco.csv`: the same numbers as a spreadsheet.
3. **`check`** runs in the `verify` phase. If **line coverage of the whole app is below 80 %**, the build
   fails with `Coverage checks have not been met`.

`ProductAppApplication` (only `main()`) is excluded from coverage in both JaCoCo and SonarQube.

### SonarQube

1. `mvn sonar:sonar` starts the **SonarScanner for Maven**. It logs in with your token, asks the server
   which rules to use (the *Quality Profile*, default **"Sonar way core"**) and downloads the analysers.
   The first time, it also downloads a Java runtime for the scanner engine (cached in `~/.sonar/cache`).
2. The scanner analyses `src/main/java` and `pom.xml`, and the test code in `src/test/java` separately
   (16 files in this project). It also scans them for hard-coded secrets such as passwords or AWS keys.
   It imports `jacoco.xml` for coverage and `target/surefire-reports` for test results.
3. It uploads one compressed report. The server's **Compute Engine** processes it in the background and
   updates the dashboard.
4. Because `sonar.qualitygate.wait=true`, the scanner waits for the **Quality Gate** and **fails the
   Maven build** if the gate fails.

The default Quality Gate **"Sonar way"** checks only **new code**, meaning code changed since the first
analysis of the current version (`<version>1.0.0</version>` in `pom.xml`):

| Condition on new code | Fails when |
|---|---|
| Issues | more than 0 new issues |
| Security hotspots reviewed | less than 100 % |
| Coverage | less than 80 % |
| Duplicated lines | more than 3 % |

This is why the gate is called "Clean as You Code": you never have to fix old code before you can push,
but everything you add must be clean.

## 4. Which configuration files are involved?

| File | Purpose |
|---|---|
| `sonarqube/docker-compose.yml` | SonarQube + PostgreSQL containers, health checks, named volumes |
| `sonarqube/.env.example` → `sonarqube/.env` | Database user/password for SonarQube's PostgreSQL, host port (default 9000) |
| `product-app/pom.xml` | JaCoCo plugin (3 goals), coverage minimum, Sonar plugin version, `sonar.*` settings |
| `product-app/.env` → `SONAR_TOKEN=` (or a `SONAR_TOKEN` Windows variable) | Your SonarQube login token. Only in the git-ignored `.env`, **never** in `pom.xml`, a script or a commit |
| `product-app/sonar-scan.cmd` / `sonar-scan.sh` | Read `SONAR_TOKEN` from `.env`, then run `mvn clean verify sonar:sonar` |
| `product-app/target/site/jacoco/` | Generated reports (`index.html`, `jacoco.xml`, `jacoco.csv`) |

The settings in `pom.xml`:

| Property | Value | Meaning |
|---|---|---|
| `jacoco.version` | `0.8.16` | JaCoCo plugin version |
| `sonar-maven-plugin.version` | `5.9.0.7382` | SonarScanner for Maven version |
| `jacoco.minimum.line.coverage` | `0.80` | `mvn verify` fails below 80 % line coverage |
| `sonar.host.url` | `http://localhost:9000` | Which SonarQube server to send the analysis to |
| `sonar.projectKey` | `product-app` | Project name in SonarQube (created automatically on the first analysis) |
| `sonar.coverage.jacoco.xmlReportPaths` | `${project.build.directory}/site/jacoco/jacoco.xml` | Where SonarQube finds the coverage |
| `sonar.coverage.exclusions` | `**/ProductAppApplication.java` | Same exclusion as JaCoCo |
| `sonar.qualitygate.wait` | `true` | Fail the Maven build when the Quality Gate fails |

Each of them can be overridden for one run with `-D`, for example `-Djacoco.minimum.line.coverage=0.90`.

## 5. What commands should I execute?

### Step 1 — Start SonarQube (Docker Desktop must be running)

```bash
cd sonarqube
cp .env.example .env            # first time only. PowerShell: Copy-Item .env.example .env
docker compose up -d --wait     # returns when SonarQube is healthy (about 1 minute)
```

SonarQube uses about **2.5 GB of RAM**. Stop it with `docker compose stop` when you are done for the day.

### Step 2 — First login (first time only)

1. Open http://localhost:9000.
2. Log in with **admin / admin**.
3. SonarQube forces you to set a new password: at least 12 characters with upper case, lower case,
   a digit and a special character. Keep it in your password manager.

You do **not** need to create the project in the UI: the first analysis creates `product-app` automatically.

### Step 3 — Create an analysis token (first time only)

1. Click your avatar (top right) → **My Account** → **Security**.
2. Under *Generate Tokens*: Name `local-dev`, Type **Global Analysis Token**, Expires in **90 days**.
3. Click **Generate** and copy the token (it starts with `sqa_`). It is shown **only once**.

A token is a password. Do not put it in `pom.xml`, a script, a chat, or a commit. The only file it may
go in is `product-app/.env` (Step 4, option A).

### Step 4 — Save the token (first time only)

The scanner reads the token from the `SONAR_TOKEN` environment variable. Pick **one** of two places to keep it.

#### Option A (recommended): in `product-app/.env`, for this project only

1. Open `product-app/.env` and paste the token after `SONAR_TOKEN=`, with no spaces and no quotes:

   ```ini
   SONAR_TOKEN=sqa_paste_your_token_here
   ```

2. Run the scan with the script instead of plain `mvn` (Step 5). The script reads the token from `.env`
   and hands it to Maven only while it runs:

   ```bash
   .\sonar-scan.cmd        # PowerShell or cmd
   ./sonar-scan.sh         # Git Bash
   ```

No terminal or VS Code restart is needed.

Why this is safe here: `.env` is in `.gitignore` (never committed) and in `.dockerignore` (never sent to
a Docker build). The Dockerfile copies only `pom.xml` and `src/`, and `docker-compose.yml` passes only the
variables it names to the containers, so the token never reaches the app. Plain `mvn` does **not** read
`.env`, which is why the script exists.

#### Option B: a Windows user variable, for every project

```powershell
[Environment]::SetEnvironmentVariable("SONAR_TOKEN", "sqa_paste_your_token_here", "User")
```

Then **close and reopen** your terminals. Restart VS Code completely, because its terminals only see
variables that existed when VS Code started. Git Bash sees the variable too. Plain `mvn ... sonar:sonar`
then works in any project.

Check it (PowerShell: `$env:SONAR_TOKEN.Substring(0,4)`, Git Bash: `echo ${SONAR_TOKEN:0:4}`): it prints `sqa_`.

For the current terminal only: PowerShell `$env:SONAR_TOKEN = "sqa_..."`, Git Bash `export SONAR_TOKEN=sqa_...`.

If you set both, the scripts use the value from `.env`. An empty `SONAR_TOKEN=` in `.env` falls back to option B.

### Step 5 — Run the checks (every time, before you push)

All commands run in `product-app/`. The integration test starts MySQL with Testcontainers, so Docker
must be running.

| Goal | Command | Time |
|---|---|---|
| Tests + coverage report | `mvn test` | ≈ 30 s |
| Tests + coverage report + **coverage check** | `mvn verify` | ≈ 35 s |
| **Everything**: tests, coverage, coverage check, SonarQube, Quality Gate (token in `.env`, option A) | `.\sonar-scan.cmd` (Git Bash: `./sonar-scan.sh`) | ≈ 50 s |
| Same, token in a Windows variable (option B) | `mvn clean verify sonar:sonar` | ≈ 50 s |
| Only re-send to SonarQube (after a build, tests not re-run) | Option A: `.\sonar-scan.cmd sonar:sonar`, option B: `mvn sonar:sonar` | ≈ 20 s |

The scripts pass any arguments you give them straight to Maven. Without arguments they run
`clean verify sonar:sonar`.

The first run takes longer while Maven downloads the plugins and Testcontainers pulls `mysql:8.0.46`.
After you **removed or disabled a test**, add `clean` (`mvn clean test`). Otherwise JaCoCo adds the new run
to the old coverage data, and the report still counts the lines the removed test used to cover.

### Step 6 — Look at the results

| What | How |
|---|---|
| Coverage report | `start target/site/jacoco/index.html` (PowerShell and Git Bash). Click a package, then a class, to see the coloured lines |
| SonarQube dashboard | http://localhost:9000/dashboard?id=product-app (the link is also printed at the end of the Maven output) |
| Issues list | Dashboard → **Issues** tab. Click an issue to see the line and the rule explanation |
| Coverage per file in SonarQube | Dashboard → **Measures** → *Coverage* |

### Everyday SonarQube commands (in `sonarqube/`)

| Task | Command |
|---|---|
| Start (and wait until healthy) | `docker compose up -d --wait` |
| Status | `docker compose ps` |
| Is it ready? | `curl http://localhost:9000/api/system/status` → `"status":"UP"` |
| Follow the logs | `docker compose logs -f sonarqube` |
| Stop (keep projects, users, tokens, history) | `docker compose stop` |
| Remove containers (keep data) | `docker compose down` |
| **Reset everything** (back to admin/admin, all history lost) | `docker compose down -v` |
| Memory use | `docker stats --no-stream sonarqube sonarqube-db` |

### Useful one-off variations

```bash
mvn verify -Djacoco.minimum.line.coverage=0.90        # stricter coverage check, this run only
mvn sonar:sonar -Dsonar.qualitygate.wait=false        # send the analysis, but don't fail on a red gate
mvn sonar:sonar -Dsonar.host.url=http://localhost:9001  # if you changed SONAR_HOST_PORT in sonarqube/.env
mvn verify -DskipTests                                # NO coverage: tests are skipped, so JaCoCo has no data
```

## 6. What output should I expect?

`docker compose up -d --wait` (first start):

```
 Volume sonarqube_postgres_data  Created
 Volume sonarqube_data  Created
 ...
 Container sonarqube-db  Healthy
 Container sonarqube  Started
 Container sonarqube  Healthy
```

`docker compose ps`:

```
NAME           IMAGE                                STATUS                    PORTS
sonarqube      sonarqube:26.11.0.134175-community   Up 36 seconds (healthy)   0.0.0.0:9000->9000/tcp
sonarqube-db   postgres:17.12-alpine                Up 46 seconds (healthy)   5432/tcp
```

`curl http://localhost:9000/api/system/status`:

```json
{"id":"...","version":"26.11.0.134175","status":"UP"}
```

`docker compose logs sonarqube` ends with `SonarQube is operational`. The warning
*Default Administrator credentials are still being used* disappears after step 2.

`mvn clean verify sonar:sonar` (the important lines, in order):

```
[INFO] --- jacoco:0.8.16:prepare-agent (prepare-agent) @ product-app ---
[INFO] argLine set to "-javaagent:C:\\Users\\<you>\\.m2\\repository\\org\\jacoco\\org.jacoco.agent\\0.8.16\\org.jacoco.agent-0.8.16-runtime.jar=destfile=...\\product-app\\target\\jacoco.exec"
...
[INFO] Tests run: 17, Failures: 0, Errors: 0, Skipped: 0
[INFO] --- jacoco:0.8.16:report (report) @ product-app ---
[INFO] Analyzed bundle 'product-app' with 10 classes
...
[INFO] --- jacoco:0.8.16:check (check) @ product-app ---
[INFO] All coverage checks have been met.
...
[INFO] Communicating with SonarQube Community Build 26.11.0.134175
[INFO]   Excluded sources for coverage: **/ProductAppApplication.java
[INFO] 16 files indexed (done) | time=9ms
[INFO] Quality profile for java: Sonar way core
[INFO] Sensor JaCoCo XML Report Importer [jacoco]
[INFO] Importing 1 report(s). Turn your logs in debug mode in order to see the exhaustive list.
...
[INFO] ------------- Check Quality Gate status
[INFO] Waiting for the analysis report to be processed (max 300s)
[INFO] QUALITY GATE STATUS: PASSED - View details on http://localhost:9000/dashboard?id=product-app
[INFO] BUILD SUCCESS
```

Two warnings are expected while this folder is **not a Git repository**. They go away once the code is in Git:

```
[WARNING] SCM provider autodetection failed. Please use "sonar.scm.provider" to define SCM of your project ...
[WARNING] Retrieving only language associated files, make sure to run the analysis inside a git repository ...
```

The SonarQube dashboard for this project (measured on 2026-11-24):

| Measure | Value |
|---|---|
| Quality Gate | **Passed** |
| Coverage | **100 %** (line 100 %, branch 100 %) |
| Unit tests | 17 |
| Reliability (bugs) | 0 · rating A |
| Security (vulnerabilities) | 0 · rating A |
| Maintainability (code smells) | 0 · rating A |
| Security hotspots | 0 |
| Duplications | 0.0 % |
| Lines of code | 599 |

The JaCoCo report (`index.html`) shows the same 100 %: all 114 lines in 10 classes are green.

The last 3 lines to turn green were the two "safety net" handlers in `GlobalExceptionHandler`. Two tests in
`ProductControllerTest` now cover them:

| Test | Handler it covers | What it checks |
|---|---|---|
| `unknownUrl_returns404WithJsonError` | `handleNoResource` (404, line 66) | `GET /api/unknown` returns the standard JSON error with *No endpoint found for GET /api/unknown* |
| `unexpectedError_returns500WithoutLeakingDetails` | `handleUnexpected` (500, lines 72-73) | When the service throws, the client gets *An unexpected error occurred* and **not** the internal exception text |

The second test prints an `ERROR ... Unexpected error on GET /api/products` log with a stack trace. That is
expected: the handler logs every unexpected error on purpose, and the test triggers one.

## 7. How can I verify it?

Make each check fail on purpose, so you know it really protects you.

### Exercise 1 — the coverage check fails

Run only the 6 service unit tests (`-Dtest=...`), as if the controller tests did not exist. Keep the `clean`
(section 8 explains why):

```bash
mvn clean verify -Dtest=ProductServiceTest
```

Expected:

```
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0
[WARNING] Rule violated for bundle product-app: lines covered ratio is 0.50, but expected minimum is 0.80
[INFO] BUILD FAILURE
[ERROR] Failed to execute goal org.jacoco:jacoco-maven-plugin:0.8.16:check (check) on project product-app: Coverage checks have not been met. See log for details.
```

All 6 tests pass, but half of the code is never executed, so the build still fails. Run `mvn clean verify`
afterwards to get the full report back.

### Exercise 2 — SonarQube finds a new issue and the Quality Gate fails

The default profile *Sonar way core* is short (263 Java rules). To see more, switch the project to
**Sonar way comprehensive** (608 rules): open the project → **Project Settings** → **Quality Profiles** →
Java → **Change profile** → *Sonar way comprehensive*.

Then add one bad line to `ProductService.delete(...)`:

```java
System.out.println("Deleted product " + id);   // temporary, for the exercise
```

and run `mvn compile sonar:sonar`. Expected:

```
[INFO] Quality profile for java: Sonar way comprehensive
[ERROR] QUALITY GATE STATUS: FAILED - View details on http://localhost:9000/dashboard?id=product-app
[INFO] BUILD FAILURE
```

The dashboard shows the failed gate condition *New issues* with value 1: `java:S106` *Replace this use of
System.out by a logger* (Maintainability, Medium). Apart from it the project is clean under this profile too.

> **Why "new code" matters.** When an issue is found in code that already existed (for example because you
> switched to a bigger profile), SonarQube lists it but it does **not** fail the gate. On 2026-11-24 the
> comprehensive profile found 5 such Low issues here, and they were fixed the same day:
> `java:S1710` ×4 (`ProductController`: repeat `@ApiResponse` directly instead of wrapping the annotations in
> `@ApiResponses({...})`) and `java:S6068` ×1 (`ProductControllerTest`: `delete(1L)` instead of `delete(eq(1L))`).

**Remove the line again** and run `mvn compile sonar:sonar`: the gate is back to `PASSED`.

### Exercise 3 — watch one line turn red

1. In `ProductControllerTest`, put `@Disabled` (from `org.junit.jupiter.api.Disabled`) above
   `unknownUrl_returns404WithJsonError`.
2. Run `mvn clean test` and open `target/site/jacoco/index.html` → `com.example.productapp.exception` →
   `GlobalExceptionHandler`. Line 66 (`handleNoResource`) is **red**: no other test calls an unknown URL.
   The 404 in the integration test is a different handler (*product* not found).
3. Remove `@Disabled`, run `mvn clean test` again: the line is green and coverage is back to 100 %.

## 8. Common errors and solutions

| Symptom | Cause | Solution |
|---|---|---|
| `HTTP 401 Unauthorized. Please check the property sonar.token or the environment variable SONAR_TOKEN` | Token missing, mistyped, expired or revoked; plain `mvn` used with the token only in `.env`; or the terminal started before you set the Windows variable | Option A: check `SONAR_TOKEN=` in `product-app/.env` and run `.\sonar-scan.cmd`, not `mvn`. Option B: open a new terminal or restart VS Code. Generate a new token if it expired |
| `ERROR: SONAR_TOKEN is empty. Paste your token into ...\.env` | The script found no token in `.env` and no Windows variable | Paste the token after `SONAR_TOKEN=` in `product-app/.env` (Step 4) |
| `Connection refused` / `Failed to query server version` (no 401) | SonarQube not running or still starting | `cd sonarqube; docker compose up -d --wait`; `docker compose logs sonarqube` |
| `error: Set SONAR_DB_PASSWORD in the .env file` | `sonarqube/.env` missing | `cp .env.example .env` in `sonarqube/` |
| `Bind for 0.0.0.0:9000 failed: port is already allocated` | Another program uses 9000 | Set `SONAR_HOST_PORT=9001` in `sonarqube/.env`, and add `-Dsonar.host.url=http://localhost:9001` to the `mvn` command (or change it in `pom.xml`) |
| `QUALITY GATE STATUS: FAILED` | New code has issues, too little coverage or duplication | Open the printed link and fix what the gate lists. To only report: `-Dsonar.qualitygate.wait=false` |
| `Coverage checks have not been met` | Line coverage dropped under 80 % | Open `index.html`, find the red lines, add tests. Lowering the minimum is a team decision, not a fix |
| Coverage does not go down after you removed or disabled tests | JaCoCo **appends** to `target/jacoco.exec`, so the lines covered by the earlier run still count | Add `clean`: `mvn clean test` / `mvn clean verify` |
| Coverage is 0.0 % in SonarQube | You ran `sonar:sonar` without running tests first, or with `-DskipTests` | Use `mvn clean verify sonar:sonar` |
| `Skipping JaCoCo execution due to missing execution data file` | Tests were skipped, so no `jacoco.exec` exists | Run without `-DskipTests` |
| `Could not find a valid Docker environment` during tests | Docker Desktop is not running (Testcontainers needs it) | Start Docker Desktop |
| SonarQube log: `max virtual memory areas vm.max_map_count [65530] is too low` | The Docker Desktop VM uses a low kernel limit (not the case on this PC: 262144 works) | `wsl -d docker-desktop sysctl -w vm.max_map_count=524288`, then `docker compose up -d` again. Repeat after a Docker Desktop restart |
| `sonarqube` container exits with code 137 | Out of memory | Give Docker Desktop at least 4 GB (Settings → Resources), stop other stacks |
| `password authentication failed for user "sonar"` | `SONAR_DB_PASSWORD` changed after the database volume was created | Put the old password back, or `docker compose down -v` (deletes SonarQube data) |
| Forgot the SonarQube admin password | — | `docker compose down -v` then `up -d --wait` resets to admin/admin (all history is lost) |

## 9. Optional: see issues while you type (SonarQube for IDE)

Install the VS Code extension **SonarQube for IDE** (`SonarSource.sonarlint-vscode`). It underlines issues
in the editor as you type. In its *Connected Mode* settings, add a SonarQube Server connection to
`http://localhost:9000` with a **User token** and bind the folder to project `product-app`. The editor
then uses exactly the same Quality Profile as your local SonarQube.

## 10. The same checks in the CI/CD pipeline

Everything is configured in `pom.xml`, so a pipeline needs only the server URL and a token from its own
credential store. Nothing about your local setup has to change.

`jenkins/Jenkinsfile` has the two stages **Tests + JaCoCo coverage** and **SonarQube analysis + Quality
Gate**. Run them on their own with `STEP = code-quality`; step 06 also runs them before it builds the
image. Setup and expected output: [doc 11, section 2.4](11-jenkins-terraform-step-by-step.md#24-sonarqube-token-for-the-code-quality-stages)
and [Code quality step](11-jenkins-terraform-step-by-step.md#code-quality-step-code-quality). The core of it:

```groovy
sh MAVEN_FN + 'mvn clean verify'                       // tests + JaCoCo + 80 % check
withCredentials([string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN')]) {
    sh MAVEN_FN + 'mvn sonar:sonar -Dsonar.host.url="$RUN_SONAR_HOST_URL"'   // waits for the Quality Gate
}
```

`MAVEN_FN` runs Maven in the `maven` Docker image, and the build page shows the test results, a JaCoCo
coverage view, and the same JaCoCo HTML report you open locally.

If your company already runs a SonarQube server, ask which **Quality Profile** and **Quality Gate** it
uses. Select the same ones in your local SonarQube, and a green local run means a green pipeline.
