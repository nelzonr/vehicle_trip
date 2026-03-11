# AWS Cloud Infrastructure Sketch

To run this solution in a scalable way (100M+ records) on AWS, this would be the recommended configuration:

### 1. Database Layer: Amazon RDS for PostgreSQL

- Enable **PostGIS**.
- Use **Provisioned IOPS (PIOPS)** to ensure write performance during massive ingestion.
- Use **Read Replicas** to offload traffic from reports and dashboards.

### 2. Ingestion & Storage: Amazon S3 + Lambda / ECS

- **S3:** CSV files are uploaded to an S3 bucket.
- **Event-Driven:** The upload triggers an event that places a message in an **Amazon SQS** queue.

### 3. Compute Layer: AWS Fargate (ECS)

- **API Service:** Runs FastAPI in horizontally scalable containers.
- **Worker Service:** Runs Celery to process SQS messages. Uses Fargate to avoid managing servers.

### 4. Cache & Task Queue: Amazon ElastiCache (Redis)

- Managed Redis service for Celery queues and WebSocket state.

### 5. API Gateway & Load Balancing

- **Application Load Balancer (ALB):** Distributes traffic to API containers.
- Natively supports **WebSockets** for status notifications.

### 6. Security & CI/CD

- **VPC:** Isolate database and Redis in private subnets.
- **AWS Secrets Manager:** Store database credentials and API keys.
- **AWS CodePipeline:** Automated deployments via Docker.

---

This setup allows you to scale based on demand, with predictable costs and high availability.
