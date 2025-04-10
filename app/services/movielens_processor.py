"""
Optimized MovieLens dataset processor for free tier Render.com.
This module handles downloading, processing, and sampling the MovieLens dataset
with minimal resource usage and background processing.
"""

import os
import logging
import json
import aiohttp
import asyncio
import zipfile
import pandas as pd
import io
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import time
from pathlib import Path

from ..core.config import settings
from ..utils.resource_manager import resource_intensive_task, process_in_chunks

logger = logging.getLogger(__name__)

# Constants
MOVIELENS_URLS = {
    "small": "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip",
    "full": "https://files.grouplens.org/datasets/movielens/ml-latest.zip"
}

class ProcessingStatus:
    """Status tracker for dataset processing."""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.status = "initialized"
        self.progress = 0.0
        self.message = "Initialized dataset processing"
        self.error = None
        self.start_time = datetime.now()
        self.update_time = datetime.now()
    
    async def update(self, status: str, progress: float, message: str, error: Optional[str] = None):
        """Update processing status."""
        self.status = status
        self.progress = progress
        self.message = message
        self.error = error
        self.update_time = datetime.now()
        
        # Log status update
        if error:
            logger.error(f"Job {self.job_id}: {status} ({progress:.1%}) - {message}. Error: {error}")
        else:
            logger.info(f"Job {self.job_id}: {status} ({progress:.1%}) - {message}")
        
        # Here you could persist status to DB if needed
        
        # Simulate database write with resource monitoring
        await asyncio.sleep(0.1)

async def download_file(url: str, status: ProcessingStatus) -> Optional[io.BytesIO]:
    """
    Download a file from a URL into memory.
    
    Args:
        url: URL to download
        status: Status tracker to update progress
        
    Returns:
        BytesIO object containing the downloaded data or None if download failed
    """
    try:
        await status.update("downloading", 0.05, f"Downloading from {url}")
        
        timeout = aiohttp.ClientTimeout(total=settings.DOWNLOAD_TIMEOUT)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    await status.update(
                        "failed", 
                        0.0, 
                        f"Failed to download: HTTP {response.status}", 
                        f"HTTP {response.status}"
                    )
                    return None
                
                # Download with progress reporting
                total_size = int(response.headers.get("content-length", 0))
                buffer = io.BytesIO()
                downloaded = 0
                
                # Download in chunks to show progress and prevent memory issues
                chunk_size = 1024 * 1024  # 1 MB chunks
                async for data in response.content.iter_chunked(chunk_size):
                    buffer.write(data)
                    downloaded += len(data)
                    
                    # Update progress if we know the total size
                    if total_size > 0:
                        progress = 0.05 + (downloaded / total_size) * 0.15  # 5-20% progress
                        await status.update(
                            "downloading", 
                            progress, 
                            f"Downloading: {downloaded/1024/1024:.1f} MB / {total_size/1024/1024:.1f} MB"
                        )
                    
                    # Add a small sleep to prevent CPU spikes
                    await asyncio.sleep(0.01)
                
                buffer.seek(0)
                await status.update("downloaded", 0.2, "Download completed")
                return buffer
    except asyncio.TimeoutError:
        await status.update("failed", 0.0, "Download timed out", "Timeout")
        return None
    except Exception as e:
        await status.update("failed", 0.0, f"Download failed: {str(e)}", str(e))
        return None

async def extract_zip(
    zip_buffer: io.BytesIO, 
    extract_path: str, 
    status: ProcessingStatus
) -> bool:
    """
    Extract a ZIP file to the specified path with resource conservation.
    
    Args:
        zip_buffer: BytesIO containing ZIP file data
        extract_path: Path to extract files to
        status: Status tracker to update progress
        
    Returns:
        True if extraction succeeded, False otherwise
    """
    try:
        await status.update("extracting", 0.2, "Extracting ZIP archive")
        
        # Ensure extract path exists
        os.makedirs(extract_path, exist_ok=True)
        
        # Extract the zip file, doing light processing to avoid memory issues
        with zipfile.ZipFile(zip_buffer) as zip_ref:
            total_files = len(zip_ref.namelist())
            for i, file in enumerate(zip_ref.namelist()):
                # Extract specific files only (we only need ratings, movies, links)
                file_lower = file.lower()
                if ('ratings' in file_lower or 
                    'movies' in file_lower or 
                    'links' in file_lower) and file_lower.endswith('.csv'):
                    zip_ref.extract(file, extract_path)
                
                # Update progress periodically
                if i % 10 == 0 or i == total_files - 1:
                    progress = 0.2 + (i / total_files) * 0.1  # 20-30% progress
                    await status.update(
                        "extracting", 
                        progress, 
                        f"Extracting: {i+1} / {total_files} files"
                    )
                
                # Free tier-friendly processing - add small pause
                if i % 100 == 0:
                    await asyncio.sleep(0.1)
        
        await status.update("extracted", 0.3, "ZIP extraction completed")
        return True
    except zipfile.BadZipFile:
        await status.update(
            "failed", 
            0.0, 
            "Failed to extract: Invalid ZIP file", 
            "BadZipFile"
        )
        return False
    except Exception as e:
        await status.update(
            "failed", 
            0.0, 
            f"Failed to extract: {str(e)}", 
            str(e)
        )
        return False

@resource_intensive_task
async def process_movielens_data(
    extract_path: str,
    output_path: str, 
    status: ProcessingStatus,
    sample_ratio: float = None
) -> bool:
    """
    Process the MovieLens dataset with resource-conscious processing.
    
    Args:
        extract_path: Path containing extracted MovieLens files
        output_path: Path to store processed data
        status: Status tracker to update progress
        sample_ratio: Ratio to sample data (0.0-1.0)
        
    Returns:
        True if processing succeeded, False otherwise
    """
    if sample_ratio is None:
        sample_ratio = settings.SAMPLE_RATIO
        
    try:
        await status.update("processing", 0.3, "Processing MovieLens data")
        
        # Ensure output path exists
        os.makedirs(output_path, exist_ok=True)
        
        # Find the right files
        ratings_file = None
        movies_file = None
        links_file = None
        
        # Find the extracted directory containing the files
        extracted_dir = extract_path
        for root, dirs, files in os.walk(extract_path):
            for file in files:
                if 'rating' in file.lower() and file.endswith('.csv'):
                    ratings_file = os.path.join(root, file)
                elif 'movie' in file.lower() and file.endswith('.csv'):
                    movies_file = os.path.join(root, file)
                elif 'link' in file.lower() and file.endswith('.csv'):
                    links_file = os.path.join(root, file)
        
        if not ratings_file or not movies_file:
            await status.update(
                "failed", 
                0.0, 
                "Required files not found in ZIP", 
                "Missing Files"
            )
            return False
        
        # Load data using pandas, with resource-friendly chunking
        await status.update("processing", 0.35, "Loading ratings data")
        ratings_chunks = pd.read_csv(ratings_file, chunksize=settings.DATA_PROCESSING_CHUNK_SIZE)
        
        # Process in smaller chunks
        all_ratings = []
        for i, chunk in enumerate(ratings_chunks):
            # Sample the data if requested
            if sample_ratio < 1.0:
                chunk = chunk.sample(frac=sample_ratio)
            
            all_ratings.append(chunk)
            
            # Update progress and sleep periodically
            if i % 5 == 0:
                progress = 0.35 + (i / 20) * 0.1  # Assume ~20 chunks, 35-45% progress
                await status.update("processing", progress, f"Processing ratings chunk {i+1}")
                await asyncio.sleep(0.1)
        
        # Combine chunks
        ratings_df = pd.concat(all_ratings, ignore_index=True)
        
        # Load movies
        await status.update("processing", 0.45, "Loading movies data")
        movies_df = pd.read_csv(movies_file)
        
        # Load links if available
        links_df = None
        if links_file:
            await status.update("processing", 0.5, "Loading links data")
            links_df = pd.read_csv(links_file)
        
        # Process the data - create content items JSON
        await status.update("processing", 0.55, "Creating content items")
        
        # Create content items
        content_items = []
        
        # Process movies in chunks
        movies_list = movies_df.to_dict('records')
        chunk_size = min(1000, len(movies_list))
        
        # Track movie stats
        num_movies = 0
        genre_counts = {}
        
        # Process in chunks to save memory
        for start_idx in range(0, len(movies_list), chunk_size):
            end_idx = min(start_idx + chunk_size, len(movies_list))
            chunk = movies_list[start_idx:end_idx]
            
            for movie in chunk:
                # Skip if we've reached max content items to keep
                if num_movies >= settings.MAX_CONTENT_ITEMS:
                    break
                    
                movie_id = str(movie['movieId'])
                
                # Extract year from title if present
                title = movie['title']
                year = None
                if title.endswith(')') and '(' in title:
                    year_str = title.split('(')[-1].rstrip(')')
                    try:
                        if year_str.isdigit():
                            year = int(year_str)
                    except:
                        pass
                
                # Process genres
                genres = []
                if isinstance(movie['genres'], str) and movie['genres'] != '(no genres listed)':
                    genres = movie['genres'].split('|')
                    # Update genre counts
                    for genre in genres:
                        genre_counts[genre] = genre_counts.get(genre, 0) + 1
                
                # Get external IDs if available
                external_ids = {}
                if links_df is not None:
                    link_row = links_df[links_df['movieId'] == int(movie_id)]
                    if not link_row.empty:
                        if 'imdbId' in link_row.columns:
                            imdb_id = link_row.iloc[0]['imdbId']
                            if not pd.isna(imdb_id):
                                external_ids['imdb_id'] = f"tt{imdb_id:07d}" if isinstance(imdb_id, int) else str(imdb_id)
                        
                        if 'tmdbId' in link_row.columns:
                            tmdb_id = link_row.iloc[0]['tmdbId']
                            if not pd.isna(tmdb_id):
                                external_ids['tmdb_id'] = str(int(tmdb_id)) if isinstance(tmdb_id, (int, float)) else str(tmdb_id)
                
                # Create content item
                content_item = {
                    'content_id': movie_id,
                    'title': title,
                    'year': year,
                    'genres': genres,
                    'type': 'movie',
                    'external_ids': external_ids
                }
                
                content_items.append(content_item)
                num_movies += 1
            
            # Update progress
            progress = 0.55 + (end_idx / len(movies_list)) * 0.15  # 55-70% progress
            await status.update(
                "processing", 
                progress, 
                f"Processed {end_idx}/{len(movies_list)} movies"
            )
            
            # Free tier friendly - add small pause
            await asyncio.sleep(0.1)
        
        # Save content items
        content_items_path = os.path.join(output_path, 'content_items.json')
        with open(content_items_path, 'w') as f:
            json.dump(content_items, f)
        
        # Process interactions - convert ratings to interactions
        await status.update("processing", 0.7, "Processing interactions")
        
        # Sample users to reduce dataset size if needed
        if settings.FREE_TIER_MODE and len(ratings_df['userId'].unique()) > 500:
            # Limit to 500 users on free tier
            user_sample_size = 500
            user_ids = ratings_df['userId'].unique()
            sampled_user_ids = pd.Series(user_ids).sample(n=min(user_sample_size, len(user_ids))).tolist()
            ratings_df = ratings_df[ratings_df['userId'].isin(sampled_user_ids)]
        
        # Track user stats
        num_users = len(ratings_df['userId'].unique())
        num_ratings = len(ratings_df)
        
        # Convert ratings to interactions and save in chunks
        interactions = []
        
        # Process ratings in chunks
        ratings_list = ratings_df.to_dict('records')
        chunk_size = min(5000, len(ratings_list))
        
        for start_idx in range(0, len(ratings_list), chunk_size):
            end_idx = min(start_idx + chunk_size, len(ratings_list))
            chunk = ratings_list[start_idx:end_idx]
            
            chunk_interactions = []
            for rating in chunk:
                interaction = {
                    'user_id': str(rating['userId']),
                    'content_id': str(rating['movieId']),
                    'interaction_type': 'rating',
                    'value': float(rating['rating']),
                    'timestamp': int(rating['timestamp'])
                }
                chunk_interactions.append(interaction)
            
            # Add to full list
            interactions.extend(chunk_interactions)
            
            # Update progress
            progress = 0.7 + (end_idx / len(ratings_list)) * 0.25  # 70-95% progress
            await status.update(
                "processing", 
                progress, 
                f"Processed {end_idx}/{len(ratings_list)} interactions"
            )
            
            # Free tier friendly - add small pause
            await asyncio.sleep(0.2)
        
        # Save interactions
        interactions_path = os.path.join(output_path, 'interactions.json')
        with open(interactions_path, 'w') as f:
            json.dump(interactions, f)
        
        # Save dataset metadata
        metadata = {
            'name': 'movielens-small' if 'small' in extract_path else 'movielens-full',
            'processed_date': datetime.now().isoformat(),
            'num_users': num_users,
            'num_movies': num_movies,
            'num_interactions': num_ratings,
            'genres': list(genre_counts.keys()),
            'sample_ratio': sample_ratio
        }
        
        metadata_path = os.path.join(output_path, 'metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)
        
        await status.update("completed", 1.0, "Processing completed")
        return True
    except Exception as e:
        await status.update(
            "failed", 
            0.0, 
            f"Processing failed: {str(e)}", 
            str(e)
        )
        return False

async def download_and_process_movielens(
    dataset_type: str = "small",
    output_dir: str = None,
    job_id: str = None,
    force: bool = False
) -> Dict[str, Any]:
    """
    Main function to download and process the MovieLens dataset.
    
    Args:
        dataset_type: "small" or "full"
        output_dir: Directory to output processed data
        job_id: Unique ID for this processing job
        force: Whether to force processing even if already exists
        
    Returns:
        Dictionary with processing status
    """
    # Validate dataset type
    if dataset_type not in MOVIELENS_URLS:
        return {
            "success": False,
            "message": f"Invalid dataset type: {dataset_type}. Valid options: {', '.join(MOVIELENS_URLS.keys())}",
            "job_id": job_id
        }
    
    # Generate job ID if not provided
    if job_id is None:
        job_id = f"movielens_{dataset_type}_{int(time.time())}"
    
    # Set up paths
    if output_dir is None:
        if hasattr(settings, 'CONTENT_PATH'):
            output_dir = os.path.join(settings.CONTENT_PATH, f"movielens-{dataset_type}")
        else:
            output_dir = os.path.join("data", "processed", f"movielens-{dataset_type}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if already processed
    metadata_path = os.path.join(output_dir, 'metadata.json')
    content_path = os.path.join(output_dir, 'content_items.json')
    interactions_path = os.path.join(output_dir, 'interactions.json')
    
    if not force and os.path.exists(metadata_path) and os.path.exists(content_path) and os.path.exists(interactions_path):
        return {
            "success": True,
            "message": f"Dataset movielens-{dataset_type} already processed",
            "job_id": job_id,
            "path": output_dir
        }
    
    # Create temp directory for extraction
    temp_dir = os.path.join("data", "raw", f"movielens-{dataset_type}")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Initialize status tracker
    status = ProcessingStatus(job_id)
    
    try:
        # Step 1: Download the dataset
        url = MOVIELENS_URLS[dataset_type]
        zip_data = await download_file(url, status)
        if zip_data is None:
            return {
                "success": False,
                "message": "Failed to download dataset",
                "job_id": job_id
            }
        
        # Step 2: Extract the dataset
        success = await extract_zip(zip_data, temp_dir, status)
        if not success:
            return {
                "success": False,
                "message": "Failed to extract dataset",
                "job_id": job_id
            }
        
        # Step 3: Process the dataset
        success = await process_movielens_data(
            temp_dir, 
            output_dir, 
            status, 
            sample_ratio=settings.SAMPLE_RATIO
        )
        if not success:
            return {
                "success": False,
                "message": "Failed to process dataset",
                "job_id": job_id
            }
        
        return {
            "success": True,
            "message": f"Successfully processed movielens-{dataset_type} dataset",
            "job_id": job_id,
            "path": output_dir
        }
    except Exception as e:
        logger.error(f"Error in download_and_process_movielens: {str(e)}")
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "job_id": job_id,
            "error": str(e)
        }

async def get_dataset_status(job_id: str) -> Dict[str, Any]:
    """
    Get the status of a dataset processing job.
    
    Args:
        job_id: Job ID to check
        
    Returns:
        Dictionary with status information
    """
    # In a real implementation, you would retrieve this from Redis or a database
    # For this example, we'll simulate it
    
    # Here you would typically query your database to get the actual status
    
    return {
        "status": "running",  # Or "completed", "failed"
        "message": "Processing dataset",
        "job_id": job_id,
        "progress": 0.5  # 0.0 to 1.0
    } 