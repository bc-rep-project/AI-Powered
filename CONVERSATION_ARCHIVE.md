# Project Archive: AI-Powered Content Recommendation Engine

## Project Overview
A sophisticated recommendation system built with FastAPI and TensorFlow that provides personalized content suggestions using neural networks. The system learns from user interactions and preferences to deliver increasingly accurate recommendations.

## Repository Structure
```
.
├── app/
│   ├── api/              # API endpoints
│   │   ├── recommendations.py
│   │   ├── auth.py
│   │   ├── monitoring.py
│   │   ├── experiments.py
│   │   └── rbac.py
│   ├── core/            # Core configurations
│   │   ├── config.py
│   │   ├── monitoring.py
│   │   └── training_config.py
│   ├── models/          # Data & ML models
│   │   ├── user.py
│   │   └── neural_recommender.py
│   ├── services/        # Business logic
│   ├── training/        # ML training components
│   ├── cache/          # Caching logic
│   └── middleware/     # Custom middleware
├── frontend/          # Next.js frontend
└── tests/            # Test cases
```

## Key Components

### Backend (FastAPI)
- Neural network-based recommendation engine
- Role-based access control (RBAC)
- A/B testing capabilities
- Real-time performance monitoring
- Automatic model retraining
- High-performance caching

### Frontend (Next.js)
- Modern, responsive design
- Secure authentication
- Mobile-first approach
- Dark/Light mode
- Real-time updates
- Analytics integration

## Configuration Files

### .env
Contains all environment variables including:
- Database connections (PostgreSQL, MongoDB, Redis)
- Authentication settings
- Model configuration
- Training parameters
- Monitoring settings

### app/core/config.py
Main configuration class using pydantic-settings

### app/core/training_config.py
Neural network and training specific configurations

### app/core/monitoring.py
Logging and metrics configuration using Prometheus

## Recent Changes
1. Updated all BaseSettings imports to use pydantic-settings
2. Added comprehensive monitoring configuration
3. Implemented neural network configuration
4. Added training parameters
5. Set up metrics collection
6. Added OAuth support with authlib package
7. Fixed dependency conflicts between httpx and supabase-py
8. Corrected httpx version constraint for compatibility
9. Fixed version conflicts between authlib and httpx
10. Adjusted httpx version to match postgrest-py requirements
11. Downgraded authlib to version compatible with httpx 0.16.1
12. Added Prometheus metrics and monitoring setup
13. Added endpoint monitoring decorator
14. Added ExperimentCreate and ExperimentUpdate models

## Dependencies Added
- authlib: For OAuth authentication (version 0.15.3)
- httpx: Required by authlib and postgrest-py (version 0.16.1)
- prometheus-client: For metrics collection and monitoring
- slowapi: For rate limiting and request throttling
- limits: Required by slowapi for rate limiting implementation

## Current State
- Basic infrastructure is set up
- Database connections are configured
- Neural network model is defined
- Monitoring system is in place
- Frontend is initialized with Next.js

## Next Steps
1. Implement recommendation algorithms
2. Set up A/B testing framework
3. Add user interaction tracking
4. Implement real-time updates
5. Add analytics dashboard

## Technical Debt
1. Need to implement proper error handling
2. Add comprehensive testing
3. Set up CI/CD pipeline
4. Implement caching strategy
5. Add data validation

## Environment Setup
See README.md for detailed setup instructions.

## Related Documentation
- [Backend README](./README.md)
- [Frontend README](./frontend/README.md)
- [API Documentation](./docs/api.md)

## Recent Updates (December 24, 2024)

### Authentication and OAuth Implementation
1. Implemented Google OAuth sign-in functionality
2. Added Google sign-in button to login and registration pages
3. Updated OAuth callback handling in backend
4. Added session middleware for OAuth support
5. Fixed CORS configuration for OAuth endpoints

### Rate Limiting Implementation
1. Initially encountered issues with slowapi RateLimitExceeded import
2. Implemented custom rate limiting solution using in-memory request store
3. Added IP-based rate limiting with configurable limits and windows
4. Integrated rate limiting middleware with FastAPI application
5. Added logging for rate limit events

### Backend Fixes
1. Fixed import issues in rate limiting middleware
2. Updated slowapi version to 0.1.8 for compatibility
3. Implemented proper error handling in middleware
4. Added logging configuration for debugging
5. Fixed MongoDB connection handling

### Frontend Updates
1. Added Google sign-in button with proper styling
2. Created Google icon SVG for sign-in buttons
3. Updated API configuration for OAuth endpoints
4. Implemented OAuth callback handling
5. Added proper error handling for authentication

### Environment and Configuration
1. Added required environment variables for Google OAuth
2. Updated API endpoint configuration
3. Added session middleware configuration
4. Updated CORS settings for OAuth endpoints
5. Added proper error logging configuration

### Known Issues and Solutions
1. Fixed 401 Unauthorized errors during login
2. Resolved CORS issues with registration endpoint
3. Fixed OAuth callback handling
4. Addressed rate limiting implementation issues
5. Resolved session management problems

### Next Steps
1. Implement proper error handling for OAuth flow
2. Add comprehensive logging for debugging
3. Implement proper session management
4. Add user profile management
5. Implement proper rate limiting persistence

### Additional Technical Debt
1. Need to implement proper rate limiting persistence
2. Add comprehensive OAuth error handling
3. Implement proper session cleanup
4. Add proper monitoring for OAuth flows
5. Implement proper user management 