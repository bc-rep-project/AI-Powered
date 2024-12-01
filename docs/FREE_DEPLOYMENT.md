# Free Deployment Guide

This guide explains how to deploy the AI Content Recommendation Engine using free hosting options.

## Option 1: Railway.app (Recommended)

Railway.app offers a generous free tier that includes:
- $5 worth of resources free per month
- Automatic deployments from GitHub
- Built-in PostgreSQL and Redis
- Custom domains
- Automatic HTTPS

### Setup Steps

1. Create a Railway account:
   - Go to [Railway.app](https://railway.app)
   - Sign up with your GitHub account

2. Create a new project:
   ```bash
   # Install Railway CLI
   npm i -g @railway/cli

   # Login to Railway
   railway login

   # Create a new project
   railway init
   ```

3. Add PostgreSQL database:
   ```bash
   railway add postgresql
   ```

4. Add Redis:
   ```bash
   railway add redis
   ```

5. Configure environment variables:
   ```bash
   # Set required environment variables
   railway vars set POSTGRES_USER=postgres
   railway vars set POSTGRES_DB=recommendation_engine
   railway vars set SECRET_KEY=your-secret-key
   ```

6. Deploy:
   ```bash
   railway up
   ```

### GitHub Actions Setup

1. Get Railway Token:
   - Go to Railway Dashboard → Settings → Tokens
   - Generate new token

2. Add to GitHub Secrets:
   - Go to your GitHub repository → Settings → Secrets
   - Add new secret named `RAILWAY_TOKEN`
   - Paste your Railway token

3. Push code to trigger deployment:
   ```bash
   git add .
   git commit -m "Initial deployment"
   git push origin main
   ```

## Option 2: Heroku (Alternative)

Heroku offers a basic free tier that includes:
- Free dyno hours
- PostgreSQL starter tier
- Redis starter tier

### Setup Steps

1. Create Heroku account:
   - Go to [Heroku](https://heroku.com)
   - Sign up for a free account

2. Install Heroku CLI:
   ```bash
   # Windows (PowerShell)
   winget install Heroku.CLI

   # macOS
   brew tap heroku/brew && brew install heroku

   # Ubuntu
   sudo snap install heroku --classic
   ```

3. Login and create app:
   ```bash
   heroku login
   heroku create ai-recommendation-engine
   ```

4. Add databases:
   ```bash
   heroku addons:create heroku-postgresql:hobby-dev
   heroku addons:create heroku-redis:hobby-dev
   ```

5. Configure environment:
   ```bash
   heroku config:set SECRET_KEY=your-secret-key
   heroku config:set PYTHON_VERSION=3.9
   ```

6. Deploy:
   ```bash
   git push heroku main
   ```

## Option 3: Google Cloud Run (Free Tier)

Google Cloud Run offers a generous free tier:
- 2 million requests per month
- 360,000 GB-seconds of compute
- 180,000 vCPU-seconds

### Setup Steps

1. Create Google Cloud account:
   - Go to [Google Cloud](https://cloud.google.com)
   - Sign up with free credits ($300)

2. Install Google Cloud SDK:
   ```bash
   # Download and install from:
   # https://cloud.google.com/sdk/docs/install
   ```

3. Initialize and deploy:
   ```bash
   gcloud init
   gcloud run deploy
   ```

## Database Options (Free Tiers)

1. **PostgreSQL**:
   - ElephantSQL (Free 20MB)
   - Supabase (Free 500MB)
   - Railway.app PostgreSQL (Included in free tier)

2. **MongoDB**:
   - MongoDB Atlas (Free 512MB)
   - Railway.app MongoDB (Included in free tier)

3. **Redis**:
   - Redis Labs (Free 30MB)
   - Upstash (Free tier available)

## Minimizing Resource Usage

To stay within free tiers:

1. Optimize container:
   ```dockerfile
   # Use slim base image
   FROM python:3.9-slim

   # Minimize layers
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   COPY . .
   ```

2. Reduce dependencies:
   ```python
   # Use lighter alternatives
   fastapi-limiter instead of redis
   sqlite instead of postgresql (for development)
   ```

3. Enable caching:
   ```python
   # Add caching headers
   from fastapi.responses import Response

   @app.get("/recommendations")
   async def get_recommendations():
       response = Response(content=...)
       response.headers["Cache-Control"] = "max-age=3600"
       return response
   ```

## Monitoring Free Resources

1. Railway Dashboard:
   - Monitor usage in Railway dashboard
   - Set up usage alerts

2. Heroku Dashboard:
   - Check dyno hours
   - Monitor add-on usage

3. Google Cloud Console:
   - Monitor Cloud Run usage
   - Set up billing alerts

## Common Issues and Solutions

1. **Memory Issues**:
   - Reduce worker count
   - Implement pagination
   - Use streaming responses

2. **CPU Limits**:
   - Implement caching
   - Reduce batch sizes
   - Optimize queries

3. **Storage Limits**:
   - Use file compression
   - Implement data cleanup
   - Use external storage

## Support and Resources

- Railway Documentation: https://docs.railway.app
- Heroku Dev Center: https://devcenter.heroku.com
- Google Cloud Run: https://cloud.google.com/run/docs
- FastAPI Deployment: https://fastapi.tiangolo.com/deployment/ 