# 06 — AWS architecture

## 1. What are we implementing?

A private, load-balanced deployment of the same Docker image on **ECS Fargate**, backed by
**RDS MySQL**, inside a **dedicated VPC**, with credentials in **Secrets Manager** and logs in
**CloudWatch**. Everything is created by Terraform.

The finished system, drawn by hand (each part is labelled with the step that creates it, see the
[sketchbook](12-aws-sketchbook.html)). The text diagram below shows the same thing in more detail.

![The finished system: users, load balancer, ECS task, RDS, NAT gateway and the AWS services they use](images/sketchbook-00b-big-picture.png)

```
                                   ┌──────────────────────────── VPC 10.0.0.0/16 (region ap-south-1) ────────────────────────────┐
                                   │                                                                                               │
                                   │   AZ a                                             AZ b                                       │
                                   │  ┌──────────────────────────────┐                ┌──────────────────────────────┐             │
   Internet                        │  │ public subnet 10.0.0.0/24    │                │ public subnet 10.0.1.0/24    │             │
      │                            │  │  ┌─────────┐   ┌───────────┐ │                │  ┌─────────┐                 │             │
      │  HTTP 80 / HTTPS 443       │  │  │   ALB   │   │  NAT GW   │ │                │  │   ALB   │ (2nd node)      │             │
      └────────────────────────────┼──┼─►│         │   │ + EIP     │ │                │  │         │                 │             │
                                   │  │  └────┬────┘   └─────▲─────┘ │                │  └────┬────┘                 │             │
                                   │  └───────┼──────────────┼───────┘                └───────┼──────────────────────┘             │
                                   │          │ 8080         │ outbound only                  │                                    │
                                   │  ┌───────▼──────────────┼───────┐                ┌───────▼──────────────────────┐             │
                                   │  │ private app 10.0.10.0/24     │                │ private app 10.0.11.0/24     │             │
                                   │  │  ┌───────────────────┴─────┐ │                │  (tasks are placed in either │             │
                                   │  │  │ ECS Fargate task        │ │                │   AZ; 1 task by default)     │             │
                                   │  │  │ product-app:8080        │ │                │                              │             │
                                   │  │  │ profile=aws             │ │                │                              │             │
                                   │  │  └───────────┬─────────────┘ │                │                              │             │
                                   │  └──────────────┼───────────────┘                └──────────────────────────────┘             │
                                   │                 │ 3306                                                                        │
                                   │  ┌──────────────▼───────────────┐                ┌──────────────────────────────┐             │
                                   │  │ private db 10.0.20.0/24      │                │ private db 10.0.21.0/24      │             │
                                   │  │  ┌─────────────────────────┐ │                │  (standby lives here when    │             │
                                   │  │  │ RDS MySQL 8.4           │ │                │   db_multi_az = true)        │             │
                                   │  │  │ db.t4g.micro, no public │ │                │                              │             │
                                   │  │  └─────────────────────────┘ │                │                              │             │
                                   │  └──────────────────────────────┘                └──────────────────────────────┘             │
                                   │     (no route to the internet at all)                                                         │
                                   └───────────────────────────────────────────────────────────────────────────────────────────────┘

   Regional services used by the task (reached through the NAT Gateway):
     Amazon ECR  ─ image "product-app:latest"        AWS Secrets Manager ─ product-app-dev/db-credentials {username, password}
     CloudWatch Logs ─ /ecs/product-app-dev          IAM ─ task execution role (pull image, write logs, read secret) + task role
     ACM (optional) ─ TLS certificate for the ALB    S3 ─ Terraform state bucket (with lockfile)
```

Mermaid version (renders on GitHub / VS Code):

```mermaid
flowchart LR
    U[Internet user] -->|80/443| ALB[Application Load Balancer<br/>public subnets]
    ALB -->|8080 health: /actuator/health| T[ECS Fargate task<br/>product-app, private app subnets]
    T -->|3306| RDS[(RDS MySQL 8.4<br/>private db subnets)]
    T -.->|pull image via NAT| ECR[(Amazon ECR)]
    T -.->|logs| CW[CloudWatch Logs]
    SM[Secrets Manager<br/>db-credentials] -.->|DB_USERNAME / DB_PASSWORD<br/>injected at task start| T
    ACM[ACM certificate<br/>optional] -.-> ALB
```

## 2. Why each service?

| Service | Role in this project | Why not something else |
|---|---|---|
| **VPC** (own, not default) | Isolated network with public/private tiers | The default VPC has only public subnets; isolation is a security requirement |
| **Public subnets** (2 AZs) | Host the ALB nodes and the NAT Gateway | An ALB requires at least two AZs |
| **Private app subnets** | Host the ECS tasks; no public IP | Tasks cannot be reached directly from the internet |
| **Private db subnets** | Host RDS; **no internet route at all** | Even a misconfigured security group cannot expose the database |
| **Internet Gateway** | Internet access for the public subnets | |
| **NAT Gateway** | Lets private tasks reach ECR, CloudWatch, Secrets Manager outbound | Tasks need to pull the image and send logs; VPC endpoints are an alternative (see 09) |
| **ALB** | Single public entry point, health checks, HTTPS termination | Replaces exposing the task directly; required for scaling to several tasks |
| **ECS Fargate** | Runs the container without managing servers | No EC2 patching; pay per task |
| **ECR** | Private registry for the image | ECS pulls from it with the execution role; images are scanned on push |
| **RDS MySQL** | Managed database: backups, patching, optional Multi-AZ | Running MySQL in a container on Fargate would lose data on restart |
| **Secrets Manager** | Stores the generated DB password; ECS injects it as env var | The password never appears in the task definition, image or code |
| **IAM** | Execution role (ECR + logs + secret) and task role (app permissions) | Least privilege: each role has only what it needs |
| **CloudWatch Logs** | Container stdout/stderr, 7-day retention | Only way to see application logs on Fargate |
| **ACM** | Free TLS certificate for the ALB (optional) | Needs a domain you control |
| **S3** | Terraform remote state with native lockfile | Shared, versioned state; prevents two people applying at once |

### Each service up close

One board per service, in the order Terraform builds them. Each board shows what the service needs
first, what Terraform creates and in which order, what uses it later, and how it works inside.
The numbers are the step numbers of the Jenkins guide ([doc 11](11-jenkins-terraform-step-by-step.md)).

#### 01 · S3 state bucket

![S3 board: the Terraform state bucket with versioning, encryption and blocked public access](images/sketchbook-01-s3-state-bucket.png)

#### 02 · VPC, subnets and route tables

![VPC board: the VPC, internet gateway, six subnets and route tables](images/sketchbook-02-vpc-network.png)

#### 03 · Security groups

![Security groups board: the chain internet, ALB, ECS, RDS](images/sketchbook-03-security-groups.png)

#### 04 · IAM roles

![IAM board: the execution role and the task role that ECS assumes](images/sketchbook-04-iam-roles.png)

#### 05 · ECR repository

![ECR board: the repository, its lifecycle rule and the image address](images/sketchbook-05-ecr-repository.png)

#### 06 · The image in ECR

![Image board: build for linux/amd64, push to ECR, scan on push](images/sketchbook-06-image-to-ecr.png)

#### 07 · Secrets Manager

![Secrets Manager board: a random password readable only by the execution role](images/sketchbook-07-database-secret.png)

#### 08 · CloudWatch Logs

![CloudWatch board: the log group ECS writes to](images/sketchbook-08-log-group.png)

#### 09 · RDS MySQL

![RDS board: the DB subnet group and the private MySQL instance behind rds-sg](images/sketchbook-09-rds-database.png)

#### 10 · NAT gateway

![NAT board: tasks can call out, nothing can call in](images/sketchbook-10-nat-gateway.png)

#### 11 · Application Load Balancer

![Load balancer board: ALB, target group, listener and health check](images/sketchbook-11-load-balancer.png)

#### 12 · ECS on Fargate

![ECS board: task definition, cluster, service and what happens when the task starts](images/sketchbook-12-ecs-app.png)

## 3. How does traffic flow?

**Inbound request** `GET http://<alb-dns>/api/products`

1. DNS resolves the ALB name to its public IPs (one per AZ).
2. The ALB security group allows 80 (and 443) from `0.0.0.0/0`.
3. The listener forwards to the target group (`target_type = ip`, port 8080).
4. The ECS security group allows 8080 **only from the ALB security group**.
5. Spring Boot handles the request; `server.forward-headers-strategy=framework` makes generated URLs
   use the public scheme/host.

**Task start-up**

1. ECS assumes the **execution role**, pulls `product-app:<tag>` from ECR (through the NAT Gateway),
   reads `username` and `password` from the secret and injects them as `DB_USERNAME`/`DB_PASSWORD`.
2. The container starts with `SPRING_PROFILES_ACTIVE=aws`, `DB_HOST=<rds endpoint>`, `DB_PORT=3306`, `DB_NAME=productdb`.
3. Flyway connects to RDS (RDS security group allows 3306 only from the ECS security group) and applies
   pending migrations.
4. The container health check and the ALB health check hit `/actuator/health`. After 2 successful checks
   the task receives traffic.
5. Logs stream to CloudWatch log group `/ecs/product-app-dev`, stream `ecs/product-app/<task id>`.

## 4. Security model (what is enforced where)

| Requirement | Implemented by |
|---|---|
| ALB in public subnets | `alb.tf` → `subnets = aws_subnet.public[*].id` |
| ECS tasks in private subnets, no public IP | `ecs_service.tf` → `assign_public_ip = false`, private app subnets |
| RDS in private DB subnets, not public | `rds.tf` → `publicly_accessible = false`, DB subnet group over `private_db` |
| DB access only from ECS | `security_groups.tf` → `rds_from_ecs` rule references the ECS SG; no other ingress |
| DB subnets have no internet route | `vpc.tf` → `aws_route_table.private_db` has no `0.0.0.0/0` route |
| Credentials in Secrets Manager | `secrets.tf`, injected via `secrets` in `ecs.tf` |
| Least privilege IAM | `iam.tf` → execution role: managed ECS policy + `GetSecretValue` on **one** secret ARN; task role: empty |
| HTTPS | `acm.tf` + `alb.tf` HTTPS listener and HTTP→HTTPS redirect when a certificate is configured |
| Encryption at rest | RDS `storage_encrypted = true`, S3 state bucket SSE, Secrets Manager (always encrypted) |
| Non-root container | `Dockerfile` → `USER app` |

## 5. Deployment flow

With Jenkins, the same flow runs as a loop of small steps, one group of resources per build
([doc 11](11-jenkins-terraform-step-by-step.md)):

![How one Jenkins step runs: you start a build, Terraform plans only that step, you approve, Terraform applies and saves the state in S3](images/sketchbook-00a-how-a-step-runs.png)

Done by hand with Terraform, as in [doc 08](08-aws-deployment-steps.md):

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant TF as Terraform
    participant AWS as AWS
    participant ECS as ECS service
    Dev->>TF: bootstrap: apply (S3 state bucket)
    Dev->>TF: apply -target=aws_ecr_repository.app
    TF->>AWS: create ECR repository
    Dev->>AWS: scripts/build-and-push.sh (docker build, docker push)
    Dev->>TF: apply (everything else)
    TF->>AWS: VPC, SGs, IAM, Secrets, RDS (5-10 min), ALB, ECS cluster/task/service
    ECS->>AWS: pull image, read secret, start task
    ECS->>AWS: Flyway migrates RDS, health checks pass
    Dev->>AWS: curl http://<alb-dns>/actuator/health -> UP
```

The ECR repository is created first because the ECS service needs an image to exist before its first
task can start. See [08-aws-deployment-steps.md](08-aws-deployment-steps.md).

## 6. High availability as configured (demo sizing)

| Component | Now | Production upgrade |
|---|---|---|
| ECS tasks | 1 task, can be placed in either AZ | `desired_count = 2+`, `enable_autoscaling = true` |
| ALB | Already spans 2 AZs | – |
| NAT Gateway | 1 (AZ a); if AZ a fails, tasks in AZ b lose outbound access | One NAT per AZ |
| RDS | Single AZ, 1-day backups | `db_multi_az = true`, 7+ day backups, deletion protection |

Details and costs: [09-scaling-and-cost.md](09-scaling-and-cost.md).
