from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Optional
from app.models.experiment import Experiment, ExperimentCreate, ExperimentUpdate
from app.services.experiment_service import experiment_service
from app.services.experiment_analysis import experiment_analysis_service, ExperimentAnalysis
from app.core.auth import get_current_user
from app.models.user import User
from app.core.monitoring import logger, metrics_logger

router = APIRouter()

@router.post("/experiments", response_model=Experiment)
async def create_experiment(
    experiment: ExperimentCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new experiment."""
    return await experiment_service.create_experiment(experiment, current_user)

@router.get("/experiments", response_model=List[Experiment])
async def list_experiments(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """List all experiments with optional status filter."""
    return await experiment_service.list_experiments(status)

@router.get("/experiments/{experiment_id}", response_model=Experiment)
async def get_experiment(
    experiment_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get experiment by ID."""
    experiment = await experiment_service.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment

@router.put("/experiments/{experiment_id}", response_model=Experiment)
async def update_experiment(
    experiment_id: str,
    experiment_update: ExperimentUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update experiment by ID."""
    experiment = await experiment_service.update_experiment(
        experiment_id,
        experiment_update
    )
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment

@router.delete("/experiments/{experiment_id}")
async def delete_experiment(
    experiment_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete experiment by ID."""
    success = await experiment_service.delete_experiment(experiment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"message": "Experiment deleted successfully"}

@router.post("/experiments/{experiment_id}/start")
async def start_experiment(
    experiment_id: str,
    current_user: User = Depends(get_current_user)
):
    """Start an experiment."""
    experiment = await experiment_service.start_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"message": "Experiment started successfully"}

@router.post("/experiments/{experiment_id}/stop")
async def stop_experiment(
    experiment_id: str,
    current_user: User = Depends(get_current_user)
):
    """Stop an experiment."""
    experiment = await experiment_service.stop_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"message": "Experiment stopped successfully"}

@router.get("/experiments/{experiment_id}/analysis", response_model=ExperimentAnalysis)
async def analyze_experiment(
    experiment_id: str,
    confidence_level: float = 0.95,
    current_user: User = Depends(get_current_user)
):
    """
    Perform statistical analysis of experiment results.
    
    Parameters:
    - experiment_id: ID of the experiment to analyze
    - confidence_level: Confidence level for statistical tests (default: 0.95)
    
    Returns:
    - Detailed statistical analysis including:
        - Metric comparisons
        - Statistical significance
        - Effect sizes
        - Confidence intervals
        - Power analysis
        - Recommendations
    """
    try:
        # Get experiment
        experiment = await experiment_service.get_experiment(experiment_id)
        if not experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
            
        # Check if experiment has enough data
        if not experiment.metrics:
            raise HTTPException(
                status_code=400,
                detail="Experiment has no metrics data"
            )
            
        # Perform analysis
        analysis = await experiment_analysis_service.analyze_experiment(
            experiment,
            confidence_level
        )
        
        # Log analysis request
        metrics_logger.log_metric(
            "experiment_analysis_requested",
            1,
            {"experiment_id": experiment_id}
        )
        
        return analysis
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "experiment_analysis_error",
            experiment_id=experiment_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail="Error performing experiment analysis"
        )

@router.get("/experiments/{experiment_id}/metrics")
async def get_experiment_metrics(
    experiment_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get raw metrics data for an experiment."""
    experiment = await experiment_service.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment.metrics 