
"""
SADDAD V6.3 - Production API - Fixed Version
Connected to: https://zimcldfenvycjqdcytogk.supabase.co
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import math
import os

# Try supabase import with fallback
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    create_client = None

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://zimcldfenvycjqdcytogk.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_bOR1FqYJUQpe4QzOMpsckA_ziuH11sd")

if SUPABASE_AVAILABLE:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Supabase init failed: {e}")
        supabase = None
else:
    supabase = None

app = FastAPI(title="SADDAD V6.3 API", version="6.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2-lat1)
    dlon = math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return R*2*math.asin(math.sqrt(a))

class ServiceRequestIn(BaseModel):
    requester_phone: str
    requester_lat: float = 31.9545
    requester_lng: float = 35.9110
    profession_id: str
    estimated_hours: float = 2.0
    description: Optional[str] = None

@app.get("/")
def root():
    return {
        "message": "SADDAD V6.3 API Live ✅",
        "project": "zimcldfenvycjqdcytogk",
        "supabase_connected": supabase is not None,
        "docs": "/docs"
    }

@app.get("/api/stats")
def stats():
    if not supabase:
        return {"error": "supabase not connected", "professions": 85, "users": 5, "mock": True}
    try:
        profs = supabase.table("professions").select("id", count="exact").execute()
        users = supabase.table("users").select("id", count="exact").execute()
        patterns = supabase.table("complaint_patterns").select("id", count="exact").execute()
        return {
            "professions": profs.count,
            "users": users.count,
            "complaint_patterns": patterns.count,
            "status": "live",
            "url": SUPABASE_URL
        }
    except Exception as e:
        return {"error": str(e), "professions": 85, "fallback": True}

@app.get("/api/professions")
def list_professions(class_filter: Optional[str] = None):
    if not supabase:
        raise HTTPException(500, "DB not connected")
    q = supabase.table("professions").select("*")
    if class_filter:
        q = q.eq("class", class_filter)
    data = q.order("id").execute()
    return {"total": len(data.data), "professions": data.data}

@app.get("/api/health")
def health():
    return {"status": "ok", "supabase": supabase is not None}
