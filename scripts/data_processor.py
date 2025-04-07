#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
import json
from datetime import datetime
import requests
import zipfile
import io
import argparse
from tqdm import tqdm
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Dataset URLs
DATASETS = {
    "movielens-small": "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip",
    "movielens-full": "https://files.grouplens.org/datasets/movielens/ml-latest.zip",
    "amazon-books": "http://snap.stanford.edu/data/amazon/productGraph/categoryFiles/ratings_Books.csv",
    "yelp": "https://www.yelp.com/dataset"  # This requires manual download
}

def download_dataset(dataset_name, output_dir):
    """Download a dataset by name and extract it if needed"""
    if dataset_name not in DATASETS:
        raise ValueError(f"Dataset {dataset_name} not found. Available datasets: {list(DATASETS.keys())}")
    
    url = DATASETS[dataset_name]
    output_path = os.path.join(output_dir, dataset_name)
    os.makedirs(output_path, exist_ok=True)
    
    logger.info(f"Downloading {dataset_name} from {url}")
    
    if url.endswith('.zip'):
        # Download and extract ZIP file
        response = requests.get(url, stream=True)
        z = zipfile.ZipFile(io.BytesIO(response.content))
        z.extractall(output_path)
        logger.info(f"Extracted ZIP file to {output_path}")
    else:
        # Direct CSV download
        response = requests.get(url)
        filename = url.split('/')[-1]
        with open(os.path.join(output_path, filename), 'wb') as f:
            f.write(response.content)
        logger.info(f"Downloaded file to {os.path.join(output_path, filename)}")
    
    return output_path

def process_movielens(dataset_path, output_path):
    """Process the MovieLens dataset into the format needed for our recommendation system"""
    # Load ratings data
    ratings_file = os.path.join(dataset_path, 'ratings.csv')
    if not os.path.exists(ratings_file):
        # Look for the file in subdirectories
        for root, dirs, files in os.walk(dataset_path):
            if 'ratings.csv' in files:
                ratings_file = os.path.join(root, 'ratings.csv')
                break
    
    ratings_df = pd.read_csv(ratings_file)
    logger.info(f"Loaded {len(ratings_df)} ratings from {ratings_file}")
    
    # Load movies data
    movies_file = os.path.join(dataset_path, 'movies.csv')
    if not os.path.exists(movies_file):
        # Look for the file in subdirectories
        for root, dirs, files in os.walk(dataset_path):
            if 'movies.csv' in files:
                movies_file = os.path.join(root, 'movies.csv')
                break
    
    movies_df = pd.read_csv(movies_file)
    logger.info(f"Loaded {len(movies_df)} movies from {movies_file}")
    
    # Process data for our system format
    
    # 1. Content items
    content_items = []
    for _, row in tqdm(movies_df.iterrows(), total=len(movies_df), desc="Processing movies"):
        genres = row['genres'].split('|') if row['genres'] != '(no genres listed)' else []
        
        content_item = {
            "content_id": str(row['movieId']),
            "title": row['title'],
            "description": f"A movie released with genres: {', '.join(genres)}",
            "content_type": "movie",
            "metadata": {
                "genres": genres,
                "year": int(row['title'].strip()[-5:-1]) if row['title'].strip()[-5:-1].isdigit() else None
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        content_items.append(content_item)
    
    # 2. User interactions
    interactions = []
    for _, row in tqdm(ratings_df.iterrows(), total=len(ratings_df), desc="Processing ratings"):
        interaction = {
            "user_id": str(int(row['userId'])),
            "content_id": str(int(row['movieId'])),
            "interaction_type": "rating",
            "value": float(row['rating']),
            "timestamp": datetime.fromtimestamp(row['timestamp']).isoformat(),
            "metadata": {}
        }
        interactions.append(interaction)
    
    # 3. Create user profiles based on interactions
    user_ids = ratings_df['userId'].unique()
    user_profiles = []
    
    for user_id in tqdm(user_ids, desc="Creating user profiles"):
        user_interactions = ratings_df[ratings_df['userId'] == user_id]
        liked_genres = set()
        
        # Find genres from highly rated movies
        for _, row in user_interactions[user_interactions['rating'] >= 4].iterrows():
            movie = movies_df[movies_df['movieId'] == row['movieId']]
            if not movie.empty:
                genres = movie.iloc[0]['genres'].split('|')
                liked_genres.update(genres)
        
        user_profile = {
            "user_id": str(int(user_id)),
            "preferences": {
                "preferred_genres": list(liked_genres)
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        user_profiles.append(user_profile)
    
    # Save processed data
    os.makedirs(output_path, exist_ok=True)
    
    with open(os.path.join(output_path, 'content_items.json'), 'w') as f:
        json.dump(content_items, f, indent=2)
    
    with open(os.path.join(output_path, 'interactions.json'), 'w') as f:
        json.dump(interactions, f, indent=2)
    
    with open(os.path.join(output_path, 'user_profiles.json'), 'w') as f:
        json.dump(user_profiles, f, indent=2)
    
    logger.info(f"Saved processed data to {output_path}")
    logger.info(f"Total content items: {len(content_items)}")
    logger.info(f"Total interactions: {len(interactions)}")
    logger.info(f"Total user profiles: {len(user_profiles)}")
    
    # Create a smaller sample for testing
    sample_size = min(1000, len(interactions))
    sample_interactions = interactions[:sample_size]
    
    # Get unique user_ids and content_ids from the sample
    sample_user_ids = set(i["user_id"] for i in sample_interactions)
    sample_content_ids = set(i["content_id"] for i in sample_interactions)
    
    # Filter content_items and user_profiles for the sample
    sample_content_items = [c for c in content_items if c["content_id"] in sample_content_ids]
    sample_user_profiles = [u for u in user_profiles if u["user_id"] in sample_user_ids]
    
    # Save sample data
    sample_path = os.path.join(output_path, 'sample')
    os.makedirs(sample_path, exist_ok=True)
    
    with open(os.path.join(sample_path, 'content_items.json'), 'w') as f:
        json.dump(sample_content_items, f, indent=2)
    
    with open(os.path.join(sample_path, 'interactions.json'), 'w') as f:
        json.dump(sample_interactions, f, indent=2)
    
    with open(os.path.join(sample_path, 'user_profiles.json'), 'w') as f:
        json.dump(sample_user_profiles, f, indent=2)
    
    logger.info(f"Saved sample data to {sample_path}")
    logger.info(f"Sample content items: {len(sample_content_items)}")
    logger.info(f"Sample interactions: {len(sample_interactions)}")
    logger.info(f"Sample user profiles: {len(sample_user_profiles)}")

def main():
    parser = argparse.ArgumentParser(description='Download and process datasets for recommendation system')
    parser.add_argument('--dataset', type=str, default='movielens-small', 
                        choices=list(DATASETS.keys()),
                        help='Dataset to download and process')
    parser.add_argument('--raw-dir', type=str, default='data/raw',
                        help='Directory to store raw data')
    parser.add_argument('--processed-dir', type=str, default='data/processed',
                        help='Directory to store processed data')
    args = parser.parse_args()
    
    # Download dataset
    dataset_path = download_dataset(args.dataset, args.raw_dir)
    
    # Process dataset based on type
    if args.dataset.startswith('movielens'):
        process_movielens(dataset_path, os.path.join(args.processed_dir, args.dataset))
    else:
        logger.warning(f"Processing for {args.dataset} not implemented yet")

if __name__ == "__main__":
    main() 