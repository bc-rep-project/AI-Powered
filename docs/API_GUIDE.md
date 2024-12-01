# AI Content Recommendation Engine API Guide

## Introduction

The AI Content Recommendation Engine provides personalized content recommendations using advanced machine learning algorithms. This guide explains how to use the API effectively.

## Authentication

All API endpoints require authentication using JWT tokens. Follow these steps:

1. Register a new user:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
         "email": "user@example.com",
         "username": "john_doe",
         "password": "securepassword123"
     }'
```

2. Get an access token:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=user@example.com&password=securepassword123"
```

3. Use the token in subsequent requests:
```bash
curl -X GET "http://localhost:8000/api/v1/recommendations" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

## Recommendations

### Get Recommendations

Get personalized content recommendations:

```bash
curl -X POST "http://localhost:8000/api/v1/recommendations" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
         "n_recommendations": 10
     }'
```

### Record Interaction

Record user interactions with content:

```bash
curl -X POST "http://localhost:8000/api/v1/interactions" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
         "content_id": "item123",
         "interaction_type": "view",
         "context": {
             "device": "mobile",
             "location": "home"
         }
     }'
```

## A/B Testing

### Create Experiment

Create a new A/B test:

```bash
curl -X POST "http://localhost:8000/api/v1/experiments" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
         "name": "New Algorithm Test",
         "description": "Testing neural collaborative filtering",
         "status": "draft",
         "variants": [
             {
                 "id": "control",
                 "name": "Current Algorithm",
                 "description": "Matrix Factorization",
                 "config": {"algorithm": "matrix_factorization"},
                 "traffic_percentage": 0.5
             },
             {
                 "id": "treatment",
                 "name": "New Algorithm",
                 "description": "Neural Collaborative Filtering",
                 "config": {"algorithm": "neural_collaborative"},
                 "traffic_percentage": 0.5
             }
         ]
     }'
```

### Record Event

Record experiment events:

```bash
curl -X POST "http://localhost:8000/api/v1/experiments/events" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
         "experiment_id": "exp123",
         "variant_id": "treatment",
         "event_type": "click",
         "metadata": {
             "item_id": "item123",
             "position": 1
         }
     }'
```

### Get Results

Get experiment results:

```bash
curl -X GET "http://localhost:8000/api/v1/experiments/{experiment_id}/results" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

## Monitoring

### System Metrics

Get system performance metrics:

```bash
curl -X GET "http://localhost:8000/api/v1/monitoring/metrics" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

### Health Status

Get detailed system health status:

```bash
curl -X GET "http://localhost:8000/api/v1/monitoring/health/detailed" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

## Best Practices

1. **Rate Limiting**: The API has rate limits. Use exponential backoff for retries.
2. **Caching**: Cache recommendations locally when appropriate.
3. **Batch Processing**: Use batch endpoints for multiple interactions.
4. **Error Handling**: Handle HTTP errors appropriately:
   - 400: Bad request - Check your input
   - 401: Unauthorized - Refresh your token
   - 403: Forbidden - Check permissions
   - 429: Too Many Requests - Implement backoff
   - 500: Server Error - Contact support

## Models

### UserProfile

```json
{
    "user_id": "string",
    "preferences": {
        "categories": ["tech", "science"],
        "tags": ["AI", "ML"]
    },
    "interaction_history": [
        {
            "content_id": "string",
            "interaction_type": "string",
            "timestamp": "datetime"
        }
    ]
}
```

### ContentItem

```json
{
    "content_id": "string",
    "title": "string",
    "description": "string",
    "metadata": {
        "category": "string",
        "tags": ["string"]
    },
    "features": {
        "embedding": [0.1, 0.2, 0.3]
    }
}
```

### Recommendation

```json
{
    "user_id": "string",
    "content_items": [
        {
            "content_id": "string",
            "score": 0.95,
            "explanation": "string"
        }
    ]
}
```

## Support

For API support:
- Email: api-support@example.com
- Documentation: https://docs.example.com
- Status Page: https://status.example.com 