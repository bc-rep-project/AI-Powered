import os
from fastapi import FastAPI, HTTPException, Depends, status, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict
import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
import uuid
from src.models.recommendation_model import RecommendationModel
from src.models.data_models import Content, Interaction, UserProfile, RecommendationHistory
from src.database import Database
from src.monitoring import Monitoring, ExperimentType
from src.visualization import Visualization
from fastapi.responses import StreamingResponse
from io import BytesIO
import json
import asyncio
from fastapi import WebSocket
from fastapi import WebSocketDisconnect
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import plotly.express as px
from src.data_export import DataExport

# Initialize FastAPI app
app = FastAPI(title="AI Content Recommendation API",
             description="Provides personalized content recommendations based on user behavior and preferences.")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ai-powered-content-recommendation-frontend.vercel.app",
        "https://ai-powered-content-recommendation-frontend-kslis1lqp.vercel.app",
        "*"  # During development - remove in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
@app.on_event("startup")
async def startup_db_client():
    await Database.connect_db()

@app.on_event("shutdown")
async def shutdown_db_client():
    await Database.close_db()

# Initialize recommendation model
recommendation_model = RecommendationModel()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secure-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# Helper functions
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30)))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_user_by_email(email: str):
    return await Database.db.users.find_one({"email": email})

async def authenticate_user(email: str, password: str):
    user = await get_user_by_email(email)
    if not user:
        return False
    if not pwd_context.verify(password, user["password"]):
        return False
    return user

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    user = await get_user_by_email(email)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# Routes
@app.get("/")
async def root():
    return {
        "message": "Welcome to AI Content Recommendation API",
        "status": "online",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

# Authentication routes
@app.post("/auth/register")
async def register(user_data: UserProfile):
    try:
        existing_user = await get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        user_dict = user_data.dict()
        user_dict["id"] = str(uuid.uuid4())
        user_dict["created_at"] = datetime.utcnow()
        
        await Database.db.users.insert_one(user_dict)
        access_token = create_access_token({"sub": user_data.email})
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/auth/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token({"sub": user["email"]})
    return {"access_token": access_token, "token_type": "bearer"}

# Content routes
@app.post("/content")
async def create_content(content: Content, current_user: dict = Depends(get_current_user)):
    content_dict = content.dict()
    await Database.db.content.insert_one(content_dict)
    return content_dict

@app.get("/content/{content_id}")
async def get_content(content_id: str, current_user: dict = Depends(get_current_user)):
    content = await Database.db.content.find_one({"id": content_id})
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return content

# Recommendation routes
@app.get("/recommendations/trending")
async def get_trending_content(
    time_window: int = Query(24, description="Time window in hours"),
    limit: int = Query(10, description="Number of items to return"),
    current_user: dict = Depends(get_current_user)
):
    """Get trending content based on recent interactions"""
    trending = await Database.get_trending_content(limit=limit, time_window_hours=time_window)
    return {
        "trending": trending,
        "time_window_hours": time_window,
        "explanation": f"Top {limit} trending items in the last {time_window} hours"
    }

@app.get("/recommendations/category/{category}")
async def get_category_recommendations(
    category: str,
    limit: int = Query(5, description="Number of items to return"),
    current_user: dict = Depends(get_current_user)
):
    """Get recommendations for a specific content category"""
    recommendations = await Database.get_category_recommendations(
        user_id=current_user["id"],
        category=category,
        limit=limit
    )
    return {
        "recommendations": recommendations,
        "category": category,
        "explanation": f"Recommended {category} content based on your preferences"
    }

@app.get("/recommendations/personalized")
async def get_personalized_recommendations(
    limit: int = Query(5, description="Number of items to return"),
    current_user: dict = Depends(get_current_user)
):
    """Get personalized recommendations for the current user"""
    # Get user's interactions
    interactions = await Database.db.interactions.find(
        {"user_id": current_user["id"]}
    ).to_list(1000)
    
    if not interactions:
        # Cold start: return trending items
        trending = await Database.get_trending_content(limit=limit)
        return {
            "recommendations": trending,
            "type": "trending",
            "explanation": "Popular items for new users"
        }
    
    # Get personalized recommendations
    recommendations = recommendation_model.get_recommendations(current_user["id"], limit)
    
    # Record recommendation history
    history = RecommendationHistory(
        user_id=current_user["id"],
        content_ids=[rec["content_id"] for rec in recommendations],
        algorithm_version="1.0",
        scores=[rec["score"] for rec in recommendations]
    )
    await Database.db.recommendation_history.insert_one(history.dict())
    
    # Fetch full content details
    content_ids = [rec["content_id"] for rec in recommendations]
    recommended_content = await Database.db.content.find(
        {"id": {"$in": content_ids}}
    ).to_list(limit)
    
    return {
        "recommendations": recommended_content,
        "type": "personalized",
        "explanation": "Based on your viewing history and preferences"
    }

# Interaction routes
@app.post("/interactions")
async def record_interaction(interaction: Interaction, current_user: dict = Depends(get_current_user)):
    """Record a user interaction with content"""
    interaction_dict = interaction.dict()
    interaction_dict["user_id"] = current_user["id"]
    
    # Update interaction counts for content
    await Database.db.content.update_one(
        {"id": interaction.content_id},
        {"$inc": {"interaction_count": 1}}
    )
    
    # Record the interaction
    await Database.db.interactions.insert_one(interaction_dict)
    
    # Update user's interaction history
    await Database.db.users.update_one(
        {"id": current_user["id"]},
        {
            "$push": {"interaction_history": interaction_dict["id"]},
            "$set": {"last_active": datetime.utcnow()}
        }
    )
    
    return interaction_dict 

# Monitoring routes
@app.get("/metrics/recommendations/{user_id}")
async def get_recommendation_metrics(
    user_id: str,
    time_window: int = Query(24, description="Time window in hours"),
    current_user: dict = Depends(get_current_user)
):
    """Get recommendation metrics for a user"""
    # Get recent recommendations
    recommendations = await Database.db.recommendation_history.find({
        "user_id": user_id,
        "timestamp": {
            "$gte": datetime.utcnow() - timedelta(hours=time_window)
        }
    }).to_list(None)
    
    if not recommendations:
        return {
            "metrics": {
                "total_recommendations": 0,
                "clicks": 0,
                "conversions": 0,
                "ctr": 0,
                "conversion_rate": 0
            },
            "time_window_hours": time_window
        }
    
    recommendation_ids = []
    for rec in recommendations:
        recommendation_ids.extend(rec["content_ids"])
    
    metrics = await Monitoring.track_recommendation_metrics(
        user_id=user_id,
        recommendation_ids=recommendation_ids,
        time_window=time_window
    )
    
    return {
        "metrics": metrics,
        "time_window_hours": time_window
    }

@app.get("/metrics/engagement/{user_id}")
async def get_user_engagement_metrics(
    user_id: str,
    days: int = Query(30, description="Number of days to analyze"),
    current_user: dict = Depends(get_current_user)
):
    """Get user engagement metrics"""
    metrics = await Monitoring.get_user_engagement(user_id, days)
    return {
        "engagement_metrics": metrics,
        "days_analyzed": days
    }

# A/B Testing routes
@app.post("/experiments/create")
async def create_ab_test(
    name: str,
    experiment_type: ExperimentType,
    variants: List[Dict],
    description: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Create a new A/B test experiment"""
    test = await Monitoring.create_ab_test(
        name=name,
        experiment_type=experiment_type,
        variants=variants,
        description=description
    )
    return {"message": "A/B test created successfully", "test": test}

@app.get("/experiments/{test_name}/results")
async def get_experiment_results(
    test_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Get results for an A/B test experiment"""
    results = await Monitoring.get_ab_test_results(test_name)
    if not results:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"test_name": test_name, "results": results}

@app.post("/experiments/{test_name}/track")
async def track_experiment_metrics(
    test_name: str,
    variant_id: str,
    metrics: Dict,
    current_user: dict = Depends(get_current_user)
):
    """Track metrics for an experiment variant"""
    await Monitoring.track_variant_performance(
        test_name=test_name,
        variant_id=variant_id,
        user_id=current_user["id"],
        metrics=metrics
    )
    return {"message": "Metrics tracked successfully"}

# Example of using A/B testing with recommendations
@app.get("/recommendations/ab_test")
async def get_ab_test_recommendations(
    test_name: str = Query(..., description="Name of the A/B test"),
    current_user: dict = Depends(get_current_user)
):
    """Get recommendations with A/B testing"""
    # Get the active test
    test = await Database.db.ab_tests.find_one({
        "name": test_name,
        "status": "active"
    })
    
    if not test:
        raise HTTPException(status_code=404, detail="A/B test not found")
    
    # Randomly assign user to a variant if not already assigned
    user_variant = await Database.db.user_variants.find_one({
        "user_id": current_user["id"],
        "test_name": test_name
    })
    
    if not user_variant:
        import random
        variant = random.choice(test["variants"])
        user_variant = {
            "user_id": current_user["id"],
            "test_name": test_name,
            "variant_id": variant["id"]
        }
        await Database.db.user_variants.insert_one(user_variant)
    
    # Get recommendations based on variant
    variant = next(v for v in test["variants"] if v["id"] == user_variant["variant_id"])
    
    if variant["type"] == "algorithm":
        # Use different recommendation algorithms based on variant
        if variant["algorithm"] == "collaborative":
            recommendations = await get_personalized_recommendations(limit=10, current_user=current_user)
        elif variant["algorithm"] == "content_based":
            recommendations = await get_category_recommendations("all", limit=10, current_user=current_user)
        else:
            recommendations = await get_trending_content(limit=10, current_user=current_user)
    
    # Track the recommendations for this variant
    await Monitoring.track_variant_performance(
        test_name=test_name,
        variant_id=variant["id"],
        user_id=current_user["id"],
        metrics={
            "recommendations_shown": len(recommendations["recommendations"]),
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    return {
        "recommendations": recommendations["recommendations"],
        "variant": variant["id"],
        "test_name": test_name
    }

# Enhanced Dashboard Routes
@app.get("/dashboard/engagement/{user_id}")
async def get_engagement_dashboard(
    user_id: str,
    days: int = Query(30, description="Number of days to analyze"),
    include_heatmap: bool = Query(True, description="Include hourly activity heatmap"),
    current_user: dict = Depends(get_current_user)
):
    """Get enhanced user engagement dashboard data"""
    dashboard_data = await Visualization.generate_engagement_chart(
        user_id=user_id,
        days=days,
        include_heatmap=include_heatmap
    )
    return dashboard_data

@app.get("/dashboard/realtime")
async def get_realtime_dashboard(
    minutes: int = Query(60, description="Number of minutes to analyze"),
    current_user: dict = Depends(get_current_user)
):
    """Get real-time dashboard data"""
    dashboard_data = await Visualization.generate_real_time_dashboard(minutes)
    return dashboard_data

@app.get("/dashboard/recommendations/insights")
async def get_recommendation_insights(
    days: int = Query(30, description="Number of days to analyze"),
    current_user: dict = Depends(get_current_user)
):
    """Get advanced recommendation insights"""
    insights = await Visualization.generate_recommendation_insights(days)
    return insights

@app.get("/dashboard/export/{chart_type}")
async def export_dashboard_chart(
    chart_type: str,
    user_id: str,
    format: str = Query("png", description="Export format (png, jpg, pdf)"),
    current_user: dict = Depends(get_current_user)
):
    """Export dashboard chart as image"""
    try:
        if chart_type == "engagement":
            data = await Visualization.generate_engagement_chart(user_id)
            chart_data = json.loads(data["daily_activity"])
        elif chart_type == "recommendations":
            data = await Visualization.generate_recommendation_insights(30)
            chart_data = json.loads(data["algorithm_comparison"])
        else:
            raise HTTPException(status_code=400, detail="Invalid chart type")
        
        # Create figure from chart data
        fig = go.Figure(chart_data)
        
        # Export as image
        img_bytes = Visualization.export_chart(fig, format=format)
        
        return StreamingResponse(
            BytesIO(img_bytes),
            media_type=f"image/{format}",
            headers={
                "Content-Disposition": f'attachment; filename="dashboard_{chart_type}.{format}"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time updates
@app.websocket("/ws/dashboard/realtime")
async def websocket_realtime_dashboard(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Send real-time dashboard updates every 5 seconds
            dashboard_data = await Visualization.generate_real_time_dashboard(minutes=60)
            await websocket.send_json(dashboard_data)
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass

# User Segmentation Routes
@app.get("/analytics/user-segments")
async def get_user_segments(
    days: int = Query(30, description="Number of days to analyze"),
    n_segments: int = Query(4, description="Number of user segments to create"),
    current_user: dict = Depends(get_current_user)
):
    """Get user segmentation analysis"""
    segments = await Visualization.generate_user_segments(days, n_segments)
    return segments

@app.get("/analytics/content/{content_id}")
async def get_content_analysis(
    content_id: str,
    days: int = Query(30, description="Number of days to analyze"),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed content performance analysis"""
    analysis = await Visualization.generate_content_drill_down(content_id, days)
    return analysis

@app.get("/analytics/algorithm/{algorithm_version}")
async def get_algorithm_analysis(
    algorithm_version: str,
    days: int = Query(30, description="Number of days to analyze"),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed algorithm performance analysis"""
    analysis = await Visualization.generate_recommendation_drill_down(algorithm_version, days)
    return analysis

# Interactive Dashboard Routes
@app.get("/dashboard/interactive")
async def get_interactive_dashboard(
    start_date: datetime = Query(None),
    end_date: datetime = Query(None),
    content_type: Optional[str] = Query(None),
    user_segment: Optional[int] = Query(None),
    algorithm_version: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Get interactive dashboard with filters"""
    filters = {
        "start_date": start_date or (datetime.utcnow() - timedelta(days=30)),
        "end_date": end_date or datetime.utcnow(),
        "content_type": content_type,
        "user_segment": user_segment,
        "algorithm_version": algorithm_version
    }
    
    # Get user segments if needed
    user_segments = None
    if user_segment is not None:
        user_segments = await Visualization.generate_user_segments()
    
    # Get filtered recommendations
    query = {
        "timestamp": {
            "$gte": filters["start_date"],
            "$lte": filters["end_date"]
        }
    }
    
    if algorithm_version:
        query["algorithm_version"] = algorithm_version
    
    recommendations = await Database.db.recommendation_history.find(query).to_list(None)
    
    # Get filtered content interactions
    interaction_query = {
        "timestamp": {
            "$gte": filters["start_date"],
            "$lte": filters["end_date"]
        }
    }
    
    if content_type:
        content_ids = await Database.db.content.distinct(
            "id",
            {"type": content_type}
        )
        interaction_query["content_id"] = {"$in": content_ids}
    
    if user_segment is not None and user_segments:
        segment_user_ids = [
            user["user_id"] 
            for user in user_segments["user_segments"] 
            if user["segment"] == user_segment
        ]
        interaction_query["user_id"] = {"$in": segment_user_ids}
    
    interactions = await Database.db.interactions.find(interaction_query).to_list(None)
    
    # Generate visualizations
    df_interactions = pd.DataFrame(interactions) if interactions else pd.DataFrame()
    df_recommendations = pd.DataFrame(recommendations) if recommendations else pd.DataFrame()
    
    visualizations = {}
    
    if not df_interactions.empty:
        # Interaction trends
        df_interactions["timestamp"] = pd.to_datetime(df_interactions["timestamp"])
        daily_interactions = df_interactions.groupby(
            df_interactions["timestamp"].dt.date
        ).size().reset_index()
        daily_interactions.columns = ["date", "count"]
        
        fig_trends = px.line(
            daily_interactions,
            x="date",
            y="count",
            title="Daily Interactions"
        )
        visualizations["interaction_trends"] = fig_trends.to_json()
        
        # Interaction types distribution
        interaction_types = df_interactions["interaction_type"].value_counts()
        fig_types = px.pie(
            values=interaction_types.values,
            names=interaction_types.index,
            title="Interaction Types Distribution"
        )
        visualizations["interaction_types"] = fig_types.to_json()
    
    if not df_recommendations.empty:
        # Algorithm performance
        df_recommendations["timestamp"] = pd.to_datetime(df_recommendations["timestamp"])
        performance = df_recommendations.groupby("algorithm_version").agg({
            "scores": lambda x: np.mean([score for scores in x for score in scores])
        }).reset_index()
        
        fig_performance = px.bar(
            performance,
            x="algorithm_version",
            y="scores",
            title="Algorithm Performance Comparison"
        )
        visualizations["algorithm_performance"] = fig_performance.to_json()
    
    return {
        "visualizations": visualizations,
        "summary": {
            "total_interactions": len(df_interactions) if not df_interactions.empty else 0,
            "total_recommendations": len(df_recommendations) if not df_recommendations.empty else 0,
            "unique_users": df_interactions["user_id"].nunique() if not df_interactions.empty else 0,
            "unique_content": df_interactions["content_id"].nunique() if not df_interactions.empty else 0
        },
        "filters": filters
    }

# Data Export Routes
@app.get("/export/data/{data_type}")
async def export_data(
    data_type: str,
    format: str = Query("csv", description="Export format (csv, excel, json)"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    user_id: Optional[str] = Query(None),
    content_id: Optional[str] = Query(None),
    interaction_type: Optional[str] = Query(None),
    algorithm_version: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Export data in various formats"""
    try:
        filters = {
            "start_date": start_date,
            "end_date": end_date,
            "user_id": user_id,
            "content_id": content_id,
            "interaction_type": interaction_type,
            "algorithm_version": algorithm_version
        }
        
        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}
        
        output, content_type, filename = await DataExport.export_data(
            data_type=data_type,
            format=format,
            filters=filters
        )
        
        return StreamingResponse(
            BytesIO(output),
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/export/dashboard/{dashboard_type}")
async def export_dashboard(
    dashboard_type: str,
    format: str = Query("pdf", description="Export format (pdf, png)"),
    content_id: Optional[str] = Query(None),
    days: int = Query(30, description="Number of days to analyze"),
    current_user: dict = Depends(get_current_user)
):
    """Export dashboard as PDF or image"""
    try:
        filters = {
            "content_id": content_id,
            "days": days
        }
        
        output = await DataExport.export_dashboard(
            dashboard_type=dashboard_type,
            format=format,
            filters=filters
        )
        
        filename = f"dashboard_{dashboard_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
        content_type = f"application/{format}"
        
        return StreamingResponse(
            BytesIO(output),
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Custom Visualization Routes
@app.post("/visualizations/custom")
async def create_custom_visualization(
    chart_type: str = Query(..., description="Type of chart to create"),
    data_type: str = Query(..., description="Type of data to visualize"),
    metrics: List[str] = Query(..., description="Metrics to include"),
    filters: Dict = Body({}, description="Data filters"),
    customization: Dict = Body({}, description="Visual customization options"),
    current_user: dict = Depends(get_current_user)
):
    """Create custom visualization"""
    try:
        # Get data
        if data_type == "interactions":
            data = await DataExport._get_interaction_data(filters)
        elif data_type == "recommendations":
            data = await DataExport._get_recommendation_data(filters)
        elif data_type == "user_segments":
            data = await DataExport._get_user_segment_data(filters)
        else:
            raise ValueError(f"Unsupported data type: {data_type}")
        
        df = pd.DataFrame(data)
        
        # Create visualization
        if chart_type == "line":
            fig = px.line(
                df,
                x=metrics[0],
                y=metrics[1:],
                title=customization.get("title", "Custom Line Chart")
            )
        elif chart_type == "bar":
            fig = px.bar(
                df,
                x=metrics[0],
                y=metrics[1:],
                title=customization.get("title", "Custom Bar Chart")
            )
        elif chart_type == "scatter":
            fig = px.scatter(
                df,
                x=metrics[0],
                y=metrics[1],
                color=metrics[2] if len(metrics) > 2 else None,
                title=customization.get("title", "Custom Scatter Plot")
            )
        elif chart_type == "pie":
            fig = px.pie(
                df,
                values=metrics[0],
                names=metrics[1],
                title=customization.get("title", "Custom Pie Chart")
            )
        else:
            raise ValueError(f"Unsupported chart type: {chart_type}")
        
        # Apply customization
        if "color_scheme" in customization:
            fig.update_traces(marker_color=customization["color_scheme"])
        if "layout" in customization:
            fig.update_layout(**customization["layout"])
        
        return {"visualization": fig.to_json()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))