import numpy as np
from scipy import stats
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class StatTestResult:
    """Results of a statistical test."""
    test_name: str
    statistic: float
    p_value: float
    is_significant: bool
    effect_size: float
    confidence_interval: Tuple[float, float]
    sample_size: Dict[str, int]
    power: float

class ExperimentStats:
    """Statistical analysis utilities for A/B testing."""
    
    @staticmethod
    def z_test_proportions(
        successes_a: int,
        trials_a: int,
        successes_b: int,
        trials_b: int,
        alpha: float = 0.05
    ) -> StatTestResult:
        """
        Perform z-test for comparing two proportions.
        Used for comparing conversion rates, CTR, etc.
        """
        # Calculate proportions
        p1 = successes_a / trials_a if trials_a > 0 else 0
        p2 = successes_b / trials_b if trials_b > 0 else 0
        
        # Pooled proportion
        p_pooled = (successes_a + successes_b) / (trials_a + trials_b)
        
        # Standard error
        se = np.sqrt(p_pooled * (1 - p_pooled) * (1/trials_a + 1/trials_b))
        
        # Z-statistic
        z_stat = (p1 - p2) / se if se > 0 else 0
        
        # P-value
        p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
        
        # Effect size (Cohen's h)
        h = 2 * np.arcsin(np.sqrt(p1)) - 2 * np.arcsin(np.sqrt(p2))
        
        # Confidence interval
        ci_margin = stats.norm.ppf(1 - alpha/2) * se
        ci = (p1 - p2 - ci_margin, p1 - p2 + ci_margin)
        
        # Statistical power
        effect_size = abs(p1 - p2)
        power = ExperimentStats._calculate_power_proportion(
            p1, p2, trials_a, trials_b, alpha
        )
        
        return StatTestResult(
            test_name="z_test_proportions",
            statistic=z_stat,
            p_value=p_value,
            is_significant=p_value < alpha,
            effect_size=h,
            confidence_interval=ci,
            sample_size={"control": trials_a, "treatment": trials_b},
            power=power
        )

    @staticmethod
    def t_test_means(
        values_a: List[float],
        values_b: List[float],
        alpha: float = 0.05
    ) -> StatTestResult:
        """
        Perform t-test for comparing two means.
        Used for comparing revenue, session duration, etc.
        """
        # Perform t-test
        t_stat, p_value = stats.ttest_ind(values_a, values_b)
        
        # Effect size (Cohen's d)
        d = (np.mean(values_a) - np.mean(values_b)) / np.sqrt(
            (np.var(values_a) + np.var(values_b)) / 2
        )
        
        # Confidence interval
        ci = stats.t.interval(
            1 - alpha,
            len(values_a) + len(values_b) - 2,
            loc=np.mean(values_a) - np.mean(values_b),
            scale=np.sqrt(np.var(values_a)/len(values_a) + np.var(values_b)/len(values_b))
        )
        
        # Statistical power
        power = ExperimentStats._calculate_power_means(
            values_a, values_b, alpha
        )
        
        return StatTestResult(
            test_name="t_test_means",
            statistic=t_stat,
            p_value=p_value,
            is_significant=p_value < alpha,
            effect_size=d,
            confidence_interval=ci,
            sample_size={"control": len(values_a), "treatment": len(values_b)},
            power=power
        )

    @staticmethod
    def mann_whitney(
        values_a: List[float],
        values_b: List[float],
        alpha: float = 0.05
    ) -> StatTestResult:
        """
        Perform Mann-Whitney U test for non-parametric comparison.
        Used when data is not normally distributed.
        """
        # Perform Mann-Whitney U test
        stat, p_value = stats.mannwhitneyu(values_a, values_b, alternative='two-sided')
        
        # Effect size (r = Z / sqrt(N))
        n1, n2 = len(values_a), len(values_b)
        z_score = (stat - (n1 * n2 / 2)) / np.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
        r = abs(z_score) / np.sqrt(n1 + n2)
        
        # Confidence interval using bootstrap
        ci = ExperimentStats._bootstrap_ci(values_a, values_b, alpha)
        
        # Power calculation using bootstrap
        power = ExperimentStats._calculate_power_bootstrap(
            values_a, values_b, alpha
        )
        
        return StatTestResult(
            test_name="mann_whitney",
            statistic=stat,
            p_value=p_value,
            is_significant=p_value < alpha,
            effect_size=r,
            confidence_interval=ci,
            sample_size={"control": n1, "treatment": n2},
            power=power
        )

    @staticmethod
    def _calculate_power_proportion(
        p1: float,
        p2: float,
        n1: int,
        n2: int,
        alpha: float
    ) -> float:
        """Calculate statistical power for proportion test."""
        # Effect size
        h = 2 * np.arcsin(np.sqrt(p1)) - 2 * np.arcsin(np.sqrt(p2))
        
        # Non-centrality parameter
        ncp = abs(h) * np.sqrt((n1 * n2) / (n1 + n2))
        
        # Critical value
        z_crit = stats.norm.ppf(1 - alpha/2)
        
        # Power
        power = 1 - stats.norm.cdf(z_crit - ncp) + stats.norm.cdf(-z_crit - ncp)
        return power

    @staticmethod
    def _calculate_power_means(
        values_a: List[float],
        values_b: List[float],
        alpha: float
    ) -> float:
        """Calculate statistical power for t-test."""
        # Effect size (Cohen's d)
        d = (np.mean(values_a) - np.mean(values_b)) / np.sqrt(
            (np.var(values_a) + np.var(values_b)) / 2
        )
        
        # Non-centrality parameter
        n1, n2 = len(values_a), len(values_b)
        ncp = abs(d) * np.sqrt((n1 * n2) / (n1 + n2))
        
        # Degrees of freedom
        df = n1 + n2 - 2
        
        # Critical value
        t_crit = stats.t.ppf(1 - alpha/2, df)
        
        # Power
        power = 1 - stats.nct.cdf(t_crit, df, ncp) + stats.nct.cdf(-t_crit, df, ncp)
        return power

    @staticmethod
    def _bootstrap_ci(
        values_a: List[float],
        values_b: List[float],
        alpha: float,
        n_bootstrap: int = 10000
    ) -> Tuple[float, float]:
        """Calculate confidence interval using bootstrap."""
        diffs = []
        for _ in range(n_bootstrap):
            sample_a = np.random.choice(values_a, size=len(values_a), replace=True)
            sample_b = np.random.choice(values_b, size=len(values_b), replace=True)
            diffs.append(np.mean(sample_a) - np.mean(sample_b))
        
        return np.percentile(diffs, [alpha/2 * 100, (1-alpha/2) * 100])

    @staticmethod
    def _calculate_power_bootstrap(
        values_a: List[float],
        values_b: List[float],
        alpha: float,
        n_bootstrap: int = 1000
    ) -> float:
        """Calculate statistical power using bootstrap."""
        significant_tests = 0
        
        for _ in range(n_bootstrap):
            sample_a = np.random.choice(values_a, size=len(values_a), replace=True)
            sample_b = np.random.choice(values_b, size=len(values_b), replace=True)
            
            _, p_value = stats.mannwhitneyu(sample_a, sample_b, alternative='two-sided')
            if p_value < alpha:
                significant_tests += 1
        
        return significant_tests / n_bootstrap 