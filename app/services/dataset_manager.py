"""
Dataset manager for efficiently downloading and processing the MovieLens dataset.
Optimized for Render.com's free tier limitations (512MB RAM, ephemeral filesystem).
"""

import os
import logging
import json
import zipfile
import requests
import pandas as pd
import numpy as np
from io import BytesIO
import asyncio
import shutil
from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime, timedelta
import time
import uuid
from ..db.mongodb import get_mongodb
from ..db.redis import get_redis
from ..core.config import settings

logger = logging.getLogger(__name__)

# Constants for MovieLens datasets
MOVIELENS_SMALL_URL = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"
MOVIELENS_FULL_URL = "https://files.grouplens.org/datasets/movielens/ml-latest.zip"

# Constants for data paths
DATA_DIR = "data"
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
MOVIELENS_SMALL_DIR = os.path.join(PROCESSED_DIR, "movielens-small")
MOVIELENS_FULL_DIR = os.path.join(PROCESSED_DIR, "movielens-full")

# Configuration
CHUNK_SIZE = 8192  # 8KB chunks for downloading
DOWNLOAD_EXPIRY_DAYS = 7  # Re-download after this many days
BATCH_SIZE = 1000  # Process in batches to save memory

# Ensure directories exist
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(MOVIELENS_SMALL_DIR, exist_ok=True)

class DatasetStatus:
    """Status tracker for dataset operations"""
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.start_time = datetime.now()
        self.progress = 0.0
        self.status = "initializing"
        self.message = "Starting dataset operation"
        self.error = None
    
    async def update(self, status: str, progress: float, message: str, error: Optional[str] = None):
        """Update status and save to Redis"""
        self.status = status
        self.progress = progress
        self.message = message
        self.error = error
        
        # Save status to Redis for tracking
        try:
            redis = await get_redis()
            if redis:
                await redis.hset(
                    f"dataset_job:{self.job_id}",
                    mapping={
                        "status": status,
                        "progress": str(progress),
                        "message": message,
                        "error": error or "",
                        "updated_at": datetime.now().isoformat()
                    }
                )
                # Set expiration to avoid cluttering Redis
                await redis.expire(f"dataset_job:{self.job_id}", 60 * 60 * 24)  # 24 hours
        except Exception as e:
            logger.error(f"Error updating dataset status in Redis: {str(e)}")

async def check_if_recently_downloaded(dataset_type: str = "small") -> bool:
    """Check if dataset was recently downloaded (within DOWNLOAD_EXPIRY_DAYS)"""
    try:
        redis = await get_redis()
        if redis:
            last_download = await redis.get(f"dataset:last_download:{dataset_type}")
            if last_download:
                last_date = datetime.fromisoformat(last_download)
                days_ago = (datetime.now() - last_date).days
                return days_ago < DOWNLOAD_EXPIRY_DAYS
        
        # If Redis not available, check local file
        info_file = os.path.join(PROCESSED_DIR, f"movielens-{dataset_type}", "dataset_info.json")
        if os.path.exists(info_file):
            with open(info_file, 'r') as f:
                info = json.load(f)
                if 'downloaded_at' in info:
                    last_date = datetime.fromisoformat(info['downloaded_at'])
                    days_ago = (datetime.now() - last_date).days
                    return days_ago < DOWNLOAD_EXPIRY_DAYS
                    
        return False
    except Exception as e:
        logger.error(f"Error checking last download time: {str(e)}")
        return False

async def mark_download_complete(dataset_type: str = "small"):
    """Mark the dataset as recently downloaded"""
    timestamp = datetime.now().isoformat()
    try:
        redis = await get_redis()
        if redis:
            await redis.set(f"dataset:last_download:{dataset_type}", timestamp)
            
        # Always update info file as backup
        info_file = os.path.join(PROCESSED_DIR, f"movielens-{dataset_type}", "dataset_info.json")
        
        info = {
            'downloaded_at': timestamp,
            'dataset_type': dataset_type,
            'dataset_version': str(uuid.uuid4())
        }
        
        with open(info_file, 'w') as f:
            json.dump(info, f)
            
    except Exception as e:
        logger.error(f"Error marking download complete: {str(e)}")

async def download_file(url: str, status: DatasetStatus) -> Optional[BytesIO]:
    """Download a file in chunks to minimize memory usage"""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        # Store chunks in memory to avoid disk I/O
        buffer = BytesIO()
        
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                buffer.write(chunk)
                downloaded += len(chunk)
                
                # Update progress
                if total_size > 0:
                    progress = min(0.4, 0.1 + (0.3 * downloaded / total_size))
                    await status.update(
                        "downloading", 
                        progress, 
                        f"Downloading: {downloaded / (1024*1024):.1f}MB / {total_size / (1024*1024):.1f}MB"
                    )
        
        buffer.seek(0)
        return buffer
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        await status.update("failed", 0.1, "Download failed", str(e))
        return None

async def extract_zip(zip_buffer: BytesIO, extract_path: str, status: DatasetStatus) -> bool:
    """Extract a zip file"""
    try:
        await status.update("extracting", 0.4, "Extracting zip file")
        
        with zipfile.ZipFile(zip_buffer) as zip_ref:
            # Get the top-level directory in the zip
            top_dir = None
            for name in zip_ref.namelist():
                parts = name.split('/')
                if len(parts) > 0:
                    if top_dir is None or parts[0] < top_dir:
                        top_dir = parts[0]
            
            # Extract with a mapping function to process entries
            for i, item in enumerate(zip_ref.infolist()):
                # Update status occasionally
                if i % 50 == 0:
                    progress = 0.4 + min(0.2, 0.2 * i / len(zip_ref.infolist()))
                    await status.update("extracting", progress, f"Extracting: {i}/{len(zip_ref.infolist())} files")
                
                # Skip directories
                if item.filename.endswith('/'):
                    continue
                
                # Remove the top directory from the path if it exists
                if top_dir and item.filename.startswith(top_dir + '/'):
                    target_path = os.path.join(extract_path, item.filename[len(top_dir)+1:])
                else:
                    target_path = os.path.join(extract_path, item.filename)
                
                # Ensure the directory exists
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                
                # Extract the file
                with zip_ref.open(item) as source, open(target_path, 'wb') as target:
                    shutil.copyfileobj(source, target)
        
        await status.update("extracted", 0.6, "Extraction complete")
        return True
    except Exception as e:
        logger.error(f"Error extracting zip: {str(e)}")
        await status.update("failed", 0.4, "Extraction failed", str(e))
        return False

async def process_movielens_data(extract_path: str, output_path: str, status: DatasetStatus) -> bool:
    """Process MovieLens data files"""
    try:
        await status.update("processing", 0.6, "Processing MovieLens data")
        
        # Process movies
        movies_file = os.path.join(extract_path, 'movies.csv')
        ratings_file = os.path.join(extract_path, 'ratings.csv')
        tags_file = os.path.join(extract_path, 'tags.csv')
        links_file = os.path.join(extract_path, 'links.csv')
        
        if not os.path.exists(movies_file) or not os.path.exists(ratings_file):
            await status.update("failed", 0.6, "Required data files not found", "movies.csv or ratings.csv not found")
            return False
        
        # Process in batches to save memory
        await status.update("processing", 0.65, "Processing movies data")
        
        # Process movies (usually small enough to fit in memory)
        movies_df = pd.read_csv(movies_file)
        
        # Process movies into a more usable format
        processed_movies = []
        for _, row in movies_df.iterrows():
            genres = [g.strip() for g in row['genres'].split('|') if g != '(no genres listed)']
            
            # Extract year from title if present
            title = row['title']
            year = None
            if title.endswith(')') and '(' in title:
                try:
                    year_str = title[title.rindex('(')+1:title.rindex(')')]
                    if year_str.isdigit():
                        year = int(year_str)
                        title = title[:title.rindex('(')].strip()
                except:
                    pass
            
            processed_movies.append({
                'movie_id': str(row['movieId']),
                'title': title,
                'year': year,
                'genres': genres
            })
        
        # Save processed movies
        os.makedirs(output_path, exist_ok=True)
        with open(os.path.join(output_path, 'movies.json'), 'w') as f:
            json.dump(processed_movies, f)
        
        # Save to MongoDB if available
        mongodb = await get_mongodb()
        if mongodb:
            await status.update("storing", 0.7, "Storing movies in MongoDB")
            # Use bulk operations for efficiency
            operations = []
            for movie in processed_movies:
                operations.append({
                    'replaceOne': {
                        'filter': {'movie_id': movie['movie_id']},
                        'replacement': movie,
                        'upsert': True
                    }
                })
            
            if operations:
                await mongodb.movies.bulk_write(operations)
        
        # Process ratings in batches to save memory
        await status.update("processing", 0.75, "Processing ratings data")
        
        # Read and process ratings in chunks
        interactions = []
        chunks = pd.read_csv(ratings_file, chunksize=BATCH_SIZE)
        
        chunk_count = 0
        for chunk in chunks:
            chunk_count += 1
            for _, row in chunk.iterrows():
                interactions.append({
                    'user_id': str(row['userId']),
                    'content_id': str(row['movieId']),
                    'value': float(row['rating']),
                    'timestamp': int(row['timestamp'])
                })
            
            # Update status for each chunk
            if chunk_count % 10 == 0:
                progress = 0.75 + min(0.15, 0.15 * len(interactions) / (10000))  # Estimate progress
                await status.update("processing", progress, f"Processed {len(interactions)} ratings")
                
                # If MongoDB is available, save interactions in batches to avoid memory buildup
                if mongodb and len(interactions) >= 5000:
                    await store_interactions_batch(mongodb, interactions)
                    interactions = []  # Clear after storing
        
        # Store remaining interactions
        if interactions:
            if mongodb:
                await store_interactions_batch(mongodb, interactions)
            
            # Also save to local file as backup
            with open(os.path.join(output_path, 'interactions.json'), 'w') as f:
                json.dump(interactions, f)
        
        # Process links if available
        if os.path.exists(links_file):
            await status.update("processing", 0.95, "Processing links data")
            links_df = pd.read_csv(links_file)
            
            # Create a mapping from movie ID to links
            links = {}
            for _, row in links_df.iterrows():
                links[str(row['movieId'])] = {
                    'imdb_id': f"tt{row['imdbId']:07d}" if not pd.isna(row['imdbId']) else None,
                    'tmdb_id': str(int(row['tmdbId'])) if not pd.isna(row['tmdbId']) else None
                }
            
            with open(os.path.join(output_path, 'links.json'), 'w') as f:
                json.dump(links, f)
        
        # Mark processing as complete
        await status.update("completed", 1.0, "Data processing complete")
        return True
        
    except Exception as e:
        logger.error(f"Error processing data: {str(e)}")
        await status.update("failed", 0.7, "Data processing failed", str(e))
        return False

async def store_interactions_batch(mongodb, interactions: List[Dict[str, Any]]):
    """Store a batch of interactions in MongoDB"""
    try:
        if not interactions:
            return
            
        # Use bulk operations for efficiency
        operations = []
        for interaction in interactions:
            operations.append({
                'insertOne': {
                    'document': interaction
                }
            })
        
        if operations:
            await mongodb.interactions.bulk_write(operations)
    except Exception as e:
        logger.error(f"Error storing interactions batch: {str(e)}")

async def run_dataset_pipeline(job_id: str, dataset_type: str = "small", force: bool = False) -> bool:
    """
    Run the complete dataset pipeline: download, extract, and process
    """
    status = DatasetStatus(job_id)
    
    try:
        # Set up constants for this dataset type
        if dataset_type == "small":
            dataset_url = MOVIELENS_SMALL_URL
            output_path = MOVIELENS_SMALL_DIR
        else:
            dataset_url = MOVIELENS_FULL_URL
            output_path = MOVIELENS_FULL_DIR
        
        # Check if already downloaded recently
        if not force and await check_if_recently_downloaded(dataset_type):
            logger.info(f"Dataset {dataset_type} was recently downloaded, skipping download")
            await status.update("skipped", 1.0, "Dataset was recently downloaded, skipping download")
            return True
        
        # Ensure directories exist
        os.makedirs(output_path, exist_ok=True)
        
        # Download dataset
        await status.update("downloading", 0.1, f"Downloading MovieLens {dataset_type} dataset")
        zip_buffer = await download_file(dataset_url, status)
        if not zip_buffer:
            return False
        
        # Extract dataset
        extract_path = os.path.join(RAW_DIR, f"movielens-{dataset_type}-temp")
        os.makedirs(extract_path, exist_ok=True)
        
        if not await extract_zip(zip_buffer, extract_path, status):
            return False
        
        # Process dataset
        if not await process_movielens_data(extract_path, output_path, status):
            return False
        
        # Clean up temporary extraction directory
        try:
            shutil.rmtree(extract_path)
        except Exception as e:
            logger.warning(f"Could not clean up temp directory: {str(e)}")
        
        # Mark download as complete
        await mark_download_complete(dataset_type)
        
        await status.update("complete", 1.0, f"MovieLens {dataset_type} dataset pipeline complete")
        return True
        
    except Exception as e:
        error_msg = f"Error in dataset pipeline: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await status.update("failed", 0.0, "Dataset pipeline failed", error_msg)
        return False

async def get_job_status(job_id: str) -> Dict[str, Any]:
    """Get the status of a dataset job"""
    try:
        redis = await get_redis()
        if redis:
            status = await redis.hgetall(f"dataset_job:{job_id}")
            if status:
                # Convert progress to float
                if "progress" in status:
                    status["progress"] = float(status["progress"])
                return status
        return {"status": "not_found", "message": f"Job {job_id} not found"}
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        return {"status": "error", "message": f"Error getting job status: {str(e)}"}

# Movie retrieval functions
async def get_movies(skip: int = 0, limit: int = 20, genre: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get movies from database or local file"""
    try:
        # Try MongoDB first
        mongodb = await get_mongodb()
        movies = []
        
        if mongodb:
            query = {} if genre is None else {"genres": genre}
            cursor = mongodb.movies.find(query).skip(skip).limit(limit)
            async for movie in cursor:
                if "_id" in movie:
                    del movie["_id"]
                movies.append(movie)
            
            if movies:
                return movies
        
        # Fallback to local file
        movies_path = os.path.join(MOVIELENS_SMALL_DIR, "movies.json")
        if os.path.exists(movies_path):
            with open(movies_path, 'r') as f:
                all_movies = json.load(f)
                
                # Filter by genre if specified
                if genre:
                    filtered_movies = [m for m in all_movies if genre in m.get('genres', [])]
                else:
                    filtered_movies = all_movies
                
                # Paginate
                paginated = filtered_movies[skip:skip+limit]
                return paginated
                
        return []
    except Exception as e:
        logger.error(f"Error getting movies: {str(e)}")
        return []

async def count_movies(genre: Optional[str] = None) -> int:
    """Count movies, optionally filtered by genre"""
    try:
        # Try MongoDB first
        mongodb = await get_mongodb()
        
        if mongodb:
            query = {} if genre is None else {"genres": genre}
            count = await mongodb.movies.count_documents(query)
            return count
        
        # Fallback to local file
        movies_path = os.path.join(MOVIELENS_SMALL_DIR, "movies.json")
        if os.path.exists(movies_path):
            with open(movies_path, 'r') as f:
                all_movies = json.load(f)
                
                if genre:
                    return len([m for m in all_movies if genre in m.get('genres', [])])
                else:
                    return len(all_movies)
                
        return 0
    except Exception as e:
        logger.error(f"Error counting movies: {str(e)}")
        return 0

async def get_movie_by_id(movie_id: str) -> Optional[Dict[str, Any]]:
    """Get a movie by ID"""
    try:
        # Try MongoDB first
        mongodb = await get_mongodb()
        
        if mongodb:
            movie = await mongodb.movies.find_one({"movie_id": movie_id})
            if movie:
                if "_id" in movie:
                    del movie["_id"]
                return movie
        
        # Fallback to local file
        movies_path = os.path.join(MOVIELENS_SMALL_DIR, "movies.json")
        if os.path.exists(movies_path):
            with open(movies_path, 'r') as f:
                all_movies = json.load(f)
                for movie in all_movies:
                    if movie.get('movie_id') == movie_id:
                        return movie
                
        return None
    except Exception as e:
        logger.error(f"Error getting movie by ID: {str(e)}")
        return None

async def search_movies_by_title(title: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search movies by title"""
    try:
        # Try MongoDB first
        mongodb = await get_mongodb()
        movies = []
        
        if mongodb:
            # Use text index if available, or regex search
            try:
                cursor = mongodb.movies.find(
                    {"$text": {"$search": title}}
                ).limit(limit)
            except:
                # Fallback to regex if text index not available
                cursor = mongodb.movies.find(
                    {"title": {"$regex": title, "$options": "i"}}
                ).limit(limit)
                
            async for movie in cursor:
                if "_id" in movie:
                    del movie["_id"]
                movies.append(movie)
            
            if movies:
                return movies
        
        # Fallback to local file with basic search
        movies_path = os.path.join(MOVIELENS_SMALL_DIR, "movies.json")
        if os.path.exists(movies_path):
            with open(movies_path, 'r') as f:
                all_movies = json.load(f)
                
                # Simple case-insensitive search
                title_lower = title.lower()
                matches = []
                
                for movie in all_movies:
                    if title_lower in movie.get('title', '').lower():
                        matches.append(movie)
                        if len(matches) >= limit:
                            break
                
                return matches
                
        return []
    except Exception as e:
        logger.error(f"Error searching movies: {str(e)}")
        return []

async def record_interaction(user_id: str, movie_id: str, rating: float) -> bool:
    """Record a user-movie interaction"""
    try:
        # Create interaction object
        interaction = {
            "user_id": user_id,
            "content_id": movie_id,
            "value": float(rating),
            "timestamp": int(time.time())
        }
        
        # Save to MongoDB if available
        mongodb = await get_mongodb()
        if mongodb:
            await mongodb.interactions.insert_one(interaction)
            
            # Increment new interactions counter for model training
            redis = await get_redis()
            if redis:
                await redis.incr("new_interactions_count", 1)
            
            return True
        
        # Fallback to local file
        interactions_path = os.path.join(MOVIELENS_SMALL_DIR, "user_interactions.json")
        
        # Read existing interactions
        existing = []
        if os.path.exists(interactions_path):
            try:
                with open(interactions_path, 'r') as f:
                    existing = json.load(f)
            except Exception as e:
                logger.error(f"Error reading existing interactions: {str(e)}")
                existing = []
        
        # Add new interaction
        existing.append(interaction)
        
        # Write back to file
        with open(interactions_path, 'w') as f:
            json.dump(existing, f)
            
        return True
    except Exception as e:
        logger.error(f"Error recording interaction: {str(e)}")
        return False

async def get_genres() -> List[str]:
    """Get a list of all available genres"""
    try:
        # Try MongoDB first
        mongodb = await get_mongodb()
        
        if mongodb:
            # Use aggregation to get unique genres
            pipeline = [
                {"$unwind": "$genres"},
                {"$group": {"_id": "$genres"}},
                {"$sort": {"_id": 1}}
            ]
            
            genres = []
            async for doc in mongodb.movies.aggregate(pipeline):
                genres.append(doc["_id"])
            
            if genres:
                return genres
        
        # Fallback to local file
        movies_path = os.path.join(MOVIELENS_SMALL_DIR, "movies.json")
        if os.path.exists(movies_path):
            with open(movies_path, 'r') as f:
                all_movies = json.load(f)
                
                # Collect all unique genres
                all_genres = set()
                for movie in all_movies:
                    for genre in movie.get('genres', []):
                        all_genres.add(genre)
                
                return sorted(list(all_genres))
                
        return []
    except Exception as e:
        logger.error(f"Error getting genres: {str(e)}")
        return [] 