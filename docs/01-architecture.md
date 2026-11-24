# 01 — Application architecture

## 1. What are we implementing?

A REST API that manages products (create, list, get, update, delete) using the standard
**Spring Boot layered architecture**. Every HTTP request passes through the same layers:

```
          HTTP (JSON)
              │
              ▼
┌───────────────────────────┐
│  ProductController        │  @RestController  – maps URLs + HTTP methods, validates input (@Valid)
└─────────────┬─────────────┘
              │ ProductRequest (DTO)                 GlobalExceptionHandler (@RestControllerAdvice)
              ▼                                      converts every exception into ApiErrorResponse JSON
┌───────────────────────────┐
│  ProductService           │  @Service – business logic, @Transactional boundaries, logging
└─────────────┬─────────────┘
              │ Product (JPA entity)
              ▼
┌───────────────────────────┐
│  ProductRepository        │  JpaRepository – generated SQL (save, findById, findAll, delete)
└─────────────┬─────────────┘
              │ JDBC (HikariCP connection pool)
              ▼
┌───────────────────────────┐
│  MySQL 8  "products"      │  table created and versioned by Flyway (V1__create_products_table.sql)
└───────────────────────────┘
```

## 2. Why do we need each layer?

| Layer | Responsibility | Why separate it |
|---|---|---|
| **Controller** | HTTP only: paths, status codes, trigger validation, Swagger annotations | Business logic must not depend on HTTP; easy to test with MockMvc |
| **DTOs** (`ProductRequest`, `ProductResponse`, `ApiErrorResponse`) | The public JSON contract | The database model can change without breaking clients; validation lives on the request DTO |
| **Service** | Business rules, transactions, logging | One place for logic; unit-testable with a mocked repository |
| **Repository** | Database access | Spring Data generates the implementation; no SQL for simple CRUD |
| **Entity** | Table mapping (`@Entity`, `@Column`) | Hibernate maps rows to objects; `@PrePersist`/`@PreUpdate` set timestamps |
| **Exception handler** | Turn exceptions into consistent JSON errors | Clients always get the same error shape; no stack traces leak |
| **Flyway migrations** | Create and evolve the schema | Repeatable, versioned, identical in every environment |

## 3. How does a request work? (POST /api/products)

1. Spring MVC parses the JSON body into a `ProductRequest` record.
2. `@Valid` runs the constraints (`@NotBlank`, `@Min`, ...). If any fail, Spring throws
   `MethodArgumentNotValidException`, which `GlobalExceptionHandler` turns into **400** with a
   `fieldErrors` map. The service is never called.
3. `ProductService.create()` starts a transaction, maps the DTO to a `Product` entity
   (`ProductMapper`), calls `productRepository.save()`, logs the result and maps the saved entity
   back to a `ProductResponse`.
4. Hibernate issues `INSERT INTO products ...`; MySQL assigns the `AUTO_INCREMENT` id.
5. The controller returns **201 Created** with a `Location: /api/products/{id}` header and the JSON body.

For `GET /api/products/{id}` with an unknown id, the service throws `ProductNotFoundException`
and the handler returns **404** with the standard error body.

## 4. Configuration and profiles

```
application.yml          common settings, reads environment variables: DB_HOST, DB_PORT, DB_NAME, DB_USERNAME, DB_PASSWORD
application-local.yml    Docker Compose: verbose logging, SQL logging, health details visible
application-aws.yml      ECS Fargate: JSON logs for CloudWatch, trust ALB forwarded headers, minimal health output
```

The active profile is chosen by the environment variable `SPRING_PROFILES_ACTIVE` (`local` in
`docker-compose.yml`, `aws` in the ECS task definition). Credentials are **never** in these files.

On AWS, the profile and the database settings come from the ECS task definition, and the credentials
from Secrets Manager:

### `SPRING_PROFILES_ACTIVE=aws`, `DB_HOST`, `DB_PORT`, `DB_NAME`: set by the task definition

![ECS board: the task definition carries the environment variables, secrets and log settings](images/sketchbook-12-ecs-app.png)

### `DB_USERNAME`, `DB_PASSWORD`: injected from Secrets Manager

![Secrets Manager board: a random password, readable only by the execution role](images/sketchbook-07-database-secret.png)

## 5. Which configuration files are involved?

| File | Purpose |
|---|---|
| `product-app/pom.xml` | Dependencies and build (Spring Boot parent, Flyway, springdoc, Testcontainers) |
| `product-app/src/main/resources/application*.yml` | Runtime configuration per profile |
| `product-app/src/main/resources/db/migration/V1__*.sql` | Database schema |
| `product-app/Dockerfile` | How the image is built |
| `product-app/docker-compose.yml` + `.env` | Local runtime |
| `terraform/ecs.tf` | AWS runtime (environment variables and secrets for the container) |

The `Dockerfile` becomes the image that ECS runs: the same image as in Docker Compose, built for `linux/amd64`:

![Image board: Maven builds the jar, the JRE alpine image runs it as user app, ECR stores and scans it](images/sketchbook-06-image-to-ecr.png)

## 6. What commands should I execute?

```bash
cd product-app
mvn test                  # compile + run all tests (needs Docker for the Testcontainers test)
mvn package -DskipTests   # build target/product-app.jar
```

## 7. What output should I expect and how can I verify it?

`mvn test` ends with:

```
[INFO] Tests run: 17, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

The 17 tests are: 6 service unit tests, 9 controller web-slice tests (including the 404 "no endpoint" and
500 "unexpected error" handlers), 2 integration tests against a real MySQL started by Testcontainers
(Flyway migration check + full CRUD lifecycle). Together they cover 100 % of the lines; see
[doc 13](13-code-quality-sonarqube-jacoco.md) for the coverage report.

## 8. Common errors and solutions

| Error | Cause | Fix |
|---|---|---|
| `Could not find a valid Docker environment` during `mvn test` | Testcontainers needs Docker | Start Docker Desktop, re-run |
| `Could not resolve placeholder 'DB_USERNAME'` when running the jar directly | Required env vars missing | Set `DB_USERNAME`/`DB_PASSWORD` (and `DB_HOST` etc.) or use Docker Compose |
| `Schema-validation: missing table [products]` | Flyway did not run (disabled / wrong location) | Check `spring.flyway.enabled=true` and that the SQL file is under `db/migration` |
| `Schema-validation: wrong column type` | Entity and migration disagree | Fix the entity or add a new migration; never edit an applied migration |

## Runtime views

### Local (Docker Compose)

```
 your browser / curl                       Docker Desktop
 ───────────────────      ┌──────────────────────────────────────────────┐
 localhost:8080  ───────► │  product-app (Spring Boot)  ──► mysql:3306   │
 localhost:3307  ───────► │  (profile: local)              (volume)      │
                          └──────────────────────────────────────────────┘
```

### AWS (ECS Fargate)

```
 Internet ──► ALB (public subnets) ──► ECS Fargate task (private subnets) ──► RDS MySQL (private DB subnets)
                                            │  profile: aws
                                            ├─► pulls image from ECR          (via NAT Gateway)
                                            ├─► reads DB_USERNAME/DB_PASSWORD from Secrets Manager
                                            └─► writes logs to CloudWatch
```

The same view, drawn by hand (each part is labelled with the step that creates it):

![The finished system: users, load balancer, ECS task, RDS, NAT gateway and the AWS services they use](images/sketchbook-00b-big-picture.png)

### What each arrow means for the application

#### Load balancer → app: `/actuator/health` must return 200

![Load balancer board: the health check GET /actuator/health; the aws profile trusts the forwarded headers](images/sketchbook-11-load-balancer.png)

#### App → RDS: JDBC through HikariCP, Flyway runs V1 at start-up

![RDS board: MySQL on port 3306, reachable only from the ECS task](images/sketchbook-09-rds-database.png)

#### Image pulled from ECR ...

![ECR board: the repository and the image address](images/sketchbook-05-ecr-repository.png)

#### ... through the NAT gateway

![NAT board: the task can call out, nothing can call in](images/sketchbook-10-nat-gateway.png)

#### App → CloudWatch: the JSON logs of `application-aws.yml`

![CloudWatch board: one log stream per task in /ecs/product-app-dev](images/sketchbook-08-log-group.png)

See [06-aws-architecture.md](06-aws-architecture.md) for the full picture.

### How the AWS side around the app is built

None of this needs application code, but it is what the app runs inside:

#### 01 · S3 state bucket (Terraform's memory)

![S3 board: the Terraform state bucket](images/sketchbook-01-s3-state-bucket.png)

#### 02 · VPC: public, private-app and private-db subnets

![VPC board: two zones, three kinds of subnet](images/sketchbook-02-vpc-network.png)

#### 03 · Security groups: who may talk to the app and the database

![Security groups board: ALB to ECS on 8080, ECS to RDS on 3306](images/sketchbook-03-security-groups.png)

#### 04 · IAM roles: no AWS keys in the container

![IAM board: the execution role and the empty task role](images/sketchbook-04-iam-roles.png)

#### Jenkins builds all of it, one step at a time

![How one Jenkins step runs: plan, your approval, apply, state saved in S3](images/sketchbook-00a-how-a-step-runs.png)
