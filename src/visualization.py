from typing import List, Dict, Any, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np
from sklearn.cluster import KMeans
from .database import Database
from .monitoring import Monitoring, MetricType

class Visualization:
    @classmethod
    async def generate_engagement_chart(
        cls,
        user_id: str,
        days: int = 30,
        include_heatmap: bool = True
    ) -> Dict[str, Any]:
        """Generate engagement visualization data with hourly heatmap"""
        metrics = await Monitoring.get_user_engagement(user_id, days)
        
        # Daily activity chart
        daily_df = pd.DataFrame(metrics["daily_activity"])
        daily_chart = None
        if not daily_df.empty:
            daily_df["date"] = pd.to_datetime(daily_df["date"])
            fig_daily = px.line(
                daily_df,
                x="date",
                y="count",
                title="Daily User Activity"
            )
            daily_chart = fig_daily.to_json()
        
        # Hourly activity heatmap
        heatmap_chart = None
        if include_heatmap:
            interactions = await Database.db.interactions.find({
                "user_id": user_id,
                "timestamp": {"$gte": datetime.utcnow() - timedelta(days=days)}
            }).to_list(None)
            
            if interactions:
                df = pd.DataFrame(interactions)
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df["hour"] = df["timestamp"].dt.hour
                df["day_of_week"] = df["timestamp"].dt.day_name()
                
                pivot_table = pd.pivot_table(
                    df,
                    values="content_id",
                    index="day_of_week",
                    columns="hour",
                    aggfunc="count",
                    fill_value=0
                )
                
                fig_heatmap = go.Figure(data=go.Heatmap(
                    z=pivot_table.values,
                    x=pivot_table.columns,
                    y=pivot_table.index,
                    colorscale="Viridis"
                ))
                fig_heatmap.update_layout(
                    title="Activity Heatmap by Hour and Day",
                    xaxis_title="Hour of Day",
                    yaxis_title="Day of Week"
                )
                heatmap_chart = fig_heatmap.to_json()
        
        # Enhanced interaction funnel
        funnel_data = []
        for interaction_type in ["view", "click", "like", "share", "purchase"]:
            count = metrics["interaction_types"].get(interaction_type, 0)
            funnel_data.append(dict(
                interaction=interaction_type.capitalize(),
                count=count
            ))
        
        fig_funnel = go.Figure(go.Funnel(
            y=[d["interaction"] for d in funnel_data],
            x=[d["count"] for d in funnel_data],
            textinfo="value+percent initial"
        ))
        fig_funnel.update_layout(title="Interaction Funnel")
            
        return {
            "daily_activity": daily_chart,
            "hourly_heatmap": heatmap_chart,
            "interaction_funnel": fig_funnel.to_json(),
            "metrics": metrics
        }
    
    @classmethod
    async def generate_real_time_dashboard(
        cls,
        minutes: int = 60
    ) -> Dict[str, Any]:
        """Generate real-time dashboard data"""
        start_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        # Get recent interactions
        interactions = await Database.db.interactions.find({
            "timestamp": {"$gte": start_time}
        }).to_list(None)
        
        if not interactions:
            return {"error": "No recent interaction data available"}
        
        df = pd.DataFrame(interactions)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        # Real-time activity line chart
        df["minute"] = df["timestamp"].dt.floor("min")
        activity_by_minute = df.groupby("minute").size().reset_index()
        activity_by_minute.columns = ["timestamp", "count"]
        
        fig_realtime = px.line(
            activity_by_minute,
            x="timestamp",
            y="count",
            title="Real-time Activity (Past Hour)"
        )
        
        # Real-time content popularity
        popular_content = df.groupby("content_id").size().sort_values(ascending=False).head(5)
        fig_popular = px.bar(
            x=popular_content.index,
            y=popular_content.values,
            title="Trending Content (Past Hour)"
        )
        
        # User activity stream
        recent_activities = df.sort_values("timestamp", ascending=False).head(10)
        activity_stream = recent_activities.apply(
            lambda x: {
                "timestamp": x["timestamp"].isoformat(),
                "user_id": x["user_id"],
                "content_id": x["content_id"],
                "interaction_type": x["interaction_type"]
            },
            axis=1
        ).tolist()
        
        return {
            "realtime_activity": fig_realtime.to_json(),
            "trending_content": fig_popular.to_json(),
            "activity_stream": activity_stream,
            "summary": {
                "total_interactions": len(df),
                "unique_users": df["user_id"].nunique(),
                "unique_content": df["content_id"].nunique(),
                "peak_minute": activity_by_minute.loc[
                    activity_by_minute["count"].idxmax(),
                    "timestamp"
                ].isoformat()
            }
        }
    
    @classmethod
    async def generate_recommendation_insights(
        cls,
        days: int = 30
    ) -> Dict[str, Any]:
        """Generate advanced recommendation insights"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get recommendation history with interactions
        recommendations = await Database.db.recommendation_history.find({
            "timestamp": {"$gte": start_date}
        }).to_list(None)
        
        if not recommendations:
            return {"error": "No recommendation data available"}
        
        # Prepare data
        all_metrics = []
        for rec in recommendations:
            metrics = await Monitoring.track_recommendation_metrics(
                user_id=rec["user_id"],
                recommendation_ids=rec["content_ids"]
            )
            all_metrics.append({
                "timestamp": rec["timestamp"],
                "algorithm_version": rec.get("algorithm_version", "default"),
                **metrics
            })
        
        df = pd.DataFrame(all_metrics)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        # Algorithm performance comparison
        algo_performance = df.groupby("algorithm_version").agg({
            "ctr": "mean",
            "conversion_rate": "mean"
        }).reset_index()
        
        fig_algo = make_subplots(
            rows=1, cols=2,
            subplot_titles=("CTR by Algorithm", "Conversion Rate by Algorithm")
        )
        
        fig_algo.add_trace(
            go.Bar(
                x=algo_performance["algorithm_version"],
                y=algo_performance["ctr"],
                name="CTR"
            ),
            row=1, col=1
        )
        
        fig_algo.add_trace(
            go.Bar(
                x=algo_performance["algorithm_version"],
                y=algo_performance["conversion_rate"],
                name="Conversion Rate"
            ),
            row=1, col=2
        )
        
        # Time-based performance heatmap
        df["hour"] = df["timestamp"].dt.hour
        df["day_of_week"] = df["timestamp"].dt.day_name()
        
        pivot_ctr = pd.pivot_table(
            df,
            values="ctr",
            index="day_of_week",
            columns="hour",
            aggfunc="mean"
        )
        
        fig_heatmap = go.Figure(data=go.Heatmap(
            z=pivot_ctr.values,
            x=pivot_ctr.columns,
            y=pivot_ctr.index,
            colorscale="RdYlBu"
        ))
        fig_heatmap.update_layout(
            title="CTR Heatmap by Hour and Day",
            xaxis_title="Hour of Day",
            yaxis_title="Day of Week"
        )
        
        return {
            "algorithm_comparison": fig_algo.to_json(),
            "performance_heatmap": fig_heatmap.to_json(),
            "summary_stats": {
                "total_recommendations": len(df),
                "average_ctr": df["ctr"].mean(),
                "average_conversion_rate": df["conversion_rate"].mean(),
                "best_performing_algorithm": algo_performance.loc[
                    algo_performance["ctr"].idxmax(),
                    "algorithm_version"
                ]
            }
        }
    
    @classmethod
    def export_chart(cls, fig, format: str = "png") -> bytes:
        """Export chart as image"""
        return fig.to_image(format=format) 

    @classmethod
    async def generate_user_segments(
        cls,
        days: int = 30,
        n_segments: int = 4
    ) -> Dict[str, Any]:
        """Generate user segmentation analysis"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get user interactions
        interactions = await Database.db.interactions.find({
            "timestamp": {"$gte": start_date}
        }).to_list(None)
        
        if not interactions:
            return {"error": "No interaction data available"}
        
        df = pd.DataFrame(interactions)
        
        # Calculate user metrics
        user_metrics = df.groupby("user_id").agg({
            "content_id": "count",  # Total interactions
            "timestamp": lambda x: (x.max() - x.min()).total_seconds() / 3600,  # Activity duration
            "interaction_type": lambda x: len(x.unique())  # Interaction variety
        }).reset_index()
        
        user_metrics.columns = ["user_id", "total_interactions", "activity_duration", "interaction_variety"]
        
        # Normalize features for clustering
        features = user_metrics[["total_interactions", "activity_duration", "interaction_variety"]]
        normalized_features = (features - features.mean()) / features.std()
        
        # Perform clustering
        kmeans = KMeans(n_clusters=n_segments, random_state=42)
        user_metrics["segment"] = kmeans.fit_predict(normalized_features)
        
        # Generate segment profiles
        segment_profiles = user_metrics.groupby("segment").agg({
            "total_interactions": "mean",
            "activity_duration": "mean",
            "interaction_variety": "mean",
            "user_id": "count"  # Users per segment
        }).round(2)
        
        # Visualize segments
        fig_scatter = px.scatter_3d(
            user_metrics,
            x="total_interactions",
            y="activity_duration",
            z="interaction_variety",
            color="segment",
            title="User Segments 3D Visualization"
        )
        
        # Segment characteristics radar chart
        fig_radar = go.Figure()
        for segment in range(n_segments):
            segment_data = segment_profiles.loc[segment]
            fig_radar.add_trace(go.Scatterpolar(
                r=[
                    segment_data["total_interactions"],
                    segment_data["activity_duration"],
                    segment_data["interaction_variety"]
                ],
                theta=["Interactions", "Duration", "Variety"],
                name=f"Segment {segment}"
            ))
        
        fig_radar.update_layout(title="Segment Characteristics")
        
        return {
            "segments_3d": fig_scatter.to_json(),
            "segment_radar": fig_radar.to_json(),
            "segment_profiles": segment_profiles.to_dict(),
            "user_segments": user_metrics.to_dict(orient="records")
        }

    @classmethod
    async def generate_content_drill_down(
        cls,
        content_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Generate detailed content performance analysis"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get content interactions
        interactions = await Database.db.interactions.find({
            "content_id": content_id,
            "timestamp": {"$gte": start_date}
        }).to_list(None)
        
        if not interactions:
            return {"error": "No interaction data available for this content"}
        
        df = pd.DataFrame(interactions)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        # Hourly interaction pattern
        df["hour"] = df["timestamp"].dt.hour
        hourly_pattern = df.groupby("hour").size()
        fig_hourly = px.line(
            x=hourly_pattern.index,
            y=hourly_pattern.values,
            title="Hourly Interaction Pattern"
        )
        
        # User demographic analysis (if available)
        user_ids = df["user_id"].unique()
        users = await Database.db.users.find({
            "id": {"$in": list(user_ids)}
        }).to_list(None)
        
        user_df = pd.DataFrame(users) if users else None
        
        if user_df is not None and "preferences" in user_df.columns:
            # Analyze user preferences
            all_preferences = []
            for prefs in user_df["preferences"]:
                if isinstance(prefs, dict):
                    all_preferences.extend(prefs.keys())
            
            preference_counts = pd.Series(all_preferences).value_counts()
            fig_preferences = px.pie(
                values=preference_counts.values,
                names=preference_counts.index,
                title="User Preferences Distribution"
            )
        else:
            fig_preferences = None
        
        # Interaction funnel
        interaction_funnel = df["interaction_type"].value_counts()
        fig_funnel = go.Figure(go.Funnel(
            y=interaction_funnel.index,
            x=interaction_funnel.values
        ))
        fig_funnel.update_layout(title="Interaction Funnel")
        
        # Similar content performance comparison
        content = await Database.db.content.find_one({"id": content_id})
        if content and "type" in content:
            similar_content = await Database.db.content.find({
                "type": content["type"],
                "id": {"$ne": content_id}
            }).limit(5).to_list(None)
            
            if similar_content:
                similar_metrics = []
                for sim_content in similar_content:
                    interactions_count = await Database.db.interactions.count_documents({
                        "content_id": sim_content["id"],
                        "timestamp": {"$gte": start_date}
                    })
                    similar_metrics.append({
                        "content_id": sim_content["id"],
                        "title": sim_content.get("title", "Unknown"),
                        "interactions": interactions_count
                    })
                
                fig_comparison = px.bar(
                    similar_metrics,
                    x="title",
                    y="interactions",
                    title="Similar Content Performance"
                )
            else:
                fig_comparison = None
        else:
            fig_comparison = None
        
        return {
            "hourly_pattern": fig_hourly.to_json(),
            "user_preferences": fig_preferences.to_json() if fig_preferences else None,
            "interaction_funnel": fig_funnel.to_json(),
            "similar_content_comparison": fig_comparison.to_json() if fig_comparison else None,
            "summary": {
                "total_interactions": len(df),
                "unique_users": len(user_ids),
                "most_common_interaction": df["interaction_type"].mode().iloc[0],
                "peak_hour": hourly_pattern.idxmax()
            }
        }

    @classmethod
    async def generate_recommendation_drill_down(
        cls,
        algorithm_version: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Generate detailed algorithm performance analysis"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get recommendations
        recommendations = await Database.db.recommendation_history.find({
            "algorithm_version": algorithm_version,
            "timestamp": {"$gte": start_date}
        }).to_list(None)
        
        if not recommendations:
            return {"error": "No recommendation data available"}
        
        df = pd.DataFrame(recommendations)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        # Performance over time
        daily_performance = df.groupby(df["timestamp"].dt.date).agg({
            "scores": lambda x: np.mean([score for scores in x for score in scores])
        }).reset_index()
        
        fig_performance = px.line(
            daily_performance,
            x="timestamp",
            y="scores",
            title=f"Algorithm Performance Over Time - {algorithm_version}"
        )
        
        # Content type performance
        content_ids = [id for rec in recommendations for id in rec["content_ids"]]
        contents = await Database.db.content.find({
            "id": {"$in": content_ids}
        }).to_list(None)
        
        if contents:
            content_df = pd.DataFrame(contents)
            type_performance = content_df.groupby("type").size()
            
            fig_types = px.pie(
                values=type_performance.values,
                names=type_performance.index,
                title="Content Type Distribution"
            )
        else:
            fig_types = None
        
        return {
            "performance_trend": fig_performance.to_json(),
            "content_types": fig_types.to_json() if fig_types else None,
            "summary": {
                "total_recommendations": len(df),
                "average_score": daily_performance["scores"].mean(),
                "recommendation_count": len(content_ids)
            }
        }