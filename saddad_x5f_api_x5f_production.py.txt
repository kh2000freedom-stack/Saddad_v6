
"""
SADDAD V6.3 - Production API
Connected to: https://zimcldfenvycjqdcytogk.supabase.co
FastAPI + Supabase (PostgREST) + Haversine 5km Matching
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import math
import os
from datetime import datetime
from supabase import create_client, Client

# Supabase credentials - NEW PROJECT
SUPABASE_URL = "https://zimcldfenvycjqdcytogk.supabase.co"
SUPABASE_KEY = "sb_publishable_bOR1FqYJUQpe4QzOMpsckA_ziuH11sd"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="SADDAD V6.3 API", version="6.3.0", description="بنك الوقت الأردني - محرك مطابقة 5km")

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
    profession_id: str  # B01, A01 etc
    estimated_hours: float = 2.0
    description: Optional[str] = None

class QRConfirmIn(BaseModel):
    request_id: str
    provider_phone: str
    actual_hours: float
    qr_code: Optional[str] = "QR_MOCK"

class FeedbackIn(BaseModel):
    request_id: str
    rating: int
    complaint_text: Optional[str] = None

@app.get("/")
def root():
    return {"message": "SADDAD V6.3 API Live", "project": "zimcldfenvycjqdcytogk", "status": "connected", "docs": "/docs"}

@app.get("/api/stats")
def stats():
    profs = supabase.table("professions").select("id", count="exact").execute()
    users = supabase.table("users").select("id", count="exact").execute()
    patterns = supabase.table("complaint_patterns").select("id", count="exact").execute()
    wallets = supabase.table("wallets").select("user_id", count="exact").execute()
    return {
        "professions": profs.count,
        "users": users.count,
        "complaint_patterns": patterns.count,
        "wallets": wallets.count,
        "project": "Saddad_v6",
        "url": SUPABASE_URL
    }

@app.get("/api/professions")
def list_professions(class_filter: Optional[str] = None):
    q = supabase.table("professions").select("*")
    if class_filter:
        q = q.eq("class", class_filter)
    data = q.order("id").execute()
    return {"total": len(data.data), "professions": data.data}

@app.get("/api/users")
def list_users():
    data = supabase.table("users").select("*").execute()
    return {"total": len(data.data), "users": data.data}

@app.get("/api/wallets")
def list_wallets():
    data = supabase.table("wallets").select("*").execute()
    return data.data

@app.post("/api/request-service")
def request_service(req: ServiceRequestIn):
    # 1. Get requester
    requester = supabase.table("users").select("*").eq("phone", req.requester_phone).execute()
    if not requester.data:
        raise HTTPException(404, f"Requester phone {req.requester_phone} not found. Use 0790000004 for قادر test")
    
    # 2. Get profession
    prof = supabase.table("professions").select("*").eq("id", req.profession_id).execute()
    if not prof.data:
        raise HTTPException(404, f"Profession {req.profession_id} not found")
    prof_data = prof.data[0]

    # 3. Find providers with this profession within 5km
    # Get all user_professions for this profession
    ups = supabase.table("user_professions").select("user_id").eq("profession_id", req.profession_id).execute()
    provider_ids = [u["user_id"] for u in ups.data]
    
    if not provider_ids:
        raise HTTPException(404, f"No providers for profession {req.profession_id}")
    
    providers = supabase.table("users").select("*").in_("id", provider_ids).execute()
    
    candidates = []
    for p in providers.data:
        if p["lat"] is None or p["lng"] is None:
            continue
        dist = haversine(req.requester_lat, req.requester_lng, p["lat"], p["lng"])
        if dist > 5.0:
            continue
        score = max(0, 40*(1-dist/5)) + (p.get("rating",5)/5*25) + 15 + min(10, p.get("total_services_done",0)/5)
        candidates.append({
            "provider_id": p["id"],
            "provider_name": p["full_name"],
            "phone": p["phone"],
            "lat": p["lat"],
            "lng": p["lng"],
            "distance_km": round(dist,2),
            "rating": p["rating"],
            "match_score": round(score,1),
            "profession": prof_data["name_ar"],
            "multiplier": prof_data["multiplier"],
            "credits_needed": req.estimated_hours * prof_data["multiplier"]
        })
    
    candidates.sort(key=lambda x: x["match_score"], reverse=True)
    
    if not candidates:
        raise HTTPException(404, "لا يوجد مزود ضمن 5km")
    
    # Create service_requests entry
    req_row = {
        "requester_id": requester.data[0]["id"],
        "provider_id": candidates[0]["provider_id"],
        "profession_id": req.profession_id,
        "estimated_hours": req.estimated_hours,
        "status": "matched",
        "lat": req.requester_lat,
        "lng": req.requester_lng,
        "distance_km": candidates[0]["distance_km"]
    }
    inserted = supabase.table("service_requests").insert(req_row).execute()
    
    return {
        "request_id": inserted.data[0]["id"] if inserted.data else "mock_id",
        "profession": prof_data["name_ar"],
        "multiplier": prof_data["multiplier"],
        "candidates_found": len(candidates),
        "best_match": candidates[0],
        "all_candidates": candidates[:5]
    }

@app.post("/api/confirm-qr")
def confirm_qr(data: QRConfirmIn):
    # Find request
    req = supabase.table("service_requests").select("*").eq("id", data.request_id).execute()
    if not req.data:
        raise HTTPException(404, "Request not found")
    
    # Get provider profession multiplier
    prof_id = req.data[0]["profession_id"]
    prof = supabase.table("professions").select("multiplier").eq("id", prof_id).execute()
    multiplier = prof.data[0]["multiplier"] if prof.data else 1.5
    
    credits = data.actual_hours * multiplier
    bill_JOD = credits * 10
    
    # Update request to completed
    supabase.table("service_requests").update({"status": "completed"}).eq("id", data.request_id).execute()
    
    # Update wallets - add to provider
    provider = supabase.table("users").select("id").eq("phone", data.provider_phone).execute()
    if provider.data:
        pid = provider.data[0]["id"]
        wallet = supabase.table("wallets").select("*").eq("user_id", pid).execute()
        if wallet.data:
            new_balance = wallet.data[0]["time_credits_hours"] + credits
            supabase.table("wallets").update({"time_credits_hours": new_balance}).eq("user_id", pid).execute()
    
    return {
        "status": "completed",
        "actual_hours": data.actual_hours,
        "multiplier": multiplier,
        "credits_earned": credits,
        "bill_covered_JOD": bill_JOD,
        "message": f"تم سداد {bill_JOD}د من صندوق الفواتير"
    }

@app.get("/api/complaint-patterns")
def complaint_patterns():
    data = supabase.table("complaint_patterns").select("*").execute()
    return data.data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
