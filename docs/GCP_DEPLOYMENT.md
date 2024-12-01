# Google Cloud Platform Deployment Guide

This guide provides step-by-step instructions for deploying the AI Content Recommendation Engine on Google Cloud Platform.

## Prerequisites

1. Install Google Cloud SDK:
```bash
# For Windows (PowerShell)
(New-Object Net.WebClient).DownloadFile("https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe", "$env:Temp\GoogleCloudSDKInstaller.exe")
& $env:Temp\GoogleCloudSDKInstaller.exe

# For Linux/macOS
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

2. Initialize Google Cloud SDK:
```bash
gcloud init
```

## Step 1: Set Up GCP Project

1. Create a new project (or select existing):
```bash
gcloud projects create [PROJECT_ID]
gcloud config set project [PROJECT_ID]
```

2. Enable required APIs:
```bash
gcloud services enable container.googleapis.com \
    cloudbuild.googleapis.com \
    cloudresourcemanager.googleapis.com \
    compute.googleapis.com \
    servicenetworking.googleapis.com \
    sqladmin.googleapis.com \
    redis.googleapis.com \
    monitoring.googleapis.com
```

## Step 2: Set Up Database Services

1. Create Cloud SQL (PostgreSQL) instance:
```bash
gcloud sql instances create recommendation-db \
    --database-version=POSTGRES_13 \
    --tier=db-g1-small \
    --region=[REGION] \
    --storage-type=SSD \
    --storage-size=10GB \
    --backup \
    --availability-type=zonal

# Create database
gcloud sql databases create recommendation_db \
    --instance=recommendation-db

# Create user
gcloud sql users create [DB_USER] \
    --instance=recommendation-db \
    --password=[DB_PASSWORD]
```

2. Set up MongoDB using MongoDB Atlas:
   - Visit [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
   - Create M0 (free) or larger cluster
   - Configure network access for GKE cluster IP range
   - Save connection string

3. Create Redis instance:
```bash
gcloud redis instances create recommendation-cache \
    --size=1 \
    --region=[REGION] \
    --zone=[ZONE] \
    --redis-version=redis_6_x
```

## Step 3: Create GKE Cluster

```bash
gcloud container clusters create recommendation-cluster \
    --region=[REGION] \
    --num-nodes=3 \
    --machine-type=e2-standard-2 \
    --enable-autoscaling \
    --min-nodes=3 \
    --max-nodes=5 \
    --enable-autorepair \
    --enable-autoupgrade
```

## Step 4: Configure Secrets and ConfigMaps

1. Create secrets for database credentials:
```bash
kubectl create secret generic db-credentials \
    --from-literal=username=[DB_USER] \
    --from-literal=password=[DB_PASSWORD]

kubectl create secret generic mongodb-credentials \
    --from-literal=url=[MONGODB_URL]
```

2. Create ConfigMap for application configuration:
```bash
kubectl create configmap app-config \
    --from-literal=database-name=recommendation_db \
    --from-literal=redis-host=[REDIS_HOST]
```

## Step 5: Set Up Cloud Build

1. Configure Cloud Build:
```bash
# Grant Cloud Build access to GKE
gcloud projects add-iam-policy-binding [PROJECT_ID] \
    --member="serviceAccount:$(gcloud projects describe $PROJECT_ID \
    --format='get(projectNumber)')@cloudbuild.gserviceaccount.com" \
    --role="roles/container.developer"
```

2. Create Cloud Build trigger:
```bash
gcloud beta builds triggers create github \
    --repo-name=[REPO_NAME] \
    --repo-owner=[REPO_OWNER] \
    --branch-pattern="^main$" \
    --build-config=cloudbuild.yaml
```

## Step 6: Deploy Application

1. Update `k8s/deployment.yaml` with correct image path:
```yaml
image: gcr.io/[PROJECT_ID]/recommendation-engine:latest
```

2. Deploy to GKE:
```bash
kubectl apply -f k8s/
```

## Step 7: Set Up Monitoring

1. Configure Cloud Monitoring:
```bash
# Install Cloud Operations agent
kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-customize/master/prometheus-to-sd/prometheus-to-sd-kube.yaml
```

2. Set up Cloud Logging:
```bash
# View application logs
gcloud logging read "resource.type=k8s_container AND resource.labels.cluster_name=recommendation-cluster"
```

## Step 8: Set Up Load Balancer and SSL

1. Create SSL certificate:
```bash
gcloud compute ssl-certificates create recommendation-cert \
    --domains=[YOUR_DOMAIN]
```

2. Configure HTTPS load balancer:
```bash
gcloud compute forwarding-rules create recommendation-https \
    --load-balancing-scheme=EXTERNAL \
    --network-tier=PREMIUM \
    --address=[IP_ADDRESS] \
    --target-https-proxy=recommendation-proxy \
    --ports=443
```

## Maintenance and Scaling

1. Scale the cluster:
```bash
# Manual scaling
gcloud container clusters resize recommendation-cluster \
    --num-nodes=[NODE_COUNT] \
    --region=[REGION]

# Update autoscaling
gcloud container clusters update recommendation-cluster \
    --enable-autoscaling \
    --min-nodes=[MIN_NODES] \
    --max-nodes=[MAX_NODES] \
    --region=[REGION]
```

2. Update application:
```bash
# Trigger new build
gcloud builds submit --config cloudbuild.yaml

# Rolling update
kubectl set image deployment/recommendation-engine \
    recommendation-engine=gcr.io/[PROJECT_ID]/recommendation-engine:[NEW_VERSION]
```

3. Monitor costs:
```bash
# View current month's costs
gcloud billing accounts list
gcloud beta billing projects describe [PROJECT_ID]
```

## Estimated Costs (Monthly)

- GKE Cluster (3 nodes, e2-standard-2): ~$150
- Cloud SQL (db-g1-small): ~$50
- MongoDB Atlas (M0): Free (or M10: ~$60)
- Memorystore Redis (1GB): ~$50
- Load Balancer: ~$20
- Cloud Storage and network: ~$30

Total estimated cost: $300-400/month

## Troubleshooting

1. Check pod status:
```bash
kubectl get pods
kubectl describe pod [POD_NAME]
kubectl logs [POD_NAME]
```

2. Check service status:
```bash
kubectl get services
kubectl describe service recommendation-engine
```

3. Database connectivity:
```bash
# Test PostgreSQL connection
gcloud sql connect recommendation-db --user=[DB_USER]

# Test Redis connection
gcloud redis instances describe recommendation-cache
```

4. View application logs:
```bash
gcloud logging read "resource.type=k8s_container AND resource.labels.cluster_name=recommendation-cluster"
```

## Security Best Practices

1. Enable Cloud Security Command Center:
```bash
gcloud services enable securitycenter.googleapis.com
```

2. Configure VPC Service Controls:
```bash
gcloud services vpc-service-controls enable
```

3. Set up Cloud Armor:
```bash
gcloud compute security-policies create recommendation-policy
gcloud compute security-policies rules create 1000 \
    --security-policy recommendation-policy \
    --expression "evaluatePreconfiguredExpr('xss-stable')" \
    --action "deny-403"
```

## Support and Resources

- GCP Console: https://console.cloud.google.com
- GKE Documentation: https://cloud.google.com/kubernetes-engine/docs
- Cloud SQL Documentation: https://cloud.google.com/sql/docs
- Cloud Monitoring: https://cloud.google.com/monitoring 