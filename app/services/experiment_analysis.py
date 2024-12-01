from typing import Dict, List, Optional
from app.models.experiment import Experiment, ExperimentMetrics
from app.utils.statistics import ExperimentStats, StatTestResult
from app.core.monitoring import logger, metrics_logger
from dataclasses import dataclass
from datetime import datetime

@dataclass
class MetricAnalysis:
    """Analysis results for a single metric."""
    metric_name: str
    control_value: float
    treatment_value: float
    relative_difference: float
    statistical_test: StatTestResult
    recommendation: str

@dataclass
class ExperimentAnalysis:
    """Complete analysis of an experiment."""
    experiment_id: str
    status: str
    start_date: datetime
    duration_days: float
    total_users: int
    metrics_analysis: Dict[str, MetricAnalysis]
    overall_recommendation: str
    confidence_level: float

class ExperimentAnalysisService:
    def __init__(self):
        self.stats = ExperimentStats()

    async def analyze_experiment(
        self,
        experiment: Experiment,
        confidence_level: float = 0.95
    ) -> ExperimentAnalysis:
        """Perform comprehensive analysis of an experiment."""
        try:
            # Get control and treatment metrics
            control_metrics = self._get_variant_metrics(experiment, "control")
            treatment_metrics = self._get_variant_metrics(experiment, "treatment")
            
            if not control_metrics or not treatment_metrics:
                raise ValueError("Missing metrics for control or treatment")
            
            # Analyze each metric
            metrics_analysis = {}
            
            # Analyze CTR
            metrics_analysis["ctr"] = self._analyze_proportion_metric(
                "CTR",
                control_metrics.clicks,
                control_metrics.impressions,
                treatment_metrics.clicks,
                treatment_metrics.impressions,
                alpha=1-confidence_level
            )
            
            # Analyze conversion rate
            metrics_analysis["conversion_rate"] = self._analyze_proportion_metric(
                "Conversion Rate",
                control_metrics.conversions,
                control_metrics.clicks,
                treatment_metrics.conversions,
                treatment_metrics.clicks,
                alpha=1-confidence_level
            )
            
            # Analyze revenue per user
            if control_metrics.impressions > 0 and treatment_metrics.impressions > 0:
                metrics_analysis["revenue_per_user"] = self._analyze_mean_metric(
                    "Revenue per User",
                    control_metrics.total_revenue / control_metrics.impressions,
                    treatment_metrics.total_revenue / treatment_metrics.impressions,
                    alpha=1-confidence_level
                )
            
            # Calculate overall recommendation
            overall_recommendation = self._get_overall_recommendation(metrics_analysis)
            
            # Calculate experiment duration
            duration_days = (
                (experiment.end_date or datetime.utcnow()) - experiment.start_date
            ).days if experiment.start_date else 0
            
            # Create analysis result
            analysis = ExperimentAnalysis(
                experiment_id=experiment.id,
                status=experiment.status,
                start_date=experiment.start_date,
                duration_days=duration_days,
                total_users=control_metrics.impressions + treatment_metrics.impressions,
                metrics_analysis=metrics_analysis,
                overall_recommendation=overall_recommendation,
                confidence_level=confidence_level
            )
            
            # Log analysis results
            logger.info(
                "experiment_analysis_completed",
                experiment_id=experiment.id,
                recommendation=overall_recommendation
            )
            
            return analysis
            
        except Exception as e:
            metrics_logger.log_error(
                "experiment_analysis_error",
                str(e),
                {"experiment_id": experiment.id}
            )
            raise

    def _analyze_proportion_metric(
        self,
        metric_name: str,
        successes_a: int,
        trials_a: int,
        successes_b: int,
        trials_b: int,
        alpha: float = 0.05
    ) -> MetricAnalysis:
        """Analyze a proportion-based metric (e.g., CTR, conversion rate)."""
        # Calculate proportions
        prop_a = successes_a / trials_a if trials_a > 0 else 0
        prop_b = successes_b / trials_b if trials_b > 0 else 0
        
        # Calculate relative difference
        rel_diff = ((prop_b - prop_a) / prop_a) * 100 if prop_a > 0 else 0
        
        # Perform statistical test
        test_result = self.stats.z_test_proportions(
            successes_a, trials_a,
            successes_b, trials_b,
            alpha
        )
        
        # Generate recommendation
        recommendation = self._get_metric_recommendation(
            metric_name, rel_diff, test_result
        )
        
        return MetricAnalysis(
            metric_name=metric_name,
            control_value=prop_a,
            treatment_value=prop_b,
            relative_difference=rel_diff,
            statistical_test=test_result,
            recommendation=recommendation
        )

    def _analyze_mean_metric(
        self,
        metric_name: str,
        value_a: float,
        value_b: float,
        alpha: float = 0.05
    ) -> MetricAnalysis:
        """Analyze a mean-based metric (e.g., revenue per user)."""
        # Calculate relative difference
        rel_diff = ((value_b - value_a) / value_a) * 100 if value_a > 0 else 0
        
        # Perform statistical test
        test_result = self.stats.t_test_means(
            [value_a], [value_b],  # In practice, use full value lists
            alpha
        )
        
        # Generate recommendation
        recommendation = self._get_metric_recommendation(
            metric_name, rel_diff, test_result
        )
        
        return MetricAnalysis(
            metric_name=metric_name,
            control_value=value_a,
            treatment_value=value_b,
            relative_difference=rel_diff,
            statistical_test=test_result,
            recommendation=recommendation
        )

    def _get_metric_recommendation(
        self,
        metric_name: str,
        relative_diff: float,
        test_result: StatTestResult
    ) -> str:
        """Generate recommendation based on metric analysis."""
        if not test_result.is_significant:
            if test_result.power < 0.8:
                return f"Inconclusive - Need more data (current power: {test_result.power:.2f})"
            return "No significant difference detected"
            
        if relative_diff > 0:
            return f"Treatment shows {relative_diff:.1f}% improvement in {metric_name}"
        return f"Treatment shows {abs(relative_diff):.1f}% decrease in {metric_name}"

    def _get_overall_recommendation(
        self,
        metrics_analysis: Dict[str, MetricAnalysis]
    ) -> str:
        """Generate overall experiment recommendation."""
        significant_improvements = 0
        significant_degradations = 0
        
        for analysis in metrics_analysis.values():
            if analysis.statistical_test.is_significant:
                if analysis.relative_difference > 0:
                    significant_improvements += 1
                else:
                    significant_degradations += 1
        
        if significant_improvements == 0 and significant_degradations == 0:
            return "No significant differences detected"
            
        if significant_degradations > 0:
            return "Keep control - Treatment shows significant degradation"
            
        if significant_improvements > 0:
            return "Launch treatment - Shows significant improvements"
            
        return "Gather more data - Results inconclusive"

    def _get_variant_metrics(
        self,
        experiment: Experiment,
        variant_id: str
    ) -> Optional[ExperimentMetrics]:
        """Get metrics for a specific variant."""
        return experiment.metrics.get(variant_id)

# Global experiment analysis service instance
experiment_analysis_service = ExperimentAnalysisService() 