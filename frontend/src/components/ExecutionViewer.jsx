import React, { useState, useEffect } from 'react';
import { getExecution } from '../api';

const ExecutionViewer = ({ execution, onBack, onRefresh }) => {
  const [autoRefresh, setAutoRefresh] = useState(
    execution.status === 'pending' || execution.status === 'running'
  );

  useEffect(() => {
    let interval;
    if (autoRefresh && (execution.status === 'pending' || execution.status === 'running')) {
      interval = setInterval(() => {
        onRefresh();
      }, 2000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh, execution.status, onRefresh]);

  // Stop auto-refresh when execution completes
  useEffect(() => {
    if (execution.status === 'completed' || execution.status === 'failed') {
      setAutoRefresh(false);
    }
  }, [execution.status]);

  const getStatusBadge = (status) => {
    const badges = {
      pending: { emoji: '⏳', color: '#ffc107', text: 'Pending' },
      running: { emoji: '🔄', color: '#17a2b8', text: 'Running' },
      completed: { emoji: '✅', color: '#28a745', text: 'Completed' },
      failed: { emoji: '❌', color: '#dc3545', text: 'Failed' },
      retrying: { emoji: '🔁', color: '#fd7e14', text: 'Retrying' },
    };
    const badge = badges[status] || badges.pending;
    return (
      <span style={{ 
        backgroundColor: badge.color, 
        padding: '4px 12px', 
        borderRadius: '4px',
        color: 'white',
        fontWeight: 'bold'
      }}>
        {badge.emoji} {badge.text}
      </span>
    );
  };

  const formatDateTime = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString();
  };

  const calculateDuration = (start, end) => {
    if (!start) return '-';
    const startDate = new Date(start);
    const endDate = end ? new Date(end) : new Date();
    const diffMs = endDate - startDate;
    const diffSecs = Math.floor(diffMs / 1000);
    if (diffSecs < 60) return `${diffSecs}s`;
    const mins = Math.floor(diffSecs / 60);
    const secs = diffSecs % 60;
    return `${mins}m ${secs}s`;
  };

  return (
    <div className="execution-viewer">
      <div className="viewer-header">
        <button className="btn btn-secondary" onClick={onBack}>
          ← Back to Workflows
        </button>
        <h2>Execution #{execution.id}</h2>
        <div className="header-status">
          {getStatusBadge(execution.status)}
        </div>
      </div>

      <div className="execution-summary">
        <div className="summary-item">
          <label>Status</label>
          {getStatusBadge(execution.status)}
        </div>
        <div className="summary-item">
          <label>Progress</label>
          <span>Step {execution.current_step_order} of {execution.step_executions?.length || 0}</span>
        </div>
        <div className="summary-item">
          <label>Started</label>
          <span>{formatDateTime(execution.started_at)}</span>
        </div>
        <div className="summary-item">
          <label>Duration</label>
          <span>{calculateDuration(execution.started_at, execution.completed_at)}</span>
        </div>
        {execution.error_message && (
          <div className="summary-item error">
            <label>Error</label>
            <span>{execution.error_message}</span>
          </div>
        )}
        <div className="summary-item">
          <label>💰 Total Cost</label>
          <span className="cost-badge">${execution.total_cost_usd || '0.000000'}</span>
        </div>
        <div className="summary-item">
          <label>🔢 Total Tokens</label>
          <span>{execution.total_tokens?.toLocaleString() || 0}</span>
        </div>
      </div>

      <div className="auto-refresh-toggle">
        <label>
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
          />
          Auto-refresh every 2 seconds
        </label>
        <button className="btn btn-small" onClick={onRefresh}>
          🔄 Refresh Now
        </button>
      </div>

      <div className="step-executions">
        <h3>Step Details</h3>
        {execution.step_executions?.map((stepExec, index) => (
          <StepExecutionCard 
            key={stepExec.id} 
            stepExecution={stepExec} 
            index={index}
            getStatusBadge={getStatusBadge}
          />
        ))}
      </div>
    </div>
  );
};

const StepExecutionCard = ({ stepExecution, index, getStatusBadge }) => {
  const [expanded, setExpanded] = useState(false);
  const step = stepExecution.step;

  return (
    <div className={`step-execution-card ${stepExecution.status}`}>
      <div className="step-exec-header" onClick={() => setExpanded(!expanded)}>
        <div className="step-exec-order">{index + 1}</div>
        <div className="step-exec-info">
          <strong>{step?.name || `Step ${index + 1}`}</strong>
          <span className="step-exec-model">{step?.model}</span>
        </div>
        <div className="step-exec-status">
          {getStatusBadge(stepExecution.status)}
          {stepExecution.attempt_number > 1 && (
            <span className="attempt-badge">Attempt {stepExecution.attempt_number}</span>
          )}
        </div>
        <button className="btn btn-icon">
          {expanded ? '▼' : '▶'}
        </button>
      </div>

      {expanded && (
        <div className="step-exec-details">
          {stepExecution.input_context && (
            <div className="detail-section">
              <h4>📥 Input Context</h4>
              <pre className="code-block">{stepExecution.input_context}</pre>
            </div>
          )}

          {stepExecution.prompt_sent && (
            <div className="detail-section">
              <h4>📝 Prompt Sent</h4>
              <pre className="code-block">{stepExecution.prompt_sent}</pre>
            </div>
          )}

          {stepExecution.llm_response && (
            <div className="detail-section">
              <h4>🤖 LLM Response</h4>
              <pre className="code-block">{stepExecution.llm_response}</pre>
            </div>
          )}

          {stepExecution.criteria_details && (
            <div className="detail-section">
              <h4>
                {stepExecution.criteria_passed ? '✅' : '❌'} Criteria Evaluation
              </h4>
              <p>{stepExecution.criteria_details}</p>
            </div>
          )}

          {stepExecution.output_context && (
            <div className="detail-section">
              <h4>📤 Output Context (passed to next step)</h4>
              <pre className="code-block">{stepExecution.output_context}</pre>
            </div>
          )}

          {stepExecution.error_message && (
            <div className="detail-section error">
              <h4>⚠️ Error</h4>
              <p>{stepExecution.error_message}</p>
            </div>
          )}

          <div className="detail-section token-info">
            <h4>📊 Token Usage & Cost</h4>
            <div className="token-stats">
              <span>Prompt: {stepExecution.prompt_tokens?.toLocaleString() || 0}</span>
              <span>Completion: {stepExecution.completion_tokens?.toLocaleString() || 0}</span>
              <span>Total: {stepExecution.total_tokens?.toLocaleString() || 0}</span>
              <span className="cost-badge">💰 ${stepExecution.cost_usd || '0.000000'}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ExecutionViewer;