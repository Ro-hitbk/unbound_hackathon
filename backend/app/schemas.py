# app/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ============ ENUMS ============

class CriteriaType(str, Enum):
    CONTAINS = "contains"
    REGEX = "regex"
    JSON_VALID = "json_valid"
    CODE_BLOCK = "code_block"
    LLM_JUDGE = "llm_judge"
    ALWAYS_PASS = "always_pass"


class ContextPassingMode(str, Enum):
    FULL = "full"
    CODE_ONLY = "code_only"
    SUMMARY = "summary"
    CUSTOM = "custom"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ============ STEP SCHEMAS ============

class StepBase(BaseModel):
    name: str
    order: int
    model: str = "kimi-k2p5"
    prompt: str
    criteria_type: CriteriaType = CriteriaType.ALWAYS_PASS
    criteria_value: Optional[str] = None
    max_retries: int = 3
    context_mode: ContextPassingMode = ContextPassingMode.FULL
    context_template: Optional[str] = None


class StepCreate(StepBase):
    pass


class StepUpdate(BaseModel):
    name: Optional[str] = None
    order: Optional[int] = None
    model: Optional[str] = None
    prompt: Optional[str] = None
    criteria_type: Optional[CriteriaType] = None
    criteria_value: Optional[str] = None
    max_retries: Optional[int] = None
    context_mode: Optional[ContextPassingMode] = None
    context_template: Optional[str] = None


class Step(StepBase):
    id: int
    workflow_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============ WORKFLOW SCHEMAS ============

class WorkflowBase(BaseModel):
    name: str
    description: Optional[str] = None


class WorkflowCreate(WorkflowBase):
    steps: Optional[List[StepCreate]] = []


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class Workflow(WorkflowBase):
    id: int
    created_at: datetime
    updated_at: datetime
    steps: List[Step] = []

    class Config:
        from_attributes = True


class WorkflowSummary(WorkflowBase):
    id: int
    created_at: datetime
    step_count: int = 0

    class Config:
        from_attributes = True


# ============ STEP EXECUTION SCHEMAS ============

class StepExecutionBase(BaseModel):
    step_id: int
    status: StepStatus = StepStatus.PENDING
    attempt_number: int = 1


class StepExecution(StepExecutionBase):
    id: int
    execution_id: int
    input_context: Optional[str] = None
    prompt_sent: Optional[str] = None
    llm_response: Optional[str] = None
    output_context: Optional[str] = None
    criteria_passed: bool = False
    criteria_details: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: str = "0.0"
    step: Optional[Step] = None

    class Config:
        from_attributes = True


# ============ EXECUTION SCHEMAS ============

class ExecutionBase(BaseModel):
    workflow_id: int


class ExecutionCreate(ExecutionBase):
    pass


class Execution(ExecutionBase):
    id: int
    status: ExecutionStatus
    current_step_order: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    total_tokens: int = 0
    total_cost_usd: str = "0.0"
    step_executions: List[StepExecution] = []

    class Config:
        from_attributes = True


class ExecutionSummary(BaseModel):
    id: int
    workflow_id: int
    workflow_name: str
    status: ExecutionStatus
    current_step_order: int
    total_steps: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_tokens: int = 0
    total_cost_usd: str = "0.0"

    class Config:
        from_attributes = True


# ============ API RESPONSE SCHEMAS ============

class RunWorkflowResponse(BaseModel):
    execution_id: int
    message: str


class StepExecutionUpdate(BaseModel):
    status: StepStatus
    llm_response: Optional[str] = None
    criteria_passed: bool = False
    criteria_details: Optional[str] = None
    error_message: Optional[str] = None
