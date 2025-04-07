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
import sys
import time

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

def download_dataset(dataset_name, output_dir, max_retries=3):
    """Download a dataset by name and extract it if needed"""
    if dataset_name not in DATASETS:
        raise ValueError(f"Dataset {dataset_name} not found. Available datasets: {list(DATASETS.keys())}")
    
    url = DATASETS[dataset_name]
    output_path = os.path.join(output_dir, dataset_name)
    os.makedirs(output_path, exist_ok=True)
    
    logger.info(f"Downloading {dataset_name} from {url}")
    
    # Handle retries
    for attempt in range(max_retries):
        try:
            if url.endswith('.zip'):
                # Download and extract ZIP file with progress bar
                response = requests.get(url, stream=True)
                response.raise_for_status()  # Raise an exception for bad responses
                
                total_size = int(response.headers.get('content-length', 0))
                block_size = 1024  # 1 Kibibyte
                progress_bar = tqdm(total=total_size, unit='iB', unit_scale=True)
                
                content = io.BytesIO()
                for data in response.iter_content(block_size):
                    progress_bar.update(len(data))
                    content.write(data)
                progress_bar.close()
                
                if total_size != 0 and progress_bar.n != total_size:
                    logger.warning("Downloaded size does not match expected size")
                
                content.seek(0)
                with zipfile.ZipFile(content) as z:
                    z.extractall(output_path)
                logger.info(f"Extracted ZIP file to {output_path}")
            else:
                # Direct CSV download
                response = requests.get(url)
                response.raise_for_status()
                filename = url.split('/')[-1]
                with open(os.path.join(output_path, filename), 'wb') as f:
                    f.write(response.content)
                logger.info(f"Downloaded file to {os.path.join(output_path, filename)}")
            
            # If we get here, download was successful
            break
        except requests.exceptions.RequestException as e:
            logger.error(f"Download attempt {attempt+1}/{max_retries} failed: {str(e)}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error("All download attempts failed")
                raise
    
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
        
        # If still not found, look for ratings.dat (older MovieLens format)
        if not os.path.exists(ratings_file):
            for root, dirs, files in os.walk(dataset_path):
                if 'ratings.dat' in files:
                    ratings_file = os.path.join(root, 'ratings.dat')
                    logger.info("Found ratings.dat instead of ratings.csv, will convert format")
                    break
    
    # Check if we found ratings data
    if not os.path.exists(ratings_file):
        raise FileNotFoundError(f"Could not find ratings data in {dataset_path}")
    
    # Handle different file formats
    if ratings_file.endswith('.dat'):
        # Convert old format to new format
        logger.info(f"Converting {ratings_file} to CSV format")
        ratings_data = []
        with open(ratings_file, 'r', encoding='latin-1') as f:
            for line in f:
                user_id, movie_id, rating, timestamp = line.strip().split('::')
                ratings_data.append({
                    'userId': int(user_id),
                    'movieId': int(movie_id),
                    'rating': float(rating),
                    'timestamp': int(timestamp)
                })
        ratings_df = pd.DataFrame(ratings_data)
    else:
        # Standard CSV format
        try:
            ratings_df = pd.read_csv(ratings_file)
            logger.info(f"Loaded {len(ratings_df)} ratings from {ratings_file}")
        except Exception as e:
            logger.error(f"Error reading ratings file: {str(e)}")
            raise
    
    # Load movies data
    movies_file = os.path.join(dataset_path, 'movies.csv')
    if not os.path.exists(movies_file):
        # Look for the file in subdirectories
        for root, dirs, files in os.walk(dataset_path):
            if 'movies.csv' in files:
                movies_file = os.path.join(root, 'movies.csv')
                break
        
        # If still not found, look for movies.dat (older MovieLens format)
        if not os.path.exists(movies_file):
            for root, dirs, files in os.walk(dataset_path):
                if 'movies.dat' in files:
                    movies_file = os.path.join(root, 'movies.dat')
                    logger.info("Found movies.dat instead of movies.csv, will convert format")
                    break
    
    # Check if we found movies data
    if not os.path.exists(movies_file):
        raise FileNotFoundError(f"Could not find movies data in {dataset_path}")
    
    # Handle different file formats
    if movies_file.endswith('.dat'):
        # Convert old format to new format
        logger.info(f"Converting {movies_file} to CSV format")
        movies_data = []
        with open(movies_file, 'r', encoding='latin-1') as f:
            for line in f:
                parts = line.strip().split('::')
                movie_id = int(parts[0])
                title = parts[1]
                genres = parts[2]
                movies_data.append({
                    'movieId': movie_id,
                    'title': title,
                    'genres': genres
                })
        movies_df = pd.DataFrame(movies_data)
    else:
        # Standard CSV format
        try:
            movies_df = pd.read_csv(movies_file)
            logger.info(f"Loaded {len(movies_df)} movies from {movies_file}")
        except Exception as e:
            logger.error(f"Error reading movies file: {str(e)}")
            raise
    
    # Process data for our system format
    
    # 1. Content items
    content_items = []
    for _, row in tqdm(movies_df.iterrows(), total=len(movies_df), desc="Processing movies"):
        try:
            genres = row['genres'].split('|') if row['genres'] != '(no genres listed)' else []
            
            # Try to extract year from title (handle various formats)
            year = None
            title_str = str(row['title'])
            if '(' in title_str and ')' in title_str:
                year_str = title_str[title_str.rfind('(')+1:title_str.rfind(')')]
                if year_str.isdigit() and len(year_str) == 4:
                    year = int(year_str)
            
            content_item = {
                "content_id": str(row['movieId']),
                "title": title_str,
                "description": f"A movie released with genres: {', '.join(genres)}",
                "content_type": "movie",
                "metadata": {
                    "genres": genres,
                    "year": year
                },
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            content_items.append(content_item)
        except Exception as e:
            logger.warning(f"Error processing movie {row.get('movieId', 'unknown')}: {str(e)}")
            continue
    
    if not content_items:
        raise ValueError("No content items were processed. Check the movies data format.")
    
    # 2. User interactions
    interactions = []
    for _, row in tqdm(ratings_df.iterrows(), total=len(ratings_df), desc="Processing ratings"):
        try:
            interaction = {
                "user_id": str(int(row['userId'])),
                "content_id": str(int(row['movieId'])),
                "interaction_type": "rating",
                "value": float(row['rating']),
                "timestamp": datetime.fromtimestamp(row['timestamp']).isoformat(),
                "metadata": {}
            }
            interactions.append(interaction)
        except Exception as e:
            logger.warning(f"Error processing rating: {str(e)}")
            continue
    
    if not interactions:
        raise ValueError("No interactions were processed. Check the ratings data format.")
    
    # 3. Create user profiles based on interactions
    user_ids = ratings_df['userId'].unique()
    user_profiles = []
    
    for user_id in tqdm(user_ids, desc="Creating user profiles"):
        try:
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
        except Exception as e:
            logger.warning(f"Error processing user profile for user {user_id}: {str(e)}")
            continue
    
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
    try:
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
    except Exception as e:
        logger.warning(f"Error creating sample data: {str(e)}, but continuing anyway")

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
    
    try:
        # Download dataset
        dataset_path = download_dataset(args.dataset, args.raw_dir)
        
        # Process dataset based on type
        if args.dataset.startswith('movielens'):
            process_movielens(dataset_path, os.path.join(args.processed_dir, args.dataset))
        else:
            logger.warning(f"Processing for {args.dataset} not implemented yet")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error processing dataset: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 