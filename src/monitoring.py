from datetime import datetime, timedelta
from typing import List, Dict, Optional
from enum import Enum
import numpy as np
from .database import Database

class MetricType(Enum):
    CTR = "click_through_rate"
    CONVERSION = "conversion_rate"
    ENGAGEMENT = "engagement_time"
    RETENTION = "retention_rate"

class ExperimentType(Enum):
    ALGORITHM = "algorithm"
    RANKING = "ranking"
    UI = "ui_placement"

class Monitoring:
    @classmethod
    async def track_recommendation_metrics(
        cls,
        user_id: str,
        recommendation_ids: List[str],
        time_window: int = 24
    ) -> Dict:
        """Track metrics for recommended items"""
        start_time = datetime.utcnow() - timedelta(hours=time_window)
        
        # Get interactions with recommended items
        interactions = await Database.db.interactions.find({
            "user_id": user_id,
            "content_id": {"$in": recommendation_ids},
            "timestamp": {"$gte": start_time}
        }).to_list(None)
        
        # Calculate metrics
        total_recommendations = len(recommendation_ids)
        clicks = sum(1 for i in interactions if i["interaction_type"] == "click")
        conversions = sum(1 for i in interactions if i["interaction_type"] == "purchase")
        
        metrics = {
            "total_recommendations": total_recommendations,
            "clicks": clicks,
            "conversions": conversions,
            "ctr": clicks / total_recommendations if total_recommendations > 0 else 0,
            "conversion_rate": conversions / total_recommendations if total_recommendations > 0 else 0
        }
        
        # Store metrics
        await Database.db.metrics.insert_one({
            "user_id": user_id,
            "timestamp": datetime.utcnow(),
            "metrics": metrics,
            "recommendation_ids": recommendation_ids
        })
        
        return metrics

    @classmethod
    async def get_user_engagement(cls, user_id: str, days: int = 30) -> Dict:
        """Get user engagement metrics"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get user interactions
        interactions = await Database.db.interactions.find({
            "user_id": user_id,
            "timestamp": {"$gte": start_date}
        }).to_list(None)
        
        if not interactions:
            return {
                "total_interactions": 0,
                "interaction_types": {},
                "daily_activity": [],
                "average_daily_interactions": 0
            }
        
        # Calculate engagement metrics
        interaction_types = {}
        daily_activity = {}
        
        for interaction in interactions:
            # Count interaction types
            itype = interaction["interaction_type"]
            interaction_types[itype] = interaction_types.get(itype, 0) + 1
            
            # Track daily activity
            date = interaction["timestamp"].date().isoformat()
            daily_activity[date] = daily_activity.get(date, 0) + 1
        
        # Calculate average daily interactions
        avg_daily = len(interactions) / days
        
        return {
            "total_interactions": len(interactions),
            "interaction_types": interaction_types,
            "daily_activity": [
                {"date": date, "count": count}
                for date, count in daily_activity.items()
            ],
            "average_daily_interactions": avg_daily
        }

    @classmethod
    async def create_ab_test(
        cls,
        name: str,
        experiment_type: ExperimentType,
        variants: List[Dict],
        description: Optional[str] = None
    ) -> Dict:
        """Create a new A/B test"""
        test = {
            "name": name,
            "type": experiment_type.value,
            "variants": variants,
            "description": description,
            "start_date": datetime.utcnow(),
            "status": "active",
            "results": {}
        }
        
        await Database.db.ab_tests.insert_one(test)
        return test

    @classmethod
    async def track_variant_performance(
        cls,
        test_name: str,
        variant_id: str,
        user_id: str,
        metrics: Dict
    ):
        """Track performance metrics for an A/B test variant"""
        await Database.db.ab_tests.update_one(
            {"name": test_name},
            {
                "$push": {
                    f"results.{variant_id}": {
                        "user_id": user_id,
                        "metrics": metrics,
                        "timestamp": datetime.utcnow()
                    }
                }
            }
        )

    @classmethod
    async def get_ab_test_results(cls, test_name: str) -> Dict:
        """Get results for an A/B test"""
        test = await Database.db.ab_tests.find_one({"name": test_name})
        if not test:
            return None
            
        results = {}
        for variant_id, variant_results in test.get("results", {}).items():
            metrics = [r["metrics"] for r in variant_results]
            
            results[variant_id] = {
                "sample_size": len(metrics),
                "ctr": np.mean([m["ctr"] for m in metrics]),
                "conversion_rate": np.mean([m["conversion_rate"] for m in metrics]),
                "confidence_interval": cls._calculate_confidence_interval(
                    [m["ctr"] for m in metrics]
                )
            }
            
        return results

    @staticmethod
    def _calculate_confidence_interval(values: List[float], confidence: float = 0.95):
        """Calculate confidence interval for a list of values"""
        if not values:
            return None
            
        mean = np.mean(values)
        std = np.std(values)
        z_score = 1.96  # 95% confidence interval
        
        margin_of_error = z_score * (std / np.sqrt(len(values)))
        
        return {
            "mean": mean,
            "lower_bound": mean - margin_of_error,
            "upper_bound": mean + margin_of_error,
            "confidence_level": confidence
        } 