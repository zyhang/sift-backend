"""
Sift Backend - A simple blocklist management API
"""
import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
API_SECRET = os.getenv("API_SECRET")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize FastAPI app
app = FastAPI(
    title="Sift Backend",
    description="Blocklist management API for browser extension",
    version="1.0.0"
)

# CORS configuration - allow all origins for extension access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class ReportRequest(BaseModel):
    user_id: str
    reason: Optional[str] = None


class BlocklistResponse(BaseModel):
    count: int
    users: list[str]


class MessageResponse(BaseModel):
    message: str


# API Endpoints
@app.get("/blocklist", response_model=BlocklistResponse)
async def get_blocklist():
    """
    Get all blocked user IDs from the database.
    Returns a list of user_id strings.
    """
    try:
        response = supabase.table("blocklist").select("user_id").execute()
        users = [row["user_id"] for row in response.data]
        return BlocklistResponse(count=len(users), users=users)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.post("/report", response_model=MessageResponse)
async def report_user(
    request: ReportRequest,
    x_api_key: Optional[str] = Header(None)
):
    """
    Report a user to be added to the blocklist.
    Requires x-api-key header for authentication.
    Uses upsert to avoid duplicates.
    """
    # Validate API key
    if not x_api_key or x_api_key != API_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid API key")
    
    try:
        # Upsert: insert or update if exists (based on user_id)
        supabase.table("blocklist").upsert(
            {"user_id": request.user_id, "reason": request.reason},
            on_conflict="user_id"
        ).execute()
        
        return MessageResponse(message=f"User {request.user_id} reported successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint for deployment verification."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
