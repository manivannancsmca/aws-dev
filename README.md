# product-app — Spring Boot + MySQL on AWS ECS Fargate with Terraform

A small but production-style **product management REST API**, built to learn the complete path
from local development to AWS:

```
Spring Boot 4 ──► Flyway ──► Swagger ──► Docker Compose ──► Amazon ECR ──► ECS Fargate + RDS MySQL (Terraform)
```

The **same Docker image** runs locally (Docker Compose) and on AWS (ECS Fargate). Only environment
variables change.

What runs on AWS once it is deployed, drawn by hand (the numbers are the build steps of
[doc 11](docs/11-jenkins-terraform-step-by-step.md)):

![The finished system on AWS: users, load balancer, ECS task, RDS MySQL, NAT gateway, ECR, Secrets Manager, CloudWatch Logs and IAM roles](docs/images/sketchbook-00b-big-picture.png)

## What is inside

| Area | Technology |
|---|---|
| Language / build | Java 25 (LTS), Maven 3.9 |
| Framework | Spring Boot 4.2 (Spring MVC, Spring Data JPA, Validation, Actuator) |
| Database | MySQL 8.0 locally (Docker Compose and the Testcontainers integration test); MySQL 8.4 on Amazon RDS |
| Schema migrations | Flyway (`src/main/resources/db/migration`) |
| API docs | Springdoc OpenAPI 3 + Swagger UI |
| Containers | Multi-stage Dockerfile, Docker Compose with health checks |
| Code quality (local) | JaCoCo test coverage (Maven plugin), SonarQube Community Build + PostgreSQL (Docker Compose) |
| AWS | VPC, ALB, ECS Fargate, ECR, RDS MySQL, Secrets Manager, CloudWatch, IAM, ACM (optional HTTPS) |
| Infrastructure as code | Terraform (S3 remote state with native lockfile) |

## Quick start (local, 5 minutes)

Prerequisites: **JDK 25**, **Maven 3.9+**, **Docker Desktop** (with Docker Compose v2).

Maven builds with the JDK in `JAVA_HOME`, and this project needs **JDK 25** (`mvn -version` must show
`Java version: 25...`). Terminals opened **inside VS Code** in this folder already use JDK 25
(`.vscode/settings.json`), even if your Windows `JAVA_HOME` still points to an older JDK. In any other
terminal, switch it for that window only:

```powershell
$env:JAVA_HOME = "C:\Program Files\Java\latest\jdk-25"     # PowerShell
```

```bash
export JAVA_HOME="/c/Program Files/Java/latest/jdk-25"     # Git Bash
```

The Docker image does not need a local JDK: it builds with `maven:3.9-eclipse-temurin-25-alpine` and runs on
`eclipse-temurin:25-jre-alpine`.

```bash
cd product-app
cp .env.example .env            # local-only credentials for Docker Compose
docker compose up -d --build    # builds the image, starts MySQL, waits for it, starts the app
docker compose logs -f app      # watch Flyway run and Spring Boot start (Ctrl+C to stop following)
```

Then open:

| URL | What |
|---|---|
| http://localhost:8080/swagger-ui/index.html | Swagger UI (try the APIs from the browser) |
| http://localhost:8080/api/products | REST API |
| http://localhost:8080/actuator/health | Health check (`{"status":"UP", ...}`) |

Run the automated tests (unit + web slice + a real MySQL via Testcontainers):

```bash
cd product-app
mvn test
```

`mvn test` also writes a **test coverage report** (JaCoCo) to `product-app/target/site/jacoco/index.html`.
`mvn verify` fails if line coverage drops below 80 %. To run the full code-quality check (SonarQube +
coverage + Quality Gate) on your PC before you push, see [doc 13](docs/13-code-quality-sonarqube-jacoco.md):

```bash
cd sonarqube && docker compose up -d --wait     # once: SonarQube on http://localhost:9000
cd ../product-app && ./sonar-scan.sh            # reads SONAR_TOKEN from product-app/.env (doc 13, step 4)
```

## Repository layout

```
aws-dev/
├── product-app/              Spring Boot application (+ Dockerfile, docker-compose.yml)
│   ├── src/main/java/...     controller / service / repository / entity / dto / exception / config
│   ├── src/main/resources/   application.yml, application-local.yml, application-aws.yml, db/migration/
│   ├── src/test/java/...     unit, web-slice and Testcontainers integration tests
│   ├── Dockerfile            multi-stage build -> small JRE image, non-root user, health check
│   └── docker-compose.yml    MySQL + app for local development
├── sonarqube/                docker-compose.yml: local SonarQube + PostgreSQL for code-quality checks (doc 13)
├── terraform/                AWS infrastructure (one file per concern: vpc.tf, ecs.tf, rds.tf, ...)
│   └── bootstrap/            one-time creation of the S3 bucket that stores Terraform state
├── jenkins/Jenkinsfile       pipeline: AWS resources one step at a time (doc 11) + code-quality step (tests, JaCoCo, SonarQube)
├── scripts/                  build-and-push.sh, redeploy.sh, smoke-test.sh (API checks), jenkins-setup.sh (job + AWS/SonarQube credentials)
│   └── sketchbook/           generate.py + sketchbook.css: draw docs/12-aws-sketchbook.html (+ PNGs)
└── docs/                     step-by-step, beginner-friendly documentation (start with 01)
    └── images/               the 14 sketchbook boards as PNG images (+ thumbs/ for the sketchbook page)
```

## Documentation

Read in order the first time:

| # | Document | Covers |
|---|---|---|
| 01 | [Application architecture](docs/01-architecture.md) | Layers, request flow, DTOs vs entities, error handling, profiles |
| 02 | [Project structure](docs/02-project-structure.md) | What every file is for |
| 03 | [API documentation](docs/03-api-documentation.md) | Endpoints, examples, status codes, validation, Swagger UI |
| 04 | [Database migrations (Flyway)](docs/04-database-migrations.md) | How migrations run, how to add one, what can go wrong |
| 05 | [Local Docker Compose](docs/05-local-docker-compose.md) | Build, run, inspect, troubleshoot the containers |
| 06 | [AWS architecture](docs/06-aws-architecture.md) | VPC, ALB, ECS Fargate, RDS, Secrets Manager, CloudWatch, security model |
| 07 | [Terraform implementation](docs/07-terraform.md) | Files, state backend, variables, init/plan/apply/destroy |
| 08 | [AWS deployment steps](docs/08-aws-deployment-steps.md) | The exact order of commands from zero to a running app on AWS |
| 09 | [Scaling and cost](docs/09-scaling-and-cost.md) | What each AWS service costs and how to scale up |
| 10 | [Troubleshooting](docs/10-troubleshooting.md) | Common errors and their fixes, local and AWS |
| 11 | [Jenkins + Terraform, step by step](docs/11-jenkins-terraform-step-by-step.md) | Create the AWS resources one group at a time from Jenkins, with a console checklist per step |
| 12 | [AWS sketchbook](docs/12-aws-sketchbook.html) (open in a browser) · [PNG images](docs/images/) | Hand-drawn infographic per AWS service (felt-pen style): what each step needs first, what Terraform creates in which order, and what uses it later |
| 13 | [Code quality: SonarQube + JaCoCo](docs/13-code-quality-sonarqube-jacoco.md) | Run SonarQube in Docker Compose, measure test coverage with JaCoCo, pass the Quality Gate on your PC before you push |

### The AWS sketchbook, step by step

One hand-drawn board per AWS step, saved as PNG images in [docs/images/](docs/images/). Click a board to
open it full size; the caption links to that step in [doc 11](docs/11-jenkins-terraform-step-by-step.md).

<table>
<tr>
<td align="center" width="33%"><a href="docs/images/sketchbook-01-s3-state-bucket.png"><img src="docs/images/sketchbook-01-s3-state-bucket.png" width="280" alt="Step 01 board: the S3 state bucket"></a><br><a href="docs/11-jenkins-terraform-step-by-step.md#step-01--terraform-state-bucket-s3"><b>01</b> S3 state bucket</a></td>
<td align="center" width="33%"><a href="docs/images/sketchbook-02-vpc-network.png"><img src="docs/images/sketchbook-02-vpc-network.png" width="280" alt="Step 02 board: the VPC network"></a><br><a href="docs/11-jenkins-terraform-step-by-step.md#step-02--network-vpc"><b>02</b> VPC network</a></td>
<td align="center" width="33%"><a href="docs/images/sketchbook-03-security-groups.png"><img src="docs/images/sketchbook-03-security-groups.png" width="280" alt="Step 03 board: the security groups"></a><br><a href="docs/11-jenkins-terraform-step-by-step.md#step-03--security-groups-firewall-rules"><b>03</b> Security groups</a></td>
</tr>
<tr>
<td align="center"><a href="docs/images/sketchbook-04-iam-roles.png"><img src="docs/images/sketchbook-04-iam-roles.png" width="280" alt="Step 04 board: the IAM roles"></a><br><a href="docs/11-jenkins-terraform-step-by-step.md#step-04--iam-roles-for-ecs"><b>04</b> IAM roles</a></td>
<td align="center"><a href="docs/images/sketchbook-05-ecr-repository.png"><img src="docs/images/sketchbook-05-ecr-repository.png" width="280" alt="Step 05 board: the ECR repository"></a><br><a href="docs/11-jenkins-terraform-step-by-step.md#step-05--ecr-repository"><b>05</b> ECR repository</a></td>
<td align="center"><a href="docs/images/sketchbook-06-image-to-ecr.png"><img src="docs/images/sketchbook-06-image-to-ecr.png" width="280" alt="Step 06 board: the image pushed to ECR"></a><br><a href="docs/11-jenkins-terraform-step-by-step.md#step-06--build-the-image-and-push-it-to-ecr"><b>06</b> Image to ECR</a></td>
</tr>
<tr>
<td align="center"><a href="docs/images/sketchbook-07-database-secret.png"><img src="docs/images/sketchbook-07-database-secret.png" width="280" alt="Step 07 board: the database secret"></a><br><a href="docs/11-jenkins-terraform-step-by-step.md#step-07--database-credentials-in-secrets-manager"><b>07</b> Secrets Manager</a></td>
<td align="center"><a href="docs/images/sketchbook-08-log-group.png"><img src="docs/images/sketchbook-08-log-group.png" width="280" alt="Step 08 board: the CloudWatch log group"></a><br><a href="docs/11-jenkins-terraform-step-by-step.md#step-08--cloudwatch-log-group"><b>08</b> CloudWatch Logs</a></td>
<td align="center"><a href="docs/images/sketchbook-09-rds-database.png"><img src="docs/images/sketchbook-09-rds-database.png" width="280" alt="Step 09 board: the RDS database"></a><br><a href="docs/11-jenkins-terraform-step-by-step.md#step-09--rds-mysql-database"><b>09</b> RDS MySQL</a></td>
</tr>
<tr>
<td align="center"><a href="docs/images/sketchbook-10-nat-gateway.png"><img src="docs/images/sketchbook-10-nat-gateway.png" width="280" alt="Step 10 board: the NAT gateway"></a><br><a href="docs/11-jenkins-terraform-step-by-step.md#step-10--nat-gateway"><b>10</b> NAT gateway</a></td>
<td align="center"><a href="docs/images/sketchbook-11-load-balancer.png"><img src="docs/images/sketchbook-11-load-balancer.png" width="280" alt="Step 11 board: the load balancer"></a><br><a href="docs/11-jenkins-terraform-step-by-step.md#step-11--application-load-balancer"><b>11</b> Load balancer</a></td>
<td align="center"><a href="docs/images/sketchbook-12-ecs-app.png"><img src="docs/images/sketchbook-12-ecs-app.png" width="280" alt="Step 12 board: ECS runs the app"></a><br><a href="docs/11-jenkins-terraform-step-by-step.md#step-12--ecs-cluster-task-definition-and-service"><b>12</b> ECS on Fargate</a></td>
</tr>
</table>

The sketchbook is generated. After changing a step's diagram in `scripts/sketchbook/generate.py`
(or the colours in `scripts/sketchbook/sketchbook.css`), redraw it with:

```bash
python scripts/sketchbook/generate.py         # needs only Python 3; writes docs/12-aws-sketchbook.html
python scripts/sketchbook/generate.py --png   # the same, plus the 14 PNGs in docs/images/ (uses Edge or Chrome, about 1 min)
```

Expected output: `wrote ...docs\12-aws-sketchbook.html (613 KB)`, and with `--png` one line per image,
for example `wrote ...docs\images\sketchbook-09-rds-database.png (324 KB)`. A `WARN` line names two labels
(or a label and a picture) that probably overlap: move one of them a little and run the command again.
If no browser is found, set `SKETCH_BROWSER` to the full path of `msedge.exe` or `chrome.exe`.

## Current status (2026-11-24)

- **Phases 1-6 are done and verified locally.** All 17 tests pass (100 % line coverage), the Docker Compose stack is healthy,
  and Terraform passes `validate` and a read-only `plan`.
- **Phases 7-8 ran on 2026-11-22 from Jenkins, one step at a time** (steps 01-12 of
  [11-jenkins-terraform-step-by-step.md](docs/11-jenkins-terraform-step-by-step.md)). The app ran on
  ECS Fargate behind the load balancer with RDS, and a full `terraform plan` reported *No changes*.
- **Everything was then deleted again** with `destroy-all` (45 resources), and the state bucket was
  deleted by hand, so nothing is billed. To deploy again, start at step 01. The IAM user `mani-dev`
  still has the `product-app-deployer` policy (`terraform/deployer-iam-policy.json`) attached.

## End-to-end flow

```
 Phase 1-3                Phase 4-5                     Phase 6-8
┌───────────────┐   ┌───────────────────────┐   ┌──────────────────────────────────────┐
│ Spring Boot   │   │ Dockerfile            │   │ terraform/bootstrap  -> S3 state     │
│ + Flyway      │──►│ docker compose up     │──►│ terraform apply      -> VPC/ALB/ECS/ │
│ + Swagger     │   │ verify APIs & health  │   │   RDS/ECR/Secrets/CloudWatch         │
│ mvn test      │   │ (local MySQL)         │   │ scripts/build-and-push.sh -> ECR     │
└───────────────┘   └───────────────────────┘   │ ECS pulls image, connects to RDS     │
                                                │ ALB -> http://<alb-dns>/swagger-ui   │
                                                └──────────────────────────────────────┘
```

Phases 7-8 run from Jenkins, one step at a time, each with a plan you approve
([doc 11](docs/11-jenkins-terraform-step-by-step.md)):

![How one Jenkins step runs: you start a build, Terraform plans only that step, you approve, Terraform applies and saves the state in S3](docs/images/sketchbook-00a-how-a-step-runs.png)

## Important rules followed in this project

- Schema changes only through Flyway (`spring.jpa.hibernate.ddl-auto=validate`, never `update`).
- No credentials in code or images: `.env` locally, Secrets Manager + IAM on AWS.
- One image, two profiles: `local` (Docker Compose) and `aws` (ECS), selected by `SPRING_PROFILES_ACTIVE`.
- ALB in public subnets, ECS tasks in private subnets, RDS in isolated private subnets with no internet route.
- Database reachable only from the ECS security group.
