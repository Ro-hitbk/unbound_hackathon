# app/models.py
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base


class StepStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class ExecutionStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CriteriaType(str, enum.Enum):
    CONTAINS = "contains"           # Output must contain a string
    REGEX = "regex"                 # Output must match regex
    JSON_VALID = "json_valid"       # Output must be valid JSON
    CODE_BLOCK = "code_block"       # Output must have code blocks
    LLM_JUDGE = "llm_judge"         # Use LLM to evaluate
    ALWAYS_PASS = "always_pass"     # Always pass (for testing)


class ContextPassingMode(str, enum.Enum):
    FULL = "full"                   # Pass entire output
    CODE_ONLY = "code_only"         # Extract and pass only code blocks
    SUMMARY = "summary"             # LLM summarizes before passing
    CUSTOM = "custom"               # User-defined extraction


# ============ WORKFLOW DEFINITION ============

class Workflow(Base):
    """A workflow is a sequence of steps to be executed"""
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    steps = relationship("Step", back_populates="workflow", cascade="all, delete-orphan", order_by="Step.order")
    executions = relationship("Execution", back_populates="workflow", cascade="all, delete-orphan")


class Step(Base):
    """A single step in a workflow"""
    __tablename__ = "steps"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    order = Column(Integer, nullable=False)  # Execution order (1, 2, 3...)
    name = Column(String(200), nullable=False)
    
    # LLM Configuration
    model = Column(String(100), nullable=False, default="kimi-k2p5")
    prompt = Column(Text, nullable=False)
    
    # Completion Criteria
    criteria_type = Column(Enum(CriteriaType), default=CriteriaType.ALWAYS_PASS)
    criteria_value = Column(Text, nullable=True)  # The pattern/string/prompt for criteria
    max_retries = Column(Integer, default=3)
    
    # Context Passing
    context_mode = Column(Enum(ContextPassingMode), default=ContextPassingMode.FULL)
    context_template = Column(Text, nullable=True)  # Custom template for context injection
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    workflow = relationship("Workflow", back_populates="steps")
    step_executions = relationship("StepExecution", back_populates="step", cascade="all, delete-orphan")


# ============ EXECUTION TRACKING ============

class Execution(Base):
    """A single run of a workflow"""
    __tablename__ = "executions"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    status = Column(Enum(ExecutionStatus), default=ExecutionStatus.PENDING)
    current_step_order = Column(Integer, default=1)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Total cost tracking for the entire run
    total_tokens = Column(Integer, default=0)
    total_cost_usd = Column(String(20), default="0.0")

    # Relationships
    workflow = relationship("Workflow", back_populates="executions")
    step_executions = relationship("StepExecution", back_populates="execution", cascade="all, delete-orphan")


class StepExecution(Base):
    """Execution details for a single step"""
    __tablename__ = "step_executions"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("executions.id"), nullable=False)
    step_id = Column(Integer, ForeignKey("steps.id"), nullable=False)
    
    status = Column(Enum(StepStatus), default=StepStatus.PENDING)
    attempt_number = Column(Integer, default=1)
    
    # Input/Output
    input_context = Column(Text, nullable=True)      # Context passed from previous step
    prompt_sent = Column(Text, nullable=True)        # Actual prompt sent to LLM
    llm_response = Column(Text, nullable=True)       # Raw LLM response
    output_context = Column(Text, nullable=True)     # Extracted context for next step
    
    # Token/Cost tracking
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost_usd = Column(String(20), default="0.0")     # Cost in USD as string for precision
    
    # Criteria evaluation
    criteria_passed = Column(Integer, default=0)  # Boolean as int for MySQL compatibility
    criteria_details = Column(Text, nullable=True)   # Details about criteria check
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    execution = relationship("Execution", back_populates="step_executions")
    step = relationship("Step", back_populates="step_executions")
