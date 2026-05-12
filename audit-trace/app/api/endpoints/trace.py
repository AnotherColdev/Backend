from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...database import get_db
from ...models import ProcessTrace
from ...schemas import ProcessTraceCreate, TraceChainResponse

router = APIRouter(prefix="/api/v1/audit", tags=["Trazabilidad"])

@router.post("/trace")
def create_trace(trace: ProcessTraceCreate, db: Session = Depends(get_db)):
    db_trace = ProcessTrace(**trace.model_dump())
    db.add(db_trace)
    db.commit()
    db.refresh(db_trace)
    return {"id": db_trace.id, "status": "created"}

@router.get("/trace/{dataset_load_id}", response_model=TraceChainResponse)
def get_trace_chain(dataset_load_id: str, db: Session = Depends(get_db)):
    events = db.query(ProcessTrace).filter(
        ProcessTrace.dataset_load_id == dataset_load_id
    ).order_by(ProcessTrace.created_at).all()
    
    if not events:
        raise HTTPException(status_code=404, detail="No se encontraron eventos")
    
    timeline = {}
    for event in events:
        timeline[event.event_type] = {
            "status": event.status,
            "parameters": event.parameters,
            "result_summary": event.result_summary,
            "timestamp": event.created_at.isoformat()
        }
    
    return TraceChainResponse(dataset_load_id=dataset_load_id, timeline=timeline)