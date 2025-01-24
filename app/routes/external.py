from fastapi import APIRouter, HTTPException, Response
from fastapi.param_functions import Query
from fastapi.middleware.cors import CORSMiddleware
import requests
from app.core.config import settings
from redis import asyncio as aioredis
import logging
import json

router = APIRouter(prefix="/external", tags=["external"])
logger = logging.getLogger(__name__)

# Initialize Redis client
redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

WIKI_API_URL = "https://en.wikipedia.org/w/api.php"

@router.get("/wikipedia")
async def get_wikipedia_content(
    search: str = Query(..., min_length=3),
    limit: int = 5,
    response: Response = None
):
    # Add CORS headers
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    
    cache_key = f"wiki:{search}"
    try:
        # Check cache first
        cached = await redis_client.get(cache_key)
        if cached:
            logger.info(f"Returning cached Wikipedia results for '{search}'")
            return {"source": "wikipedia", "results": json.loads(cached)}
        
        params = {
            "action": "query",
            "list": "search",
            "srsearch": search,
            "format": "json",
            "utf8": 1,
            "srlimit": limit
        }
        
        response = requests.get(WIKI_API_URL, params=params)
        response.raise_for_status()
        
        data = response.json()
        results = [
            {
                "title": item["title"],
                "snippet": item["snippet"],
                "pageid": item["pageid"],
                "url": f"https://en.wikipedia.org/?curid={item['pageid']}"
            } for item in data.get("query", {}).get("search", [])
        ]
        
        # Cache for 1 hour (3600 seconds)
        await redis_client.setex(cache_key, 3600, json.dumps(results))
        
        return {"source": "wikipedia", "results": results}
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Wikipedia API error: {str(e)}")
        raise HTTPException(
            status_code=502,
            detail="Wikipedia API is currently unavailable"
        )
    except Exception as e:
        logger.error(f"Wikipedia processing error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process Wikipedia results"
        )