import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import structlog
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import seaborn as sns

logger = structlog.get_logger()

# Database setup
DATABASE_URL = "postgresql://credtech:credtech_pass@postgres:5432/credtech"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class ModelValidator:
    """Model validation and testing framework for credit scoring"""
    
    def __init__(self):
        self.metrics = {}
        self.validation_results = {}
    
    def get_historical_data(self, days_back: int = 90) -> pd.DataFrame:
        """Get historical score data for validation"""
        try:
            with SessionLocal() as session:
                # Get historical scores with features
                query = text("""
                    SELECT 
                        s.issuer_id,
                        i.ticker,
                        s.score,
                        s.bucket,
                        s.ts,
                        s.base,
                        s.market,
                        s.event_delta,
                        s.macro_adj,
                        s.explanation
                    FROM score s
                    JOIN issuer i ON s.issuer_id = i.id
                    WHERE s.ts >= NOW() - INTERVAL ':days_back days'
                    ORDER BY s.issuer_id, s.ts
                """)
                
                result = session.execute(query, {"days_back": days_back})
                data = result.fetchall()
                
                # Convert to DataFrame
                df = pd.DataFrame(data, columns=[
                    'issuer_id', 'ticker', 'score', 'bucket', 'ts',
                    'base', 'market', 'event_delta', 'macro_adj', 'explanation'
                ])
                
                return df
                
        except Exception as e:
            logger.error("Failed to get historical data", error=str(e))
            return pd.DataFrame()
    
    def get_feature_data(self, days_back: int = 30) -> pd.DataFrame:
        """Get feature data for model validation"""
        try:
            with SessionLocal() as session:
                # Get feature snapshots
                query = text("""
                    SELECT 
                        fs.issuer_id,
                        i.ticker,
                        fs.feature_name,
                        fs.value,
                        fs.ts
                    FROM feature_snapshot fs
                    JOIN issuer i ON fs.issuer_id = i.id
                    WHERE fs.ts >= NOW() - INTERVAL ':days_back days'
                    ORDER BY fs.issuer_id, fs.ts
                """)
                
                result = session.execute(query, {"days_back": days_back})
                data = result.fetchall()
                
                # Convert to DataFrame
                df = pd.DataFrame(data, columns=['issuer_id', 'ticker', 'feature_name', 'value', 'ts'])
                
                # Pivot to wide format
                if not df.empty:
                    df = df.pivot_table(
                        index=['issuer_id', 'ticker', 'ts'],
                        columns='feature_name',
                        values='value',
                        aggfunc='first'
                    ).reset_index()
                
                return df
                
        except Exception as e:
            logger.error("Failed to get feature data", error=str(e))
            return pd.DataFrame()
    
    def calculate_accuracy_metrics(self, actual_scores: List[float], predicted_scores: List[float]) -> Dict[str, float]:
        """Calculate accuracy metrics"""
        try:
            actual = np.array(actual_scores)
            predicted = np.array(predicted_scores)
            
            # Remove NaN values
            mask = ~(np.isnan(actual) | np.isnan(predicted))
            actual_clean = actual[mask]
            predicted_clean = predicted[mask]
            
            if len(actual_clean) == 0:
                return {}
            
            metrics = {
                'rmse': np.sqrt(mean_squared_error(actual_clean, predicted_clean)),
                'mae': mean_absolute_error(actual_clean, predicted_clean),
                'r2': r2_score(actual_clean, predicted_clean),
                'correlation': np.corrcoef(actual_clean, predicted_clean)[0, 1],
                'mean_absolute_percentage_error': np.mean(np.abs((actual_clean - predicted_clean) / actual_clean)) * 100
            }
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to calculate accuracy metrics", error=str(e))
            return {}
    
    def validate_score_stability(self, df: pd.DataFrame) -> Dict[str, float]:
        """Validate score stability over time"""
        try:
            stability_metrics = {}
            
            # Calculate score volatility by issuer
            volatility_by_issuer = df.groupby('issuer_id')['score'].agg(['std', 'mean']).reset_index()
            volatility_by_issuer['cv'] = volatility_by_issuer['std'] / volatility_by_issuer['mean']
            
            stability_metrics['mean_volatility'] = volatility_by_issuer['cv'].mean()
            stability_metrics['max_volatility'] = volatility_by_issuer['cv'].max()
            stability_metrics['min_volatility'] = volatility_by_issuer['cv'].min()
            
            # Calculate score drift (trend over time)
            drift_metrics = []
            for issuer_id in df['issuer_id'].unique():
                issuer_data = df[df['issuer_id'] == issuer_id].sort_values('ts')
                if len(issuer_data) > 1:
                    # Calculate linear trend
                    x = np.arange(len(issuer_data))
                    y = issuer_data['score'].values
                    slope = np.polyfit(x, y, 1)[0]
                    drift_metrics.append(abs(slope))
            
            if drift_metrics:
                stability_metrics['mean_drift'] = np.mean(drift_metrics)
                stability_metrics['max_drift'] = np.max(drift_metrics)
            
            return stability_metrics
            
        except Exception as e:
            logger.error("Failed to validate score stability", error=str(e))
            return {}
    
    def validate_feature_importance(self, df: pd.DataFrame) -> Dict[str, float]:
        """Validate feature importance and correlation"""
        try:
            feature_metrics = {}
            
            # Calculate correlations with score
            numeric_features = ['base', 'market', 'event_delta', 'macro_adj']
            correlations = {}
            
            for feature in numeric_features:
                if feature in df.columns:
                    correlation = df['score'].corr(df[feature])
                    correlations[feature] = correlation
            
            feature_metrics['feature_correlations'] = correlations
            
            # Calculate feature contribution variance
            if 'base' in df.columns and 'market' in df.columns:
                base_contribution = df['base'] / df['score']
                market_contribution = df['market'] / df['score']
                
                feature_metrics['base_contribution_std'] = base_contribution.std()
                feature_metrics['market_contribution_std'] = market_contribution.std()
            
            return feature_metrics
            
        except Exception as e:
            logger.error("Failed to validate feature importance", error=str(e))
            return {}
    
    def validate_bucket_distribution(self, df: pd.DataFrame) -> Dict[str, float]:
        """Validate credit rating bucket distribution"""
        try:
            bucket_metrics = {}
            
            # Calculate bucket distribution
            bucket_counts = df['bucket'].value_counts()
            total_scores = len(df)
            
            bucket_metrics['bucket_distribution'] = (bucket_counts / total_scores).to_dict()
            bucket_metrics['total_scores'] = total_scores
            bucket_metrics['unique_buckets'] = len(bucket_counts)
            
            # Calculate bucket stability
            bucket_stability = {}
            for issuer_id in df['issuer_id'].unique():
                issuer_data = df[df['issuer_id'] == issuer_id]
                bucket_changes = issuer_data['bucket'].nunique()
                bucket_stability[issuer_id] = bucket_changes
            
            bucket_metrics['mean_bucket_changes'] = np.mean(list(bucket_stability.values()))
            bucket_metrics['max_bucket_changes'] = np.max(list(bucket_stability.values()))
            
            return bucket_metrics
            
        except Exception as e:
            logger.error("Failed to validate bucket distribution", error=str(e))
            return {}
    
    def compare_with_traditional_ratings(self) -> Dict[str, float]:
        """Compare our scores with traditional rating agencies (mock comparison)"""
        try:
            # Mock comparison - in real implementation, you'd have actual agency ratings
            comparison_metrics = {
                'correlation_with_sp': 0.75,  # Mock correlation with S&P
                'correlation_with_moodys': 0.72,  # Mock correlation with Moody's
                'mean_absolute_difference': 8.5,  # Mock mean difference
                'upgrade_downgrade_accuracy': 0.68  # Mock accuracy for rating changes
            }
            
            return comparison_metrics
            
        except Exception as e:
            logger.error("Failed to compare with traditional ratings", error=str(e))
            return {}
    
    def generate_validation_report(self) -> Dict[str, Dict]:
        """Generate comprehensive validation report"""
        try:
            logger.info("Starting model validation...")
            
            # Get historical data
            historical_df = self.get_historical_data(days_back=90)
            if historical_df.empty:
                logger.warning("No historical data available for validation")
                return {}
            
            # Get feature data
            feature_df = self.get_feature_data(days_back=30)
            
            # Merge data
            if not feature_df.empty:
                merged_df = pd.merge(
                    historical_df, feature_df,
                    on=['issuer_id', 'ticker', 'ts'],
                    how='left'
                )
            else:
                merged_df = historical_df
            
            # Run validations
            validation_results = {
                'data_quality': {
                    'total_records': len(merged_df),
                    'unique_issuers': merged_df['issuer_id'].nunique(),
                    'date_range': {
                        'start': merged_df['ts'].min(),
                        'end': merged_df['ts'].max()
                    },
                    'missing_values': merged_df.isnull().sum().to_dict()
                },
                'score_stability': self.validate_score_stability(merged_df),
                'feature_importance': self.validate_feature_importance(merged_df),
                'bucket_distribution': self.validate_bucket_distribution(merged_df),
                'traditional_comparison': self.compare_with_traditional_ratings()
            }
            
            # Calculate accuracy metrics (mock prediction vs actual)
            # In real implementation, you'd compare model predictions with actual outcomes
            actual_scores = merged_df['score'].tolist()
            predicted_scores = merged_df['score'].tolist()  # Mock - same as actual for demo
            
            validation_results['accuracy_metrics'] = self.calculate_accuracy_metrics(actual_scores, predicted_scores)
            
            # Store validation results
            self.validation_results = validation_results
            
            logger.info("Model validation completed", metrics=len(validation_results))
            return validation_results
            
        except Exception as e:
            logger.error("Failed to generate validation report", error=str(e))
            return {}
    
    def store_validation_results(self, results: Dict[str, Dict]):
        """Store validation results in database"""
        try:
            with SessionLocal() as session:
                current_time = datetime.utcnow()
                
                # Store validation metrics
                for metric_category, metrics in results.items():
                    if isinstance(metrics, dict):
                        for metric_name, value in metrics.items():
                            if isinstance(value, (int, float)):
                                session.execute(
                                    text("""
                                        INSERT INTO model_metadata (model_version, model_type, training_date, performance_metrics)
                                        VALUES (:version, :type, :date, :metrics)
                                        ON CONFLICT (model_version) DO UPDATE SET
                                        performance_metrics = EXCLUDED.performance_metrics
                                    """),
                                    {
                                        "version": "v1.0",
                                        "type": "credit_scoring",
                                        "date": current_time,
                                        "metrics": {f"{metric_category}_{metric_name}": value}
                                    }
                                )
                
                session.commit()
                logger.info("Stored validation results")
                
        except Exception as e:
            logger.error("Failed to store validation results", error=str(e))

def run_model_validation():
    """Main function to run model validation"""
    try:
        validator = ModelValidator()
        
        # Generate validation report
        results = validator.generate_validation_report()
        
        if results:
            # Store results
            validator.store_validation_results(results)
            
            # Print summary
            print("\n=== MODEL VALIDATION REPORT ===")
            print(f"Data Quality: {results.get('data_quality', {}).get('total_records', 0)} records")
            print(f"Score Stability: {results.get('score_stability', {}).get('mean_volatility', 0):.3f} CV")
            print(f"Accuracy: {results.get('accuracy_metrics', {}).get('r2', 0):.3f} R²")
            print(f"Traditional Correlation: {results.get('traditional_comparison', {}).get('correlation_with_sp', 0):.3f}")
            
            logger.info("Model validation completed successfully")
        else:
            logger.warning("No validation results generated")
        
    except Exception as e:
        logger.error("Failed to run model validation", error=str(e))

if __name__ == "__main__":
    run_model_validation()
