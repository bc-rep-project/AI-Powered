# GCP Cost Optimization Guide

## Current Cost Breakdown (Monthly)

Base Configuration:
- GKE Cluster (3 nodes, e2-standard-2): ~$150
- Cloud SQL (db-g1-small): ~$50
- MongoDB Atlas (M0/M10): $0-60
- Memorystore Redis (1GB): ~$50
- Load Balancer: ~$20
- Cloud Storage and network: ~$30

Total: $300-400/month

## Cost Optimization Strategies

### 1. Compute Optimization

#### GKE Cluster Optimization
```bash
# Use preemptible nodes (up to 80% cheaper)
gcloud container clusters create recommendation-cluster \
    --region=[REGION] \
    --num-nodes=2 \
    --machine-type=e2-standard-2 \
    --preemptible \
    --enable-autoscaling \
    --min-nodes=2 \
    --max-nodes=4

# Enable cluster autoscaler for off-peak scaling
gcloud container clusters update recommendation-cluster \
    --enable-autoscaling \
    --min-nodes=1 \
    --max-nodes=4
```

Potential Savings:
- Preemptible nodes: ~$120/month
- Autoscaling: ~$30-50/month

#### Pod Resource Optimization
```yaml
# Update k8s/deployment.yaml
resources:
  requests:
    memory: "256Mi"  # Reduced from 512Mi
    cpu: "100m"      # Reduced from 250m
  limits:
    memory: "512Mi"  # Reduced from 1Gi
    cpu: "200m"      # Reduced from 500m
```

### 2. Database Optimization

#### Cloud SQL Optimization
```bash
# Use shared-core instance for development
gcloud sql instances create recommendation-db \
    --database-version=POSTGRES_13 \
    --tier=db-f1-micro \
    --region=[REGION] \
    --storage-type=HDD \
    --storage-size=10GB \
    --availability-type=zonal

# Enable automatic storage size reduction
gcloud sql instances patch recommendation-db \
    --enable-storage-auto-increase \
    --enable-storage-auto-decrease
```

Potential Savings:
- Shared-core instance: ~$25/month
- HDD storage: ~$10/month

#### MongoDB Optimization
- Use MongoDB Atlas M0 (Free tier) for development
- Use M10 shared cluster for production ($60/month)
- Enable auto-scaling triggers

#### Redis Optimization
```bash
# Use smaller Redis instance
gcloud redis instances create recommendation-cache \
    --size=0.5 \
    --region=[REGION] \
    --zone=[ZONE] \
    --redis-version=redis_6_x
```

Potential Savings: ~$25/month

### 3. Network Optimization

#### Load Balancer Optimization
```bash
# Use regional load balancer instead of global
gcloud compute forwarding-rules create recommendation-lb \
    --load-balancing-scheme=EXTERNAL_MANAGED \
    --network-tier=STANDARD \
    --region=[REGION]
```

#### Cloud CDN Configuration
```bash
# Enable Cloud CDN for static content
gcloud compute backend-services update recommendation-backend \
    --enable-cdn
```

Potential Savings:
- Network tier: ~$10/month
- CDN caching: Variable based on traffic

### 4. Storage Optimization

```bash
# Set up lifecycle policies for logs and backups
gsutil lifecycle set lifecycle-config.json gs://[BUCKET_NAME]

# Content of lifecycle-config.json
{
  "rule":
  [
    {
      "action": {"type": "Delete"},
      "condition": {"age": 30}
    }
  ]
}
```

### 5. Monitoring and Logging Optimization

```bash
# Set up log exclusion filters
gcloud logging exclusions create noisy-logs \
    --description="Exclude frequent debug logs" \
    --log-filter="severity<=DEBUG"

# Set up metric retention policies
gcloud monitoring channels create \
    --display-name="Critical-Only" \
    --type="email" \
    --enabled \
    --email-address="alerts@yourdomain.com"
```

## Optimized Cost Breakdown

After implementing optimizations:
- GKE Cluster (preemptible): ~$50
- Cloud SQL (optimized): ~$25
- MongoDB Atlas (M0/M10): $0-60
- Memorystore Redis (0.5GB): ~$25
- Load Balancer (regional): ~$10
- Storage and network: ~$20

Total Optimized Cost: $130-190/month
Potential Savings: $170-210/month (>50% reduction)

## Implementation Steps

1. Development Environment
```bash
# Create cost-optimized development cluster
gcloud container clusters create dev-cluster \
    --region=[REGION] \
    --num-nodes=1 \
    --machine-type=e2-small \
    --preemptible \
    --enable-autoscaling \
    --min-nodes=1 \
    --max-nodes=2
```

2. Staging Environment
```bash
# Create cost-optimized staging cluster
gcloud container clusters create staging-cluster \
    --region=[REGION] \
    --num-nodes=2 \
    --machine-type=e2-standard-2 \
    --preemptible \
    --enable-autoscaling \
    --min-nodes=1 \
    --max-nodes=3
```

3. Production Environment
```bash
# Create cost-optimized production cluster
gcloud container clusters create prod-cluster \
    --region=[REGION] \
    --num-nodes=2 \
    --machine-type=e2-standard-2 \
    --node-locations=[ZONE-1],[ZONE-2] \
    --enable-autoscaling \
    --min-nodes=2 \
    --max-nodes=4
```

## Monitoring Cost Optimization

1. Set up budget alerts:
```bash
gcloud billing budgets create \
    --billing-account=[BILLING_ACCOUNT_ID] \
    --display-name="Monthly Budget" \
    --budget-amount=200 \
    --threshold-rules=percent=0.8 \
    --threshold-rules=percent=0.9 \
    --threshold-rules=percent=1.0
```

2. Enable cost breakdown reports:
```bash
gcloud services enable billingbudgets.googleapis.com
```

3. Set up cost monitoring dashboard:
```bash
# Create monitoring workspace
gcloud monitoring workspaces create \
    --display-name="Cost Monitoring"

# Add cost metrics
gcloud monitoring metrics-scopes create \
    --monitoring-workspace-project=[PROJECT_ID] \
    --scopes=[PROJECT_ID]
```

## Best Practices

1. Regular Cost Review
- Weekly cost analysis
- Resource utilization monitoring
- Idle resource cleanup

2. Development Practices
- Use preemptible nodes for non-critical workloads
- Implement graceful handling of preemption
- Set up auto-scaling policies

3. Resource Management
- Regular cleanup of unused resources
- Implement tagging strategy for cost allocation
- Use committed use discounts for stable workloads

4. Monitoring and Alerting
- Set up billing alerts
- Monitor resource utilization
- Track cost per service/feature

## Additional Cost-Saving Tips

1. Use Cloud Storage lifecycle policies
2. Implement caching strategies
3. Optimize container images
4. Use spot instances where applicable
5. Enable gVisor for better resource isolation
6. Implement proper tagging for cost allocation
7. Use Cloud Build's included free tier
8. Optimize CI/CD pipeline execution 