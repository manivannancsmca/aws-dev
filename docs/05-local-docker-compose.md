# 05 — Local Docker Compose setup

## 1. What are we implementing?

Two containers on your machine, started with one command:

```
docker compose up -d --build
   │
   ├─► product-mysql   mysql:8.0.46          port 3307 on your PC → 3306 in the container, data in volume "mysql_data"
   │        │ healthcheck: mysqladmin ping (every 10 s)
   │        ▼ healthy
   └─► product-app     product-app:local     port 8080 → 8080, profile "local", DB_HOST=mysql
            │ Flyway migrates, Spring Boot starts
            ▼ healthcheck: wget /actuator/health (every 15 s)
```

## 2. Why do we need it?

- Runs the **exact image** that will run on AWS. If it works here, the image is correct.
- No MySQL installation on your PC; the database lives in a Docker volume you can wipe at any time.
- Startup ordering and health checks are the same ideas ECS and the ALB use later.
- Section 9 shows what each container and file becomes on AWS.

## 3. How does it work?

- `docker-compose.yml` defines two services. `depends_on: condition: service_healthy` makes Compose
  wait for the MySQL health check before starting the app.
- Values such as `${MYSQL_PASSWORD}` are read from `.env` in the same folder. Passwords use the
  `${VAR:?message}` form, so Compose refuses to start with a clear message if they are missing.
- Inside the Compose network the app reaches MySQL by its **service name** `mysql`
  (`DB_HOST=mysql`), not `localhost`.
- The `Dockerfile` builds the jar inside a Maven container and copies only the extracted layers into a
  small JRE image that runs as the non-root user `app`.

## 4. Which configuration files are involved?

| File | Purpose |
|---|---|
| `product-app/docker-compose.yml` | Services, ports, volume, health checks, environment variables |
| `product-app/.env` (copy of `.env.example`) | Database name, user, passwords, host ports |
| `product-app/Dockerfile`, `.dockerignore` | Image build |
| `product-app/src/main/resources/application-local.yml` | Profile used inside the container |

## 5. What commands should I execute?

All commands run in the `product-app` folder (Git Bash, PowerShell or CMD).

### First start

```bash
cp .env.example .env                 # PowerShell: Copy-Item .env.example .env
docker compose up -d --build         # build image + start both containers in the background
docker compose up -d --build --wait  # same, but the command returns only when both are healthy
```

### Everyday commands

| Task | Command |
|---|---|
| Status | `docker compose ps` |
| Follow app logs | `docker compose logs -f app` |
| Last 100 lines of MySQL logs | `docker compose logs --tail=100 mysql` |
| Stop (keep data) | `docker compose stop` |
| Start again | `docker compose start` |
| Restart only the app | `docker compose restart app` |
| Rebuild after code changes | `docker compose up -d --build app` |
| Remove containers (keep data volume) | `docker compose down` |
| Remove containers **and** the database volume | `docker compose down -v` |
| Open a MySQL shell | `docker compose exec mysql mysql -uproduct_user -pproduct_pass productdb` |
| Shell inside the app container | `docker compose exec app sh` |
| Resource usage | `docker stats --no-stream` |
| Inspect health check results | `docker inspect --format '{{json .State.Health}}' product-app` |
| Image details | `docker images product-app:local` · `docker history product-app:local` |

### Verify from your machine

```bash
curl http://localhost:8080/actuator/health
curl -X POST http://localhost:8080/api/products -H "Content-Type: application/json" \
  -d '{"name":"Wireless Mouse","description":"Ergonomic 2.4 GHz wireless mouse","price":29.99,"quantity":150}'
curl http://localhost:8080/api/products
```

Open http://localhost:8080/swagger-ui/index.html in a browser.

## 6. What output should I expect?

`docker compose up -d --build --wait`:

```
 Container product-mysql  Healthy
 Container product-app    Healthy
```

`docker compose ps`:

```
NAME            IMAGE               STATUS                    PORTS
product-app     product-app:local   Up 11 seconds (healthy)   0.0.0.0:8080->8080/tcp
product-mysql   mysql:8.0.46        Up 21 seconds (healthy)   0.0.0.0:3307->3306/tcp
```

`docker compose logs app` (first start) contains:

```
The following 1 profile is active: "local"
Schema history table `productdb`.`flyway_schema_history` does not exist yet
Successfully validated 1 migration (execution time 00:00.023s)
Creating Schema History table `productdb`.`flyway_schema_history` ...
Current version of schema `productdb`: << Empty Schema >>
Migrating schema `productdb` to version "1 - create products table"
Successfully applied 1 migration to schema `productdb`, now at version v1
Tomcat started on port 8080 (http) with context path '/'
Started ProductAppApplication in 6.573 seconds (process running for 6.933)
```

`curl http://localhost:8080/actuator/health` (local profile shows components):

```json
{"status":"UP","components":{"db":{"status":"UP","details":{"database":"MySQL","validationQuery":"isValid()"}},
 "diskSpace":{"status":"UP"},"livenessState":{"status":"UP"},"ping":{"status":"UP"},"readinessState":{"status":"UP"}},
 "groups":["liveness","readiness"]}
```

Create a product:

```
HTTP/1.1 201
Location: http://localhost:8080/api/products/1
{"id":1,"name":"Wireless Mouse","description":"Ergonomic 2.4 GHz wireless mouse","price":29.99,"quantity":150,
 "createdAt":"2026-11-22T10:38:06.947414Z","updatedAt":"2026-11-22T10:38:06.947414Z"}
```

Image: `docker images product-app:local` → about **430 MB** (Alpine + JRE 25 + application layers).

## 7. How can I verify it?

The quickest check is the smoke test script. From the repository root, in Git Bash:

```bash
./scripts/smoke-test.sh
```

Expected: 12 lines starting with `PASS` and a final `ALL CHECKS PASSED`. The script creates one product,
updates it and deletes it again, so it leaves your data as it was. Later you can run the same script
against AWS by passing the load balancer URL: `./scripts/smoke-test.sh http://<alb-dns-name>`.

Checklist (all were verified while building this project):

- [ ] `docker compose ps` shows both containers `(healthy)`.
- [ ] `/actuator/health` returns `"status":"UP"` with `db` → `UP`.
- [ ] Swagger UI loads and `POST /api/products` → 201 via **Try it out**.
- [ ] `GET /api/products/999` → 404 JSON; `GET /api/products/abc` → 400 JSON; invalid body → 400 with `fieldErrors`.
- [ ] `docker compose exec mysql mysql -uproduct_user -pproduct_pass productdb -e "SELECT version, description, success FROM flyway_schema_history;"` shows version 1, success 1.
- [ ] Data survives a restart: create a product, `docker compose restart app`, list again.
- [ ] `docker compose down` then `docker compose up -d` → data still there (volume). `down -v` → empty database, Flyway re-creates the schema.

## 8. Common errors and solutions

| Symptom | Cause | Solution |
|---|---|---|
| `Bind for 0.0.0.0:3306 failed: port is already allocated` / `3307` busy | Another MySQL on your PC uses the port | Change `MYSQL_HOST_PORT` in `.env` (default is already 3307 for this reason) |
| `Bind for 0.0.0.0:8080 failed` | Something else listens on 8080 | Change `APP_HOST_PORT` in `.env` |
| `error: Set MYSQL_PASSWORD in the .env file` | `.env` missing | `cp .env.example .env` |
| App container restarts in a loop, log shows `Communications link failure` | App started before MySQL was ready (health check misconfigured) or wrong `DB_HOST` | Keep `depends_on: condition: service_healthy`; `DB_HOST` must be `mysql` (service name) |
| `Access denied for user 'product_user'@'%'` | Password in `.env` changed after the volume was created (MySQL only reads env on first init) | `docker compose down -v` then `up -d` (deletes data) |
| `product-mysql` keeps restarting; `docker compose logs mysql` shows `Cannot boot server version 80046 on data directory built by version 804xx. Downgrade is not supported` | The volume was created by MySQL 8.4; this file now uses 8.0, which cannot read it | `docker compose down -v` then `up -d --build` (deletes local data; Flyway recreates the table) |
| `mysql` container unhealthy for > 1 minute | Slow first initialisation or low memory | `docker compose logs mysql`; give Docker Desktop ≥ 4 GB RAM |
| Build fails with `dependency:go-offline` network errors | No internet / proxy | Retry; configure Docker Desktop proxy settings |
| Build takes long every time | BuildKit cache not used | Make sure Docker Desktop uses BuildKit (default); the `--mount=type=cache` keeps Maven downloads |
| `exec /usr/bin/java: exec format error` on AWS later | Image built for ARM (Apple Silicon) | Build with `docker build --platform linux/amd64` (done by `scripts/build-and-push.sh`) |
| Health check always `starting` | JVM slow to boot | `start_period` is 60 s; check `docker compose logs app` for exceptions |

## 9. From Docker Compose to AWS

The same image later runs on AWS. Every piece of this local setup has a counterpart there:

![The finished system on AWS: load balancer, ECS task, RDS, NAT gateway and the AWS services they use](images/sketchbook-00b-big-picture.png)

| Locally (Docker Compose) | On AWS | Step |
|---|---|---|
| `product-app` container, profile `local` | ECS Fargate task, profile `aws` | 12 |
| image `product-app:local` | the same image as `product-app:latest` in ECR | 05 + 06 |
| `mysql` container + volume `mysql_data` | RDS MySQL (managed, encrypted, backed up) | 09 |
| passwords in `.env` | Secrets Manager, injected as `DB_USERNAME` / `DB_PASSWORD` | 07 |
| `docker compose logs app` | CloudWatch Logs `/ecs/product-app-dev` | 08 |
| Compose health check, `localhost:8080` | load balancer health check, `http://<alb-dns-name>` | 11 |
| Compose network, service name `mysql` | VPC subnets + security groups, `DB_HOST` = RDS endpoint | 02 + 03 |
| (not needed locally) | NAT gateway, IAM roles, Terraform state bucket | 10, 04, 01 |
| `docker compose up` | Jenkins + Terraform, one step at a time ([doc 11](11-jenkins-terraform-step-by-step.md)) | all |

One board per row, from the [sketchbook](12-aws-sketchbook.html):

### `product-app` container → ECS Fargate task (step 12)

![ECS board: the task definition and service that run the same image with profile aws](images/sketchbook-12-ecs-app.png)

### `product-app:local` image → the same image in ECR (step 06) ...

![Image board: the same Dockerfile, built for linux/amd64 and pushed to ECR](images/sketchbook-06-image-to-ecr.png)

### ... stored in the ECR repository (step 05)

![ECR board: the repository and the image address](images/sketchbook-05-ecr-repository.png)

### `mysql` container + `mysql_data` volume → RDS MySQL (step 09)

![RDS board: managed MySQL 8.4, private, reachable only from the ECS task](images/sketchbook-09-rds-database.png)

### Passwords in `.env` → Secrets Manager (step 07)

![Secrets Manager board: a random password nobody types](images/sketchbook-07-database-secret.png)

### `docker compose logs app` → CloudWatch Logs (step 08)

![CloudWatch board: one log stream per task](images/sketchbook-08-log-group.png)

### Health check + `localhost:8080` → load balancer (step 11)

![Load balancer board: the public address and the /actuator/health check](images/sketchbook-11-load-balancer.png)

### Compose network (service name `mysql`) → VPC subnets (step 02) ...

![VPC board: public, private-app and private-db subnets in two zones](images/sketchbook-02-vpc-network.png)

### ... and security groups (step 03)

![Security groups board: only ALB to ECS on 8080 and ECS to RDS on 3306](images/sketchbook-03-security-groups.png)

### Not needed locally · NAT gateway (step 10)

![NAT board: the way out of the private subnets](images/sketchbook-10-nat-gateway.png)

### Not needed locally · IAM roles (step 04)

![IAM board: temporary keys instead of a .env file](images/sketchbook-04-iam-roles.png)

### Not needed locally · Terraform state bucket (step 01)

![S3 board: where Terraform remembers what it built](images/sketchbook-01-s3-state-bucket.png)

### `docker compose up` → Jenkins + Terraform, one step at a time

![How one Jenkins step runs: plan, your approval, apply, state saved in S3](images/sketchbook-00a-how-a-step-runs.png)

## Running without Docker (optional)

Start only MySQL in Docker and run the app from your IDE / Maven:

```bash
docker compose up -d mysql
DB_HOST=localhost DB_PORT=3307 DB_NAME=productdb DB_USERNAME=product_user DB_PASSWORD=product_pass \
SPRING_PROFILES_ACTIVE=local mvn spring-boot:run
```

PowerShell: set the variables with `$env:DB_HOST="localhost"` etc. before `mvn spring-boot:run`.
