"""API Documentation descriptions and examples."""

# Tags descriptions
TAGS = {
    "auth": {
        "name": "Authentication",
        "description": "User authentication and authorization endpoints. Use these endpoints to register, login, and manage user sessions."
    },
    "recommendations": {
        "name": "Recommendations",
        "description": "Content recommendation endpoints. Get personalized recommendations and record user interactions."
    },
    "experiments": {
        "name": "A/B Testing",
        "description": "Experiment management endpoints. Create and manage A/B tests to evaluate different recommendation algorithms."
    },
    "monitoring": {
        "name": "Monitoring",
        "description": "System monitoring endpoints. Track system health, performance metrics, and recommendation quality."
    }
}

# Authentication examples
AUTH_EXAMPLES = {
    "register": {
        "summary": "Register a new user",
        "description": """
        Register a new user account with email and password.
        The email must be unique and the password must be at least 8 characters long.
        """,
        "request_example": {
            "email": "user@example.com",
            "username": "john_doe",
            "password": "securepassword123"
        },
        "response_example": {
            "id": "user123",
            "email": "user@example.com",
            "username": "john_doe",
            "is_active": True,
            "created_at": "2023-01-01T00:00:00Z"
        }
    },
    "login": {
        "summary": "Login to get access token",
        "description": """
        Login with email and password to get an access token.
        Use this token in the Authorization header for subsequent requests.
        """,
        "request_example": {
            "username": "user@example.com",
            "password": "securepassword123"
        },
        "response_example": {
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            "token_type": "bearer"
        }
    }
}

# Recommendation examples
RECOMMENDATION_EXAMPLES = {
    "get_recommendations": {
        "summary": "Get personalized recommendations",
        "description": """
        Get personalized content recommendations based on user preferences and behavior.
        The recommendations are generated using machine learning algorithms and user interaction history.
        """,
        "parameters": {
            "n_recommendations": "Number of recommendations to return (default: 10)"
        },
        "response_example": {
            "recommendations": [
                {
                    "content_id": "item123",
                    "title": "Example Content",
                    "score": 0.95,
                    "explanation": "Based on your interests in similar content"
                }
            ]
        }
    },
    "record_interaction": {
        "summary": "Record user interaction",
        "description": """
        Record a user's interaction with content (e.g., view, like, purchase).
        These interactions are used to improve future recommendations.
        """,
        "request_example": {
            "user_id": "user123",
            "content_id": "item123",
            "interaction_type": "view",
            "context": {
                "device": "mobile",
                "location": "home"
            }
        }
    }
}

# Experiment examples
EXPERIMENT_EXAMPLES = {
    "create_experiment": {
        "summary": "Create A/B test experiment",
        "description": """
        Create a new A/B testing experiment to evaluate different recommendation algorithms or strategies.
        Define variants and their traffic allocation.
        """,
        "request_example": {
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
        }
    },
    "record_event": {
        "summary": "Record experiment event",
        "description": """
        Record events (impressions, clicks, conversions) for experiment tracking.
        These events are used to calculate experiment metrics and determine winners.
        """,
        "request_example": {
            "user_id": "user123",
            "experiment_id": "exp123",
            "variant_id": "treatment",
            "event_type": "click",
            "metadata": {
                "item_id": "item123",
                "position": 1
            }
        }
    },
    "get_results": {
        "summary": "Get experiment results",
        "description": """
        Get metrics and results for an experiment.
        Includes key metrics like CTR, conversion rate, and revenue impact.
        """,
        "response_example": {
            "control": {
                "impressions": 1000,
                "clicks": 100,
                "conversions": 10,
                "ctr": 0.1,
                "conversion_rate": 0.1
            },
            "treatment": {
                "impressions": 1000,
                "clicks": 120,
                "conversions": 15,
                "ctr": 0.12,
                "conversion_rate": 0.125
            }
        }
    }
}

# Monitoring examples
MONITORING_EXAMPLES = {
    "get_metrics": {
        "summary": "Get system metrics",
        "description": """
        Get detailed system metrics including request rates, response times,
        recommendation quality, and cache performance.
        """,
        "response_example": {
            "requests": {
                "total": 10000,
                "success_rate": 0.99
            },
            "response_times": {
                "p50": 100,
                "p95": 250,
                "p99": 500
            },
            "recommendation_quality": {
                "precision": 0.85,
                "recall": 0.75,
                "ndcg": 0.8
            }
        }
    },
    "get_health": {
        "summary": "Get system health status",
        "description": """
        Get detailed health status of the system including component status,
        error rates, and performance indicators.
        """,
        "response_example": {
            "status": "healthy",
            "components": {
                "database": "healthy",
                "cache": "healthy",
                "model_service": "healthy"
            },
            "error_rate": 0.001,
            "cache_hit_rate": 0.95
        }
    }
} 