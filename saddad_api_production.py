
"""
SADDAD V7 - Time Bank Production API - Linked to Supabase
Points system, not JOD for professions
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os, math, datetime

try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except:
    SUPABASE_AVAILABLE = False
    create_client = None

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://zimcldfenvycjqdcytogk.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_bOR1FqYJUQpe4QzOMpsckA_ziuH11sd")

supabase = None
if SUPABASE_AVAILABLE:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Supabase init fail: {e}")

app = FastAPI(title="SADDAD V7 Time Bank API", version="7.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---
class PointsRequest(BaseModel):
    user_phone: str
    profession_id: str
    cost_points: int

class PointsEarn(BaseModel):
    user_phone: str
    profession_id: str
    earn_points: int

class UserCreate(BaseModel):
    phone: str
    name: str
    skill: Optional[str] = None
    lat: float = 31.9545
    lng: float = 35.9110

MOCK_PROFS = [
    {"id":"ELEC_001","name_ar":"كهربائي منازل","name_en":"House Electrician","class":"A","points":8,"icon":"⚡","avg_time_min":60},
    {"id":"PLUM_001","name_ar":"سباك","name_en":"Plumber","class":"A","points":6,"icon":"🔧","avg_time_min":45},
    {"id":"CARP_001","name_ar":"نجار","name_en":"Carpenter","class":"B","points":9,"icon":"🪚","avg_time_min":90},
    {"id":"PAINT_001","name_ar":"دهان","name_en":"Painter","class":"B","points":5,"icon":"🎨","avg_time_min":120},
    {"id":"AC_001","name_ar":"فني تكييف","name_en":"AC Technician","class":"A","points":10,"icon":"❄️","avg_time_min":60},
    {"id":"TILE_001","name_ar":"بليط","name_en":"Tiler","class":"C","points":7,"icon":"🧱","avg_time_min":180},
    {"id":"WELD_001","name_ar":"حداد","name_en":"Welder","class":"C","points":12,"icon":"🔨","avg_time_min":60},
    {"id":"TEACH_001","name_ar":"معلم خصوصي","name_en":"Tutor","class":"D","points":7,"icon":"📚","avg_time_min":60},
    {"id":"DELIV_001","name_ar":"توصيل طلبات","name_en":"Delivery","class":"G","points":3,"icon":"🛵","avg_time_min":30},
    {"id":"BILL_ELEC","name_ar":"دفع فاتورة كهرباء (من الصندوق)","name_en":"Pay Electricity Bill","class":"F","points":15,"icon":"💡","avg_time_min":5},
]
for i in range(10, 85):
    MOCK_PROFS.append({"id":f"PROF_{i:03d}","name_ar":f"مهنة {i}","name_en":f"Profession {i}","class":chr(65+i%7),"points":3+i%13,"icon":"🛠️","avg_time_min":30+i%120})

@app.get("/")
def root():
    return {"message":"SADDAD V7 Time Bank Live ✅","version":"7.0","points_system":"1 point = 1 JOD value inside app","supabase_connected": supabase is not None,"docs":"/docs"}

@app.get("/api/stats")
def stats():
    if not supabase:
        return {"professions":85,"users":5,"points_ledger": 1240,"fund_total_jod":3102663,"fund_level_percent":68,"status":"mock"}
    try:
        profs = supabase.table("professions").select("id", count="exact").execute()
        users = supabase.table("users").select("id", count="exact").execute()
        # Try points_ledger if exists
        try:
            ledger = supabase.table("points_ledger").select("id", count="exact").execute()
            ledger_count = ledger.count
        except:
            ledger_count = 0
        return {"professions": profs.count or 85,"users": users.count or 5,"points_ledger": ledger_count,"fund_total_jod":3102663,"fund_level_percent":68,"status":"live"}
    except Exception as e:
        return {"professions":85,"users":5,"points_ledger":0,"fund_total_jod":3102663,"fund_level_percent":68,"status":"fallback","error":str(e)}

@app.get("/api/professions")
def list_profs(class_filter: Optional[str]=None, search: Optional[str]=None):
    if supabase:
        try:
            q = supabase.table("professions").select("*")
            if class_filter:
                q = q.eq("class", class_filter)
            res = q.order("id").execute()
            data = res.data
            # Add points field if missing
            for p in data:
                if "points" not in p:
                    p["points"] = p.get("avg_wage_jod", 5)  # migrate old field
            if search and data:
                sl = search.lower()
                data = [p for p in data if sl in p.get("name_ar","").lower() or sl in p.get("name_en","").lower()]
            if data:
                return {"total":len(data),"professions":data,"source":"supabase","currency":"points"}
        except Exception as e:
            print(f"prof error {e}")
    # Fallback
    data = MOCK_PROFS
    if class_filter:
        data = [p for p in data if p["class"]==class_filter]
    if search:
        sl = search.lower()
        data = [p for p in data if sl in p.get("name_ar","").lower() or sl in p.get("name_en","").lower()]
    return {"total":len(data),"professions":data,"source":"mock","currency":"points"}

@app.get("/api/community")
def community():
    # Mock community near Amman - later from users table
    users = [
        {"phone":"0790000001","name":"أحمد الكهربجي","skill":"كهربائي منازل","points":24,"trust":92,"distance_km":1.2,"available":True,"icon":"⚡"},
        {"phone":"0790000002","name":"سارة معلمة","skill":"معلمة انجليزي","points":18,"trust":88,"distance_km":0.8,"available":True,"icon":"📚"},
        {"phone":"0790000003","name":"محمد النجار","skill":"نجار","points":31,"trust":95,"distance_km":2.1,"available":False,"icon":"🪚"},
        {"phone":"0790000004","name":"خالد السباك","skill":"سباك","points":12,"trust":85,"distance_km":0.5,"available":True,"icon":"🔧"},
    ]
    return {"total":len(users),"users":users}

@app.get("/api/points/balance/{phone}")
def get_balance(phone: str):
    if supabase:
        try:
            # Try ledger
            res = supabase.table("points_ledger").select("*").eq("user_phone", phone).order("created_at", desc=True).limit(1).execute()
            if res.data:
                return {"phone":phone,"balance_points":res.data[0]["balance"],"monthly_consumption":res.data[0].get("monthly_consumption",0),"cap":res.data[0].get("cap",15),"source":"supabase"}
        except:
            pass
    # Mock balance
    return {"phone":phone,"balance_points":12,"monthly_consumption":7,"cap":15,"monthly_cap_percent":47,"debt_points":0,"source":"mock"}

@app.post("/api/points/request")
def request_service(req: PointsRequest):
    # Core Time Bank Algorithm
    bal = get_balance(req.user_phone)
    balance = bal["balance_points"]
    consumption = bal["monthly_consumption"]
    cap = bal["cap"]
    
    result = {}
    if balance >= req.cost_points:
        result = {"status":"paid_from_balance","message":f"دفعت {req.cost_points} نقاط من رصيدك","new_balance":balance-req.cost_points,"new_consumption":consumption+req.cost_points,"fund_used":0}
    elif consumption + req.cost_points <= cap:
        debt = req.cost_points - balance
        result = {"status":"covered_by_fund","message":f"الصندوق غطاك! دين {debt} نقطة عليك - لازم تقدم خدمة","new_balance":0,"new_consumption":consumption+req.cost_points,"fund_used":debt,"debt":debt}
    else:
        result = {"status":"blocked","message":"رصيدك والسقف الشهري خلصوا - لازم تقدم خدمة أول","new_balance":balance,"new_consumption":consumption,"fund_used":0}
    
    # Log to supabase if possible
    if supabase:
        try:
            supabase.table("points_ledger").insert({
                "user_phone": req.user_phone,
                "profession_id": req.profession_id,
                "type": "request",
                "points": -req.cost_points,
                "balance": result.get("new_balance", balance),
                "monthly_consumption": result.get("new_consumption", consumption),
                "status": result["status"]
            }).execute()
        except Exception as e:
            print(f"ledger insert fail {e}")
    
    return result

@app.post("/api/points/earn")
def earn_service(req: PointsEarn):
    bal = get_balance(req.user_phone)
    new_balance = bal["balance_points"] + req.earn_points
    result = {"status":"earned","message":f"كسبت {req.earn_points} نقاط!","new_balance":new_balance,"earned":req.earn_points}
    if supabase:
        try:
            supabase.table("points_ledger").insert({
                "user_phone": req.user_phone,
                "profession_id": req.profession_id,
                "type": "earn",
                "points": req.earn_points,
                "balance": new_balance,
                "status":"earned"
            }).execute()
        except Exception as e:
            print(f"earn log fail {e}")
    return result

@app.get("/api/fund")
def fund():
    return {
        "total_subscribers":1034221,
        "total_jod":3102663,
        "breakdown":{"services_60":1861597,"reserve_20":620532,"profit_20":620532},
        "level_percent":68,
        "current_cap_points":15,
        "status":"مستقر",
        "last_20_ops":[
            {"type":"request","points":8,"time":"قبل دقيقتين"},
            {"type":"earn","points":6,"time":"قبل 5 دقائق"},
            {"type":"covered_by_fund","points":4,"time":"قبل 7 دقائق"},
        ]
    }

@app.get("/api/health")
def health():
    return {"status":"ok","version":"7.0-TimeBank","supabase": supabase is not None,"points_system":"active"}
