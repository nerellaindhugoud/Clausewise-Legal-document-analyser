from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect 
from fastapi.middleware.cors import CORSMiddleware 
from fastapi.staticfiles import StaticFiles 
from typing import Optional 
import asyncio

from backend.utils import ( 
    extract_clauses, classify_contract, summarize_extract, keyword_qa, find_entities_regex, detect_risks, upcoming_alerts, detect_language, compare_contracts 
    )
from backend.collab_manager import COLLAB
from backend.ibm_clients import IBMProviders

app = FastAPI(title="ClauseWise  IBM Watson/Granite (No HF/Torch)")

app.add_middleware( 
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"], )

#You can mount static assets if you add an HTML collab page

app.mount("/static", 
          StaticFiles(directory="frontend"), 
          name="static"
         )

#---- Helpers that use IBM Granite when available ----

def summarise(text: str) -> str: 
    g = IBMProviders.wx_generate( 
        system_prompt="You are a legal assistant. Summarize the contract in 5-7 bullet points in the same language as the input.", 
        user_prompt=text[:12000] 
    ) 
    return g or summarize_extract(text, max_sentences=6)

def simplify_clause(clause: str) -> str: 
    g = IBMProviders.wx_generate(
         system_prompt="Rewrite the clause in simpler, layman-friendly language while preserving legal meaning.", 
         user_prompt=clause[:4000] 
    ) 
    return g or clause

def answer_llm(context: str, question: str) -> str: 
    g = IBMProviders.wx_generate( 
        system_prompt="Answer strictly using the provided contract text. If unknown, say 'Not found in document.'", 
        user_prompt=f"Contract:\n{context[:10000]}\n\nQuestion: {question}" 
    ) 
    return g or keyword_qa(context, question)

@app.post("/analyze") 
async def analyze(file: UploadFile = File(...)): 
    text = (await file.read()).decode("utf-8", errors="ignore") 
    lang = detect_language(text) 
    clauses = extract_clauses(text) 
    contract_type = classify_contract(text) 
    summary = summarise(text) # Entities: try IBM NLU first, fallback to regex 
    
    nlu = IBMProviders.nlu_entities(text) 
    
    entities = nlu.get("entities") if nlu else None 
    
    entities_out = nlu if nlu else find_entities_regex(text) 
    risks = detect_risks(text) 
    alerts = upcoming_alerts(text) # Simplify top clauses 
    
    simplified = [simplify_clause(c) for c in clauses[:5]] 
    return {
         "language": lang, 
         "contract_type": contract_type, 
         "clauses": clauses, 
         "simplified_examples": simplified, 
         "summary": summary, 
         "entities": entities_out, 
         "risks": risks, 
         "alerts": alerts, 
         "uses_granite": IBMProviders.wx_ready(), 
         "uses_watson_nlu": IBMProviders.nlu_ready(), 
         }

@app.post("/ask") 
async def ask(file: UploadFile = File(...), question: str = Form(...)): 
    text = (await file.read()).decode("utf-8", errors="ignore") 
    ans = answer_llm(text, question) 
    return {"answer": ans}

@app.post("/compare") 
async def compare(file_a: UploadFile = File(...), file_b: UploadFile = File(...)):
     a = (await file_a.read()).decode("utf-8", errors="ignore") 
     b = (await file_b.read()).decode("utf-8", errors="ignore") 
     result = compare_contracts(a, b) 
     return result

#-------- Real-time Collaboration via WebSockets --------

@app.websocket("/ws/{room_id}")
async def ws_endpoint(ws: WebSocket, room_id: str): 
    await ws.accept() 
    await COLLAB.join(room_id, ws) 
    try: 
        while True: 
            data = await ws.receive_json()
            mtype = data.get("type") 
            if mtype == "document": 
                await COLLAB.update_document(room_id, data.get("payload", ""))
            elif mtype == "chat": 
                await COLLAB.add_chat(room_id, data.get("user", "anon"), data.get("payload", ""))
    except WebSocketDisconnect: 
        await COLLAB.leave(room_id, ws)

async def alert_broadcaster(): 
    while True: 
        for room_id, room in COLLAB.rooms.items(): 
            await COLLAB.broadcast(room_id, {"type": "alert", "payload": {"message": "Smart alert: check upcoming deadlines in 60 days."}}) 
        await asyncio.sleep(30)

@app.on_event("startup") 
async def startup_event(): 
    asyncio.create_task(alert_broadcaster()
    )

