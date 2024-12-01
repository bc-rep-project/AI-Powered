import uuid
import random
from datetime import datetime
from typing import Dict, List, Optional
from app.models.experiment import (
    Experiment,
    ExperimentStatus,
    ExperimentVariant,
    ExperimentMetrics,
    UserAssignment,
    ExperimentEvent
)
from app.db.database import mongodb
from app.core.monitoring import metrics_logger, logger

class ExperimentService:
    def __init__(self):
        self.experiments_collection = mongodb.experiments
        self.assignments_collection = mongodb.user_assignments
        self.events_collection = mongodb.experiment_events
        self.cache: Dict[str, Experiment] = {}

    async def create_experiment(self, experiment: Experiment) -> Experiment:
        """Create a new experiment."""
        experiment.id = str(uuid.uuid4())
        await self.experiments_collection.insert_one(experiment.dict())
        return experiment

    async def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Get experiment by ID."""
        if experiment_id in self.cache:
            return self.cache[experiment_id]
            
        experiment_data = await self.experiments_collection.find_one({"id": experiment_id})
        if experiment_data:
            experiment = Experiment(**experiment_data)
            self.cache[experiment_id] = experiment
            return experiment
        return None

    async def update_experiment(self, experiment: Experiment) -> Experiment:
        """Update experiment."""
        await self.experiments_collection.update_one(
            {"id": experiment.id},
            {"$set": experiment.dict()}
        )
        self.cache[experiment.id] = experiment
        return experiment

    async def get_active_experiments(self) -> List[Experiment]:
        """Get all active experiments."""
        experiments = await self.experiments_collection.find(
            {"status": ExperimentStatus.ACTIVE}
        ).to_list(None)
        return [Experiment(**exp) for exp in experiments]

    async def assign_user_to_experiment(
        self,
        user_id: str,
        experiment_id: str
    ) -> Optional[str]:
        """Assign user to an experiment variant."""
        # Check if user is already assigned
        assignment = await self.assignments_collection.find_one({
            "user_id": user_id,
            "experiment_id": experiment_id
        })
        
        if assignment:
            return assignment["variant_id"]
        
        # Get experiment
        experiment = await self.get_experiment(experiment_id)
        if not experiment or experiment.status != ExperimentStatus.ACTIVE:
            return None
        
        # Randomly assign variant based on traffic percentages
        random_value = random.random()
        cumulative_percentage = 0
        
        for variant in experiment.variants:
            cumulative_percentage += variant.traffic_percentage
            if random_value <= cumulative_percentage:
                # Create assignment
                assignment = UserAssignment(
                    user_id=user_id,
                    experiment_id=experiment_id,
                    variant_id=variant.id
                )
                
                await self.assignments_collection.insert_one(assignment.dict())
                return variant.id
        
        return None

    async def record_event(self, event: ExperimentEvent):
        """Record an experiment event."""
        try:
            # Store event
            await self.events_collection.insert_one(event.dict())
            
            # Update metrics
            experiment = await self.get_experiment(event.experiment_id)
            if not experiment:
                return
            
            # Initialize metrics if not exists
            if event.variant_id not in experiment.metrics:
                experiment.metrics[event.variant_id] = ExperimentMetrics(
                    variant_id=event.variant_id
                )
            
            # Update metrics based on event type
            metrics = experiment.metrics[event.variant_id]
            if event.event_type == "impression":
                metrics.impressions += 1
            elif event.event_type == "click":
                metrics.clicks += 1
            elif event.event_type == "conversion":
                metrics.conversions += 1
                if "revenue" in event.metadata:
                    metrics.total_revenue += float(event.metadata["revenue"])
            
            # Update experiment
            await self.update_experiment(experiment)
            
            # Log metrics
            logger.info(
                "experiment_event_recorded",
                experiment_id=event.experiment_id,
                variant_id=event.variant_id,
                event_type=event.event_type,
                metrics=metrics.dict()
            )
            
        except Exception as e:
            metrics_logger.log_error(
                "experiment_event_error",
                str(e),
                {"event": event.dict()}
            )

    async def get_experiment_results(
        self,
        experiment_id: str
    ) -> Dict[str, ExperimentMetrics]:
        """Get experiment results."""
        experiment = await self.get_experiment(experiment_id)
        if not experiment:
            return {}
            
        return experiment.metrics

    async def start_experiment(self, experiment_id: str):
        """Start an experiment."""
        experiment = await self.get_experiment(experiment_id)
        if experiment and experiment.status == ExperimentStatus.DRAFT:
            experiment.status = ExperimentStatus.ACTIVE
            experiment.start_date = datetime.utcnow()
            await self.update_experiment(experiment)

    async def stop_experiment(self, experiment_id: str):
        """Stop an experiment."""
        experiment = await self.get_experiment(experiment_id)
        if experiment and experiment.status == ExperimentStatus.ACTIVE:
            experiment.status = ExperimentStatus.COMPLETED
            experiment.end_date = datetime.utcnow()
            await self.update_experiment(experiment)

# Global experiment service instance
experiment_service = ExperimentService() 