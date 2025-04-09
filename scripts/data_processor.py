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
import gc
import shutil

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

def process_movielens(dataset_path, output_path, sample_ratio=None, batch_size=5000, mongodb_uri=None):
    """
    Process the MovieLens dataset into the format needed for our recommendation system
    
    Args:
        dataset_path: Path to the raw dataset
        output_path: Path to save processed data
        sample_ratio: Fraction of data to use (0.0-1.0). If None, use all data.
        batch_size: Number of records to process at once to reduce memory usage
        mongodb_uri: If provided, save data to MongoDB instead of files
    """
    start_time = time.time()
    logger.info(f"Starting MovieLens processing with sample_ratio={sample_ratio}, batch_size={batch_size}")
    
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
            # Use chunks to avoid loading everything into memory
            ratings_chunks = pd.read_csv(ratings_file, chunksize=batch_size)
            ratings_list = []
            for chunk in ratings_chunks:
                ratings_list.append(chunk)
            ratings_df = pd.concat(ratings_list)
            logger.info(f"Loaded {len(ratings_df)} ratings from {ratings_file}")
        except Exception as e:
            logger.error(f"Error reading ratings file: {str(e)}")
            raise
    
    # Apply sampling if requested
    if sample_ratio and 0 < sample_ratio < 1:
        original_size = len(ratings_df)
        # Sample users instead of random ratings to maintain user behavior patterns
        user_ids = ratings_df['userId'].unique()
        sampled_users = np.random.choice(
            user_ids, 
            size=int(len(user_ids) * sample_ratio), 
            replace=False
        )
        ratings_df = ratings_df[ratings_df['userId'].isin(sampled_users)]
        logger.info(f"Sampled {len(ratings_df)} ratings ({len(ratings_df)/original_size:.1%}) from {len(sampled_users)} users")
    
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
    
    # Only keep movies that have ratings in our sampled dataset
    if sample_ratio and 0 < sample_ratio < 1:
        rated_movie_ids = ratings_df['movieId'].unique()
        movies_df = movies_df[movies_df['movieId'].isin(rated_movie_ids)]
        logger.info(f"Filtered to {len(movies_df)} movies that have ratings in the sampled dataset")
    
    # Initialize MongoDB client if URI is provided
    mongo_client = None
    if mongodb_uri:
        try:
            from pymongo import MongoClient
            mongo_client = MongoClient(mongodb_uri)
            db = mongo_client["recommendation_engine"]
            logger.info(f"Connected to MongoDB at {mongodb_uri}")
            
            # Create indices for better performance
            db.content_items.create_index("content_id")
            db.interactions.create_index("user_id")
            db.interactions.create_index("content_id")
            db.user_profiles.create_index("user_id")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            mongo_client = None
    
    # Process content items in batches
    logger.info("Processing content items...")
    content_items = []
    batch_idx = 0
    
    for i in range(0, len(movies_df), batch_size):
        batch_idx += 1
        batch = movies_df.iloc[i:i+batch_size]
        batch_content = []
        
        for _, row in tqdm(batch.iterrows(), total=len(batch), desc=f"Processing movies batch {batch_idx}"):
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
                batch_content.append(content_item)
            except Exception as e:
                logger.warning(f"Error processing movie {row.get('movieId', 'unknown')}: {str(e)}")
                continue
        
        # Store the batch
        if mongo_client:
            if batch_content:
                try:
                    db.content_items.insert_many(batch_content)
                    logger.info(f"Inserted {len(batch_content)} content items to MongoDB (batch {batch_idx})")
                except Exception as e:
                    logger.error(f"Error inserting content items to MongoDB: {str(e)}")
        
        content_items.extend(batch_content)
        
        # Save intermediate results
        if i > 0 and (i + batch_size) % (batch_size * 5) == 0:
            try:
                os.makedirs(output_path, exist_ok=True)
                with open(os.path.join(output_path, f'content_items_part{batch_idx}.json'), 'w') as f:
                    json.dump(batch_content, f)
                logger.info(f"Saved intermediate content items to {output_path}/content_items_part{batch_idx}.json")
            except Exception as e:
                logger.error(f"Error saving intermediate content items: {str(e)}")
        
        # Run garbage collection to free memory
        gc.collect()
    
    if not content_items:
        raise ValueError("No content items were processed. Check the movies data format.")
    
    # Process user interactions in batches
    logger.info("Processing user interactions...")
    interactions = []
    batch_idx = 0
    
    for i in range(0, len(ratings_df), batch_size):
        batch_idx += 1
        batch = ratings_df.iloc[i:i+batch_size]
        batch_interactions = []
        
        for _, row in tqdm(batch.iterrows(), total=len(batch), desc=f"Processing ratings batch {batch_idx}"):
            try:
                interaction = {
                    "user_id": str(int(row['userId'])),
                    "content_id": str(int(row['movieId'])),
                    "interaction_type": "rating",
                    "value": float(row['rating']),
                    "timestamp": datetime.fromtimestamp(row['timestamp']).isoformat(),
                    "metadata": {}
                }
                batch_interactions.append(interaction)
            except Exception as e:
                logger.warning(f"Error processing rating: {str(e)}")
                continue
        
        # Store the batch
        if mongo_client:
            if batch_interactions:
                try:
                    db.interactions.insert_many(batch_interactions)
                    logger.info(f"Inserted {len(batch_interactions)} interactions to MongoDB (batch {batch_idx})")
                except Exception as e:
                    logger.error(f"Error inserting interactions to MongoDB: {str(e)}")
        
        interactions.extend(batch_interactions)
        
        # Save intermediate results
        if i > 0 and (i + batch_size) % (batch_size * 5) == 0:
            try:
                os.makedirs(output_path, exist_ok=True)
                with open(os.path.join(output_path, f'interactions_part{batch_idx}.json'), 'w') as f:
                    json.dump(batch_interactions, f)
                logger.info(f"Saved intermediate interactions to {output_path}/interactions_part{batch_idx}.json")
            except Exception as e:
                logger.error(f"Error saving intermediate interactions: {str(e)}")
        
        # Run garbage collection to free memory
        gc.collect()
    
    if not interactions:
        raise ValueError("No interactions were processed. Check the ratings data format.")
    
    # 3. Create user profiles based on interactions
    logger.info("Creating user profiles...")
    user_ids = ratings_df['userId'].unique()
    user_profiles = []
    batch_size_users = max(100, int(len(user_ids) / 10))  # Smaller batch size for user profiles
    
    for i in range(0, len(user_ids), batch_size_users):
        batch_user_ids = user_ids[i:i+batch_size_users]
        batch_profiles = []
        
        for user_id in tqdm(batch_user_ids, desc=f"Creating user profiles batch {i//batch_size_users + 1}"):
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
                batch_profiles.append(user_profile)
            except Exception as e:
                logger.warning(f"Error processing user profile for user {user_id}: {str(e)}")
                continue
        
        # Store the batch
        if mongo_client:
            if batch_profiles:
                try:
                    db.user_profiles.insert_many(batch_profiles)
                    logger.info(f"Inserted {len(batch_profiles)} user profiles to MongoDB")
                except Exception as e:
                    logger.error(f"Error inserting user profiles to MongoDB: {str(e)}")
        
        user_profiles.extend(batch_profiles)
        
        # Run garbage collection to free memory
        gc.collect()
    
    # Save processed data to files
    os.makedirs(output_path, exist_ok=True)
    
    logger.info(f"Saving final output files to {output_path}...")
    with open(os.path.join(output_path, 'content_items.json'), 'w') as f:
        json.dump(content_items, f, indent=2)
    
    with open(os.path.join(output_path, 'interactions.json'), 'w') as f:
        json.dump(interactions, f, indent=2)
    
    with open(os.path.join(output_path, 'user_profiles.json'), 'w') as f:
        json.dump(user_profiles, f, indent=2)
    
    # Save metadata
    metadata = {
        "processed_at": datetime.now().isoformat(),
        "total_content_items": len(content_items),
        "total_interactions": len(interactions),
        "total_users": len(user_profiles),
        "sample_ratio": sample_ratio,
        "processing_time_seconds": time.time() - start_time
    }
    
    with open(os.path.join(output_path, 'metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"Saved processed data to {output_path}")
    logger.info(f"Total content items: {len(content_items)}")
    logger.info(f"Total interactions: {len(interactions)}")
    logger.info(f"Total user profiles: {len(user_profiles)}")
    logger.info(f"Processing time: {time.time() - start_time:.2f} seconds")
    
    # Close MongoDB connection if open
    if mongo_client:
        mongo_client.close()
        logger.info("Closed MongoDB connection")
    
    # Create a smaller sample for testing
    sample_path = os.path.join(output_path, 'sample')
    os.makedirs(sample_path, exist_ok=True)
    
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
    parser.add_argument('--sample-ratio', type=float, default=None,
                        help='Fraction of data to use (0.0-1.0). If None, use all data.')
    parser.add_argument('--batch-size', type=int, default=5000,
                        help='Number of records to process at once to reduce memory usage')
    parser.add_argument('--mongodb-uri', type=str, default=None,
                        help='If provided, save data to MongoDB instead of files')
    args = parser.parse_args()
    
    try:
        # Download dataset
        dataset_path = download_dataset(args.dataset, args.raw_dir)
        
        # Process dataset based on type
        if args.dataset.startswith('movielens'):
            process_movielens(dataset_path, os.path.join(args.processed_dir, args.dataset), args.sample_ratio, args.batch_size, args.mongodb_uri)
        else:
            logger.warning(f"Processing for {args.dataset} not implemented yet")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error processing dataset: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 