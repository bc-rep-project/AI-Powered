#!/usr/bin/env python3
import os
import json
import logging
import argparse
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import matplotlib.pyplot as plt
import tensorflow as tf
import seaborn as sns
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import RecommendationModel from train_model.py
import sys
sys.path.append('.')
try:
    from scripts.train_model import RecommendationModel
except ImportError:
    try:
        from train_model import RecommendationModel
    except ImportError:
        logger.error("Could not import RecommendationModel. Make sure scripts/train_model.py exists.")
        sys.exit(1)

def load_interactions(data_path):
    """Load interaction data from JSON file"""
    with open(os.path.join(data_path, 'interactions.json'), 'r') as f:
        interactions = json.load(f)
    
    # Convert to DataFrame
    df = pd.DataFrame(interactions)
    
    return df

def compute_ndcg(relevance_scores, k=10):
    """Compute Normalized Discounted Cumulative Gain (NDCG)"""
    if len(relevance_scores) == 0:
        return 0.0
    
    # If k is greater than the number of items, use all items
    k = min(k, len(relevance_scores))
    
    # Get top k items
    top_k_scores = relevance_scores[:k]
    
    # Compute DCG
    dcg = top_k_scores[0] + sum([score / np.log2(i + 1) for i, score in enumerate(top_k_scores, 2)])
    
    # Compute IDCG (ideal DCG)
    ideal_scores = sorted(relevance_scores, reverse=True)[:k]
    idcg = ideal_scores[0] + sum([score / np.log2(i + 1) for i, score in enumerate(ideal_scores, 2)])
    
    if idcg == 0:
        return 0.0
    
    return dcg / idcg

def evaluate_model(model, test_interactions, all_content_ids, k_values=[5, 10, 20]):
    """Evaluate a recommendation model using ranking metrics"""
    # Group interactions by user
    user_interactions = {}
    for _, row in test_interactions.iterrows():
        user_id = row['user_id']
        content_id = row['content_id']
        rating = float(row['value'])
        
        if user_id not in user_interactions:
            user_interactions[user_id] = {}
        
        user_interactions[user_id][content_id] = rating
    
    # Metrics to track
    metrics = {f'precision@{k}': [] for k in k_values}
    metrics.update({f'recall@{k}': [] for k in k_values})
    metrics.update({f'ndcg@{k}': [] for k in k_values})
    
    # Evaluate for each user
    for user_id, interactions in tqdm(user_interactions.items(), desc="Evaluating users"):
        # Skip users with too few interactions
        if len(interactions) < 2:
            continue
        
        # Get recommendations for this user
        try:
            recommendations = model.get_recommendations(user_id, top_k=max(k_values))
            recommended_items = [content_id for content_id, _ in recommendations]
            
            # Relevant items are those with high ratings (e.g., >= 4)
            relevant_items = [content_id for content_id, rating in interactions.items() if rating >= 4]
            
            # If no relevant items, skip this user
            if not relevant_items:
                continue
            
            # Calculate metrics for each k
            for k in k_values:
                # Precision@k
                recommended_k = recommended_items[:k]
                hits = len(set(recommended_k) & set(relevant_items))
                precision = hits / k if k > 0 else 0
                metrics[f'precision@{k}'].append(precision)
                
                # Recall@k
                recall = hits / len(relevant_items) if relevant_items else 0
                metrics[f'recall@{k}'].append(recall)
                
                # NDCG@k
                # Create relevance scores for recommended items (1 if relevant, 0 if not)
                relevance = [1 if item in relevant_items else 0 for item in recommended_k]
                ndcg = compute_ndcg(relevance, k)
                metrics[f'ndcg@{k}'].append(ndcg)
        
        except Exception as e:
            logger.warning(f"Error evaluating user {user_id}: {str(e)}")
            continue
    
    # Calculate average metrics
    result = {}
    for metric, values in metrics.items():
        if values:
            result[metric] = np.mean(values)
        else:
            result[metric] = 0.0
    
    return result

def evaluate_rating_prediction(model, test_interactions):
    """Evaluate rating prediction accuracy"""
    # Prepare data
    user_ids = []
    content_ids = []
    actual_ratings = []
    
    for _, row in test_interactions.iterrows():
        user_ids.append(row['user_id'])
        content_ids.append(row['content_id'])
        actual_ratings.append(float(row['value']))
    
    # Get predictions
    predicted_ratings = []
    for user_id, content_id in tqdm(zip(user_ids, content_ids), desc="Predicting ratings", total=len(user_ids)):
        try:
            # Get user embedding index
            user_encoded = model.user_encoder.transform([user_id])[0]
            # Get content embedding index
            content_encoded = model.content_encoder.transform([content_id])[0]
            
            # Predict rating
            prediction = model.model.predict(
                [[user_encoded], [content_encoded]], 
                verbose=0
            )[0][0]
            
            predicted_ratings.append(float(prediction))
        except Exception as e:
            logger.warning(f"Error predicting rating for user {user_id}, content {content_id}: {str(e)}")
            predicted_ratings.append(np.nan)
    
    # Remove nan values
    valid_indices = ~np.isnan(predicted_ratings)
    actual_ratings = np.array(actual_ratings)[valid_indices]
    predicted_ratings = np.array(predicted_ratings)[valid_indices]
    
    # Calculate metrics
    mae = np.mean(np.abs(actual_ratings - predicted_ratings))
    rmse = np.sqrt(np.mean(np.square(actual_ratings - predicted_ratings)))
    
    return {
        'mae': mae,
        'rmse': rmse,
        'actual_ratings': actual_ratings,
        'predicted_ratings': predicted_ratings
    }

def plot_rating_prediction(actual, predicted, save_path=None):
    """Plot actual vs predicted ratings"""
    plt.figure(figsize=(10, 6))
    
    # Create scatter plot
    plt.scatter(actual, predicted, alpha=0.3)
    
    # Add diagonal line (perfect prediction)
    min_val = min(min(actual), min(predicted))
    max_val = max(max(actual), max(predicted))
    plt.plot([min_val, max_val], [min_val, max_val], 'r--', label='Perfect prediction')
    
    # Add regression line
    z = np.polyfit(actual, predicted, 1)
    p = np.poly1d(z)
    plt.plot(actual, p(actual), 'b-', label=f'Regression line (y = {z[0]:.3f}x + {z[1]:.3f})')
    
    # Add labels and title
    plt.xlabel('Actual Ratings')
    plt.ylabel('Predicted Ratings')
    plt.title('Actual vs Predicted Ratings')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    if save_path:
        plt.savefig(save_path)
        logger.info(f"Rating prediction plot saved to {save_path}")
    else:
        plt.show()

def plot_rating_distribution(actual, predicted, save_path=None):
    """Plot distribution of actual and predicted ratings"""
    plt.figure(figsize=(12, 5))
    
    # Actual ratings distribution
    plt.subplot(1, 2, 1)
    sns.histplot(actual, bins=10, kde=True)
    plt.title('Actual Rating Distribution')
    plt.xlabel('Rating')
    plt.ylabel('Count')
    
    # Predicted ratings distribution
    plt.subplot(1, 2, 2)
    sns.histplot(predicted, bins=10, kde=True)
    plt.title('Predicted Rating Distribution')
    plt.xlabel('Rating')
    plt.ylabel('Count')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path)
        logger.info(f"Rating distribution plot saved to {save_path}")
    else:
        plt.show()

def main():
    parser = argparse.ArgumentParser(description='Evaluate recommendation model')
    parser.add_argument('--model-path', type=str, required=True,
                        help='Path to the trained model')
    parser.add_argument('--data-path', type=str, required=True,
                        help='Path to the test data directory')
    parser.add_argument('--output-dir', type=str, default='evaluation',
                        help='Directory to save evaluation results')
    parser.add_argument('--k-values', type=int, nargs='+', default=[5, 10, 20],
                        help='K values for evaluation metrics')
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load model
    logger.info(f"Loading model from {args.model_path}")
    model = RecommendationModel.load(args.model_path)
    
    # Load test data
    logger.info(f"Loading test data from {args.data_path}")
    test_interactions = load_interactions(args.data_path)
    
    # Get all content IDs
    all_content_ids = model.content_encoder.classes_
    
    # Evaluate ranking metrics
    logger.info("Evaluating ranking metrics")
    ranking_metrics = evaluate_model(model, test_interactions, all_content_ids, args.k_values)
    
    # Evaluate rating prediction
    logger.info("Evaluating rating prediction")
    rating_metrics = evaluate_rating_prediction(model, test_interactions)
    
    # Combine metrics
    all_metrics = {
        **ranking_metrics,
        'mae': rating_metrics['mae'],
        'rmse': rating_metrics['rmse']
    }
    
    # Save metrics
    metrics_path = os.path.join(args.output_dir, 'metrics.json')
    with open(metrics_path, 'w') as f:
        json.dump(all_metrics, f, indent=2)
    logger.info(f"Metrics saved to {metrics_path}")
    
    # Plot results
    plot_rating_prediction(
        rating_metrics['actual_ratings'],
        rating_metrics['predicted_ratings'],
        save_path=os.path.join(args.output_dir, 'rating_prediction.png')
    )
    
    plot_rating_distribution(
        rating_metrics['actual_ratings'],
        rating_metrics['predicted_ratings'],
        save_path=os.path.join(args.output_dir, 'rating_distribution.png')
    )
    
    # Print summary
    logger.info("Evaluation summary:")
    for metric, value in all_metrics.items():
        logger.info(f"  {metric}: {value:.4f}")

if __name__ == "__main__":
    main() 