# app/workflow_executor.py
"""
Workflow execution engine.
Runs workflows step by step, calling LLMs, checking criteria, and passing context.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import (
    Execution, StepExecution, Step, Workflow,
    ExecutionStatus, StepStatus, ContextPassingMode
)
from .unbound_client import call_llm, summarize_for_context, calculate_cost, select_model_for_task
from .criteria_checker import evaluate_criteria, extract_context

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_db_session() -> Session:
    """Create a new database session."""
    return SessionLocal()


async def execute_step(
    step: Step,
    step_execution: StepExecution,
    input_context: Optional[str],
    db: Session
) -> tuple[bool, Optional[str]]:
    """
    Execute a single step with retry logic.
    
    Args:
        step: The step definition
        step_execution: The execution record to update
        input_context: Context from previous step
        db: Database session
    
    Returns:
        Tuple of (success: bool, output_context: Optional[str])
    """
    max_attempts = step.max_retries + 1  # Initial attempt + retries
    
    for attempt in range(1, max_attempts + 1):
        # Update attempt number
        logger.info(f"Step '{step.name}' attempt {attempt}/{max_attempts}")
        step_execution.attempt_number = attempt
        step_execution.status = StepStatus.RUNNING if attempt == 1 else StepStatus.RETRYING
        step_execution.started_at = datetime.utcnow()
        step_execution.input_context = input_context
        db.commit()
        
        # Build the full prompt with context
        full_prompt = step.prompt
        if input_context:
            full_prompt = f"Context from previous step:\n\n{input_context}\n\n---\n\nYour task:\n{step.prompt}"
        
        step_execution.prompt_sent = full_prompt
        db.commit()
        
        # Determine model - use auto-selection if "auto" is specified
        model_to_use = step.model
        if step.model == "auto":
            criteria_type_str = step.criteria_type.value if hasattr(step.criteria_type, 'value') else step.criteria_type
            model_to_use = select_model_for_task(full_prompt, criteria_type_str)
            logger.info(f"Auto-selected model: {model_to_use}")
        
        # Call the LLM
        logger.info(f"Calling LLM model={model_to_use}")
        result = await call_llm(
            model=model_to_use,
            prompt=full_prompt
        )
        logger.info(f"LLM result: success={result['success']}")
        
        # Store token usage if available
        usage = result.get("usage", {})
        step_execution.prompt_tokens = usage.get("prompt_tokens", 0)
        step_execution.completion_tokens = usage.get("completion_tokens", 0)
        step_execution.total_tokens = usage.get("total_tokens", 0)
        step_execution.cost_usd = str(calculate_cost(
            model_to_use,
            step_execution.prompt_tokens,
            step_execution.completion_tokens
        ))
        db.commit()
        
        if not result["success"]:
            step_execution.error_message = result["error"]
            step_execution.llm_response = None
            db.commit()
            
            if attempt < max_attempts:
                await asyncio.sleep(2)  # Wait before retry
                continue
            else:
                step_execution.status = StepStatus.FAILED
                step_execution.completed_at = datetime.utcnow()
                db.commit()
                return False, None
        
        # Store the response
        llm_response = result["response"]
        step_execution.llm_response = llm_response
        db.commit()
        
        # Evaluate criteria
        passed, details = await evaluate_criteria(
            output=llm_response,
            criteria_type=step.criteria_type,
            criteria_value=step.criteria_value,
            original_prompt=step.prompt
        )
        
        step_execution.criteria_passed = 1 if passed else 0
        step_execution.criteria_details = details
        db.commit()
        
        logger.info(f"Criteria passed={passed}, details={details}")
        
        if passed:
            # Extract context for next step
            output_context = extract_context(
                output=llm_response,
                context_mode=step.context_mode.value if hasattr(step.context_mode, 'value') else step.context_mode,
                context_template=step.context_template
            )
            
            # If summary mode, generate summary
            if step.context_mode == ContextPassingMode.SUMMARY:
                output_context = await summarize_for_context(llm_response)
            
            step_execution.output_context = output_context
            step_execution.status = StepStatus.COMPLETED
            step_execution.completed_at = datetime.utcnow()
            step_execution.error_message = None
            db.commit()
            
            return True, output_context
        else:
            # Criteria not met
            step_execution.error_message = f"Criteria not met: {details}"
            db.commit()
            
            if attempt < max_attempts:
                await asyncio.sleep(1)  # Wait before retry
                continue
            else:
                step_execution.status = StepStatus.FAILED
                step_execution.completed_at = datetime.utcnow()
                db.commit()
                return False, None
    
    return False, None


async def execute_workflow_async(execution_id: int):
    """
    Execute a workflow asynchronously.
    
    Args:
        execution_id: The execution record ID
    """
    db = get_db_session()
    
    try:
        # Load execution record
        execution = db.query(Execution).filter(Execution.id == execution_id).first()
        if not execution:
            return
        
        # Update status to running
        execution.status = ExecutionStatus.RUNNING
        db.commit()
        
        # Load workflow and steps
        workflow = execution.workflow
        steps = sorted(workflow.steps, key=lambda s: s.order)
        
        if not steps:
            execution.status = ExecutionStatus.FAILED
            execution.error_message = "Workflow has no steps"
            execution.completed_at = datetime.utcnow()
            db.commit()
            return
        
        # Execute steps in order
        current_context: Optional[str] = None
        
        for i, step in enumerate(steps):
            # Add delay between steps to avoid rate limiting
            if i > 0:
                logger.info("Waiting 2 seconds before next step...")
                await asyncio.sleep(2)
            
            logger.info(f"Starting step {step.order}: {step.name}")
            execution.current_step_order = step.order
            db.commit()
            
            # Find the step execution record
            step_execution = db.query(StepExecution).filter(
                StepExecution.execution_id == execution_id,
                StepExecution.step_id == step.id
            ).first()
            
            if not step_execution:
                # Create one if it doesn't exist
                step_execution = StepExecution(
                    execution_id=execution_id,
                    step_id=step.id,
                    status=StepStatus.PENDING
                )
                db.add(step_execution)
                db.commit()
            
            # Execute the step
            success, output_context = await execute_step(
                step=step,
                step_execution=step_execution,
                input_context=current_context,
                db=db
            )
            
            if not success:
                logger.error(f"Step '{step.name}' failed!")
                execution.status = ExecutionStatus.FAILED
                execution.error_message = f"Step '{step.name}' failed after {step.max_retries + 1} attempts"
                execution.completed_at = datetime.utcnow()
                db.commit()
                return
            
            # Pass context to next step
            logger.info(f"Step '{step.name}' completed successfully")
            current_context = output_context
        
        # All steps completed - calculate total costs
        logger.info(f"Workflow execution {execution_id} completed successfully!")
        
        # Aggregate token usage and costs from all step executions
        total_tokens = 0
        total_cost = 0.0
        for se in execution.step_executions:
            total_tokens += se.total_tokens or 0
            try:
                total_cost += float(se.cost_usd or "0")
            except ValueError:
                pass
        
        execution.total_tokens = total_tokens
        execution.total_cost_usd = str(round(total_cost, 6))
        execution.status = ExecutionStatus.COMPLETED
        execution.completed_at = datetime.utcnow()
        execution.error_message = None
        db.commit()
        
    except Exception as e:
        # Handle unexpected errors
        logger.exception(f"Unexpected error in execution {execution_id}: {e}")
        execution = db.query(Execution).filter(Execution.id == execution_id).first()
        if execution:
            execution.status = ExecutionStatus.FAILED
            execution.error_message = f"Unexpected error: {str(e)}"
            execution.completed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


def execute_workflow(execution_id: int):
    """
    Entry point for background task execution.
    Runs the async executor in an event loop.
    """
    # Create a new event loop for this thread since we're running in a background task
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(execute_workflow_async(execution_id))
    finally:
        loop.close()
