from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging
import os
import json
from ..core.auth import get_current_user
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.content import ContentItem, ContentItemDB
from ..models.interaction import InteractionCreate, InteractionDB
from ..services.interaction_counter import increment_interaction_counter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/content", tags=["content"])

# Path to content data
CONTENT_PATH = os.environ.get("CONTENT_PATH", "data/processed/movielens-small")

# Models for responses
class MovieResponse(BaseModel):
    content_id: str
    title: str
    description: Optional[str] = None
    genres: List[str] = []
    year: Optional[int] = None
    
    class Config:
        from_attributes = True

class MovieInteractionRequest(BaseModel):
    content_id: str
    interaction_type: str = "rating"  # rating, like, view, etc.
    value: float  # For ratings: 1-5
    metadata: Optional[Dict[str, Any]] = None

class MovieInteractionResponse(BaseModel):
    id: int
    user_id: str
    content_id: str
    interaction_type: str
    value: float
    timestamp: str
    status: str = "success"

# Load content from file
def get_content_items():
    try:
        content_path = os.path.join(CONTENT_PATH, 'content_items.json')
        if not os.path.exists(content_path):
            # Try sample path
            content_path = os.path.join(CONTENT_PATH, 'sample', 'content_items.json')
        
        with open(content_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading content items: {str(e)}")
        return []

@router.get("/movies", response_model=List[MovieResponse])
async def get_movies(
    skip: int = 0, 
    limit: int = 20, 
    genre: Optional[str] = None,
    year: Optional[int] = None,
    search: Optional[str] = None,
    user = Depends(get_current_user)
):
    """Get a list of movies with pagination and filtering"""
    try:
        # Load all content items
        content_items = get_content_items()
        
        # Apply filters
        filtered_items = []
        for item in content_items:
            if item.get("content_type") != "movie":
                continue
                
            # Apply genre filter
            if genre and genre not in item.get("metadata", {}).get("genres", []):
                continue
                
            # Apply year filter
            if year and item.get("metadata", {}).get("year") != year:
                continue
                
            # Apply search filter
            if search and search.lower() not in item.get("title", "").lower():
                continue
                
            filtered_items.append(item)
        
        # Apply pagination
        paginated_items = filtered_items[skip:skip+limit]
        
        # Format response
        result = []
        for item in paginated_items:
            result.append(MovieResponse(
                content_id=item["content_id"],
                title=item["title"],
                description=item.get("description", ""),
                genres=item.get("metadata", {}).get("genres", []),
                year=item.get("metadata", {}).get("year")
            ))
        
        return result
    except Exception as e:
        logger.error(f"Error retrieving movies: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve movies: {str(e)}"
        )

@router.get("/movies/{content_id}", response_model=MovieResponse)
async def get_movie_by_id(
    content_id: str,
    user = Depends(get_current_user)
):
    """Get a specific movie by its ID"""
    try:
        # Load all content items
        content_items = get_content_items()
        
        # Find the specific movie
        for item in content_items:
            if item.get("content_id") == content_id:
                return MovieResponse(
                    content_id=item["content_id"],
                    title=item["title"],
                    description=item.get("description", ""),
                    genres=item.get("metadata", {}).get("genres", []),
                    year=item.get("metadata", {}).get("year")
                )
        
        # Movie not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movie with ID {content_id} not found"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving movie {content_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve movie: {str(e)}"
        )

@router.post("/interact", response_model=MovieInteractionResponse)
async def create_interaction(
    interaction: MovieInteractionRequest,
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new interaction with a movie (rating, like, etc.)"""
    try:
        # Validate content exists
        content_items = get_content_items()
        content_exists = False
        
        for item in content_items:
            if item.get("content_id") == interaction.content_id:
                content_exists = True
                break
                
        if not content_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Content with ID {interaction.content_id} not found"
            )
            
        # Create interaction in database
        interaction_create = InteractionCreate(
            user_id=user.id,
            content_id=interaction.content_id,
            interaction_type=interaction.interaction_type,
            value=interaction.value,
            metadata=interaction.metadata or {}
        )
        
        db_interaction = InteractionDB(
            user_id=interaction_create.user_id,
            content_id=interaction_create.content_id,
            interaction_type=interaction_create.interaction_type,
            value=interaction_create.value,
            interaction_metadata=interaction_create.metadata
        )
        
        db.add(db_interaction)
        db.commit()
        db.refresh(db_interaction)
        
        # Increment the interaction counter for model retraining
        await increment_interaction_counter()
        
        # Format response
        return MovieInteractionResponse(
            id=db_interaction.id,
            user_id=db_interaction.user_id,
            content_id=db_interaction.content_id,
            interaction_type=db_interaction.interaction_type,
            value=float(db_interaction.value),
            timestamp=db_interaction.timestamp.isoformat(),
            status="success"
        )
    except HTTPException:
        raise
    except Exception as e:
        if db:
            db.rollback()
        logger.error(f"Error creating interaction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create interaction: {str(e)}"
        )

@router.get("/genres", response_model=List[str])
async def get_genres(
    user = Depends(get_current_user)
):
    """Get a list of all available genres"""
    try:
        # Load all content items
        content_items = get_content_items()
        
        # Extract all genres
        all_genres = set()
        for item in content_items:
            if item.get("content_type") == "movie":
                genres = item.get("metadata", {}).get("genres", [])
                all_genres.update(genres)
        
        return sorted(list(all_genres))
    except Exception as e:
        logger.error(f"Error retrieving genres: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve genres: {str(e)}"
        )

@router.get("/years", response_model=List[int])
async def get_years(
    user = Depends(get_current_user)
):
    """Get a list of all available movie years"""
    try:
        # Load all content items
        content_items = get_content_items()
        
        # Extract all years
        all_years = set()
        for item in content_items:
            if item.get("content_type") == "movie":
                year = item.get("metadata", {}).get("year")
                if year:
                    all_years.add(year)
        
        return sorted(list(all_years))
    except Exception as e:
        logger.error(f"Error retrieving years: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve years: {str(e)}"
        )

@router.get("/refresh", response_model=MovieResponse)
async def refresh_dataset(
    user = Depends(get_current_user)
):
    """Refresh the content dataset if it's missing"""
    try:
        # Check if content items exist
        content_items = get_content_items()
        
        if not content_items:
            # Dataset is missing or empty, try to download it
            logger.info("Content dataset missing, downloading MovieLens dataset...")
            
            # Run the data processor script
            import os
            import subprocess
            import sys
            from pathlib import Path
            
            # Create directories if they don't exist
            os.makedirs("data/raw", exist_ok=True)
            os.makedirs("data/processed", exist_ok=True)
            
            # Run data_processor.py script
            script_path = str(Path(__file__).parent.parent.parent / "scripts" / "data_processor.py")
            
            try:
                subprocess.run([
                    sys.executable,
                    script_path,
                    "--dataset", "movielens-small",
                    "--raw-dir", "data/raw",
                    "--processed-dir", "data/processed"
                ], check=True)
                
                # Reload content items
                content_items = get_content_items()
                
                if content_items:
                    return MovieResponse(
                        content_id="refresh_success",
                        title="Dataset Refreshed",
                        description="The MovieLens dataset has been successfully downloaded and processed.",
                        genres=["refresh", "success"],
                        year=2025
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Downloaded dataset but content items are still missing"
                    )
            except subprocess.CalledProcessError as e:
                logger.error(f"Error running data processor: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to download dataset: {str(e)}"
                )
        
        # Dataset exists
        return MovieResponse(
            content_id="dataset_exists",
            title="Dataset Ready",
            description=f"The dataset is already available with {len(content_items)} content items.",
            genres=["ready"],
            year=2025
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing dataset: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh dataset: {str(e)}"
        ) 