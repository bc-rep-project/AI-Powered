# Deployment Guide

This guide provides instructions for deploying the AI Content Recommendation Engine in various environments.

## Prerequisites

- Docker and Docker Compose
- Kubernetes (for cloud deployments)
- Access to a cloud platform (AWS, GCP, or Azure)
- Domain name (optional)

## Local Deployment

1. Clone the repository:
```bash
git clone <repository-url>
cd ai-content-recommendation
```

2. Create and configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Build and start the containers:
```bash
docker-compose up -d
```

4. Access the services:
- API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090

## Cloud Deployment Options

### AWS Deployment

1. **Prerequisites**:
   - AWS CLI installed and configured
   - ECR repository created
   - EKS cluster running

2. **Build and push Docker image**:
```bash
aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <aws-account-id>.dkr.ecr.<region>.amazonaws.com
docker build -t <ecr-repo-url> .
docker push <ecr-repo-url>
```

3. **Deploy to EKS**:
```bash
# Update kubeconfig
aws eks update-kubeconfig --name <cluster-name> --region <region>

# Apply Kubernetes configurations
kubectl apply -f k8s/
```

### Google Cloud Platform (GCP)

1. **Prerequisites**:
   - gcloud CLI installed and configured
   - GKE cluster created

2. **Build and push Docker image**:
```bash
gcloud auth configure-docker
docker build -t gcr.io/<project-id>/<image-name> .
docker push gcr.io/<project-id>/<image-name>
```

3. **Deploy to GKE**:
```bash
# Update kubeconfig
gcloud container clusters get-credentials <cluster-name> --region <region>

# Apply Kubernetes configurations
kubectl apply -f k8s/
```

### Microsoft Azure

1. **Prerequisites**:
   - Azure CLI installed and configured
   - AKS cluster created

2. **Build and push Docker image**:
```bash
az acr login --name <registry-name>
docker build -t <registry-name>.azurecr.io/<image-name> .
docker push <registry-name>.azurecr.io/<image-name>
```

3. **Deploy to AKS**:
```bash
# Update kubeconfig
az aks get-credentials --resource-group <resource-group> --name <cluster-name>

# Apply Kubernetes configurations
kubectl apply -f k8s/
```

## Production Considerations

1. **Security**:
   - Enable SSL/TLS
   - Configure proper authentication
   - Set up network policies
   - Use secrets management
   - Regular security updates

2. **Scaling**:
   - Configure horizontal pod autoscaling
   - Set up database replication
   - Use managed Redis clusters
   - Configure proper resource limits

3. **Monitoring**:
   - Set up alerts in Grafana
   - Configure log aggregation
   - Enable distributed tracing
   - Set up uptime monitoring

4. **Backup**:
   - Regular database backups
   - Disaster recovery plan
   - Data retention policies

5. **Performance**:
   - Configure CDN for static assets
   - Optimize database queries
   - Set up caching strategies
   - Use connection pooling

## Environment Variables

Required environment variables for production deployment:

```env
# Database
POSTGRES_USER=<db-user>
POSTGRES_PASSWORD=<db-password>
POSTGRES_DB=<db-name>
POSTGRES_HOST=<db-host>
POSTGRES_PORT=5432

# MongoDB
MONGODB_URL=<mongodb-url>

# Redis
REDIS_HOST=<redis-host>
REDIS_PORT=6379

# Security
SECRET_KEY=<your-secret-key>
ALLOWED_ORIGINS=<comma-separated-origins>

# Monitoring
GRAFANA_USER=<grafana-admin-user>
GRAFANA_PASSWORD=<grafana-admin-password>
```

## Health Checks

The application provides the following health check endpoints:

- `/health`: Basic application health
- `/metrics`: Prometheus metrics

## Troubleshooting

1. **Database Connection Issues**:
   - Check connection strings
   - Verify network connectivity
   - Check security groups/firewall rules

2. **Performance Issues**:
   - Check resource utilization
   - Review database indexes
   - Analyze slow queries
   - Check cache hit rates

3. **Memory Issues**:
   - Review container memory limits
   - Check for memory leaks
   - Monitor garbage collection

4. **Monitoring Issues**:
   - Verify Prometheus configuration
   - Check Grafana data sources
   - Review alert rules

## Support

For deployment issues or questions:
1. Check the troubleshooting guide
2. Review application logs
3. Contact the development team
4. Open a GitHub issue 