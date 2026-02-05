# app/main.py
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from datetime import datetime

from . import models, schemas
from .database import engine, SessionLocal

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Agentic Workflow Builder API")

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============ WORKFLOW ENDPOINTS ============

@app.post("/workflows/", response_model=schemas.Workflow)
def create_workflow(workflow: schemas.WorkflowCreate, db: Session = Depends(get_db)):
    """Create a new workflow with optional steps"""
    db_workflow = models.Workflow(
        name=workflow.name,
        description=workflow.description
    )
    db.add(db_workflow)
    db.flush()  # Get the ID
    
    # Add steps if provided
    for step_data in workflow.steps:
        db_step = models.Step(
            workflow_id=db_workflow.id,
            **step_data.model_dump()
        )
        db.add(db_step)
    
    db.commit()
    db.refresh(db_workflow)
    return db_workflow


@app.get("/workflows/", response_model=List[schemas.WorkflowSummary])
def list_workflows(db: Session = Depends(get_db)):
    """List all workflows with step counts"""
    workflows = db.query(models.Workflow).all()
    result = []
    for wf in workflows:
        result.append(schemas.WorkflowSummary(
            id=wf.id,
            name=wf.name,
            description=wf.description,
            created_at=wf.created_at,
            step_count=len(wf.steps)
        ))
    return result


@app.get("/workflows/{workflow_id}", response_model=schemas.Workflow)
def get_workflow(workflow_id: int, db: Session = Depends(get_db)):
    """Get a workflow with all its steps"""
    workflow = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@app.put("/workflows/{workflow_id}", response_model=schemas.Workflow)
def update_workflow(workflow_id: int, workflow: schemas.WorkflowUpdate, db: Session = Depends(get_db)):
    """Update workflow metadata"""
    db_workflow = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
    if not db_workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    if workflow.name is not None:
        db_workflow.name = workflow.name
    if workflow.description is not None:
        db_workflow.description = workflow.description
    
    db.commit()
    db.refresh(db_workflow)
    return db_workflow


@app.delete("/workflows/{workflow_id}")
def delete_workflow(workflow_id: int, db: Session = Depends(get_db)):
    """Delete a workflow and all its steps"""
    workflow = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    db.delete(workflow)
    db.commit()
    return {"message": "Workflow deleted"}


# ============ STEP ENDPOINTS ============

@app.post("/workflows/{workflow_id}/steps/", response_model=schemas.Step)
def add_step(workflow_id: int, step: schemas.StepCreate, db: Session = Depends(get_db)):
    """Add a step to a workflow"""
    workflow = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    db_step = models.Step(workflow_id=workflow_id, **step.model_dump())
    db.add(db_step)
    db.commit()
    db.refresh(db_step)
    return db_step


@app.put("/steps/{step_id}", response_model=schemas.Step)
def update_step(step_id: int, step: schemas.StepUpdate, db: Session = Depends(get_db)):
    """Update a step"""
    db_step = db.query(models.Step).filter(models.Step.id == step_id).first()
    if not db_step:
        raise HTTPException(status_code=404, detail="Step not found")
    
    update_data = step.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_step, field, value)
    
    db.commit()
    db.refresh(db_step)
    return db_step


@app.delete("/steps/{step_id}")
def delete_step(step_id: int, db: Session = Depends(get_db)):
    """Delete a step"""
    step = db.query(models.Step).filter(models.Step.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    db.delete(step)
    db.commit()
    return {"message": "Step deleted"}


# ============ EXECUTION ENDPOINTS ============

@app.post("/workflows/{workflow_id}/run", response_model=schemas.RunWorkflowResponse)
async def run_workflow(workflow_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Start executing a workflow"""
    from .workflow_executor import execute_workflow
    
    workflow = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    if not workflow.steps:
        raise HTTPException(status_code=400, detail="Workflow has no steps")
    
    # Create execution record
    execution = models.Execution(
        workflow_id=workflow_id,
        status=models.ExecutionStatus.PENDING
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    
    # Create step execution records for each step
    for step in workflow.steps:
        step_exec = models.StepExecution(
            execution_id=execution.id,
            step_id=step.id,
            status=models.StepStatus.PENDING
        )
        db.add(step_exec)
    db.commit()
    
    # Run workflow in background
    background_tasks.add_task(execute_workflow, execution.id)
    
    return schemas.RunWorkflowResponse(
        execution_id=execution.id,
        message="Workflow execution started"
    )


@app.get("/executions/", response_model=List[schemas.ExecutionSummary])
def list_executions(db: Session = Depends(get_db)):
    """List all executions"""
    executions = db.query(models.Execution).order_by(models.Execution.started_at.desc()).all()
    result = []
    for ex in executions:
        result.append(schemas.ExecutionSummary(
            id=ex.id,
            workflow_id=ex.workflow_id,
            workflow_name=ex.workflow.name,
            status=ex.status,
            current_step_order=ex.current_step_order,
            total_steps=len(ex.workflow.steps),
            started_at=ex.started_at,
            completed_at=ex.completed_at,
            total_tokens=ex.total_tokens or 0,
            total_cost_usd=ex.total_cost_usd or "0.0"
        ))
    return result


@app.get("/executions/{execution_id}", response_model=schemas.Execution)
def get_execution(execution_id: int, db: Session = Depends(get_db)):
    """Get execution details with all step executions"""
    execution = db.query(models.Execution).filter(models.Execution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution


@app.get("/workflows/{workflow_id}/executions", response_model=List[schemas.ExecutionSummary])
def get_workflow_executions(workflow_id: int, db: Session = Depends(get_db)):
    """Get all executions for a specific workflow"""
    workflow = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    executions = db.query(models.Execution).filter(
        models.Execution.workflow_id == workflow_id
    ).order_by(models.Execution.started_at.desc()).all()
    
    result = []
    for ex in executions:
        result.append(schemas.ExecutionSummary(
            id=ex.id,
            workflow_id=ex.workflow_id,
            workflow_name=workflow.name,
            status=ex.status,
            current_step_order=ex.current_step_order,
            total_steps=len(workflow.steps),
            started_at=ex.started_at,
            completed_at=ex.completed_at,
            total_tokens=ex.total_tokens or 0,
            total_cost_usd=ex.total_cost_usd or "0.0"
        ))
    return result


# ============ UTILITY ENDPOINTS ============

@app.get("/models/")
def list_available_models():
    """List available LLM models"""
    return {
        "models": [
            {"id": "auto", "name": "🤖 Auto Select", "description": "Automatically picks the best model for the task"},
            {"id": "kimi-k2p5", "name": "Kimi K2.5", "description": "262k context, images, extended thinking"},
            {"id": "kimi-k2-instruct-0905", "name": "Kimi K2 Instruct", "description": "256k context, instruction-following"},
        ]
    }


@app.get("/criteria-types/")
def list_criteria_types():
    """List available completion criteria types"""
    return {
        "criteria_types": [
            {"id": "always_pass", "name": "Always Pass", "description": "Step always succeeds (for testing)"},
            {"id": "contains", "name": "Contains String", "description": "Output must contain specific text"},
            {"id": "regex", "name": "Regex Match", "description": "Output must match a regex pattern"},
            {"id": "json_valid", "name": "Valid JSON", "description": "Output must be valid JSON"},
            {"id": "code_block", "name": "Has Code Block", "description": "Output must contain code blocks"},
            {"id": "llm_judge", "name": "LLM Judge", "description": "Use another LLM to evaluate"},
        ]
    }


@app.get("/context-modes/")
def list_context_modes():
    """List available context passing modes"""
    return {
        "context_modes": [
            {"id": "full", "name": "Full Output", "description": "Pass entire previous output"},
            {"id": "code_only", "name": "Code Only", "description": "Extract and pass only code blocks"},
            {"id": "summary", "name": "Summary", "description": "LLM summarizes before passing"},
            {"id": "custom", "name": "Custom", "description": "User-defined extraction template"},
        ]
    }


# ============ WORKFLOW EXPORT/IMPORT ============

@app.get("/workflows/{workflow_id}/export")
def export_workflow(workflow_id: int, db: Session = Depends(get_db)):
    """Export a workflow definition as JSON"""
    workflow = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    export_data = {
        "version": "1.0",
        "workflow": {
            "name": workflow.name,
            "description": workflow.description,
            "steps": [
                {
                    "order": step.order,
                    "name": step.name,
                    "model": step.model,
                    "prompt": step.prompt,
                    "criteria_type": step.criteria_type.value if hasattr(step.criteria_type, 'value') else step.criteria_type,
                    "criteria_value": step.criteria_value,
                    "max_retries": step.max_retries,
                    "context_mode": step.context_mode.value if hasattr(step.context_mode, 'value') else step.context_mode,
                    "context_template": step.context_template,
                }
                for step in sorted(workflow.steps, key=lambda s: s.order)
            ]
        }
    }
    return export_data


@app.post("/workflows/import")
def import_workflow(import_data: dict, db: Session = Depends(get_db)):
    """Import a workflow from JSON definition"""
    if "workflow" not in import_data:
        raise HTTPException(status_code=400, detail="Invalid import format: missing 'workflow' key")
    
    workflow_data = import_data["workflow"]
    
    # Create the workflow
    workflow = models.Workflow(
        name=workflow_data.get("name", "Imported Workflow"),
        description=workflow_data.get("description", "")
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    
    # Create steps
    for step_data in workflow_data.get("steps", []):
        step = models.Step(
            workflow_id=workflow.id,
            order=step_data.get("order", 1),
            name=step_data.get("name", "Step"),
            model=step_data.get("model", "kimi-k2p5"),
            prompt=step_data.get("prompt", ""),
            criteria_type=step_data.get("criteria_type", "always_pass"),
            criteria_value=step_data.get("criteria_value"),
            max_retries=step_data.get("max_retries", 3),
            context_mode=step_data.get("context_mode", "full"),
            context_template=step_data.get("context_template")
        )
        db.add(step)
    
    db.commit()
    db.refresh(workflow)
    
    return {
        "message": "Workflow imported successfully",
        "workflow_id": workflow.id,
        "name": workflow.name,
        "steps_count": len(workflow.steps)
    }
