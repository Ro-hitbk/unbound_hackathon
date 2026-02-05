import React, { useState, useEffect } from 'react';
import { deleteWorkflow, runWorkflow, getWorkflowExecutions } from '../api';

const WorkflowList = ({ workflows, onEdit, onViewExecution, onRefresh }) => {
  const [executionsMap, setExecutionsMap] = useState({});
  const [runningWorkflows, setRunningWorkflows] = useState(new Set());

  useEffect(() => {
    // Load recent executions for each workflow
    const loadExecutions = async () => {
      const execMap = {};
      for (const wf of workflows) {
        try {
          const response = await getWorkflowExecutions(wf.id);
          execMap[wf.id] = response.data.slice(0, 3); // Get last 3
        } catch (error) {
          execMap[wf.id] = [];
        }
      }
      setExecutionsMap(execMap);
    };
    if (workflows.length > 0) {
      loadExecutions();
    }
  }, [workflows]);

  const handleDelete = async (id, name) => {
    if (window.confirm(`Delete workflow "${name}"? This cannot be undone.`)) {
      try {
        await deleteWorkflow(id);
        onRefresh();
      } catch (error) {
        alert('Failed to delete workflow');
      }
    }
  };

  const handleRun = async (id) => {
    setRunningWorkflows(prev => new Set([...prev, id]));
    try {
      const response = await runWorkflow(id);
      alert(`Workflow started! Execution ID: ${response.data.execution_id}`);
      // Wait a moment then view the execution
      setTimeout(() => {
        onViewExecution(response.data.execution_id);
      }, 500);
    } catch (error) {
      alert(`Failed to run workflow: ${error.response?.data?.detail || error.message}`);
    }
    setRunningWorkflows(prev => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  };

  const getStatusBadge = (status) => {
    const badges = {
      pending: { emoji: '⏳', color: '#ffc107' },
      running: { emoji: '🔄', color: '#17a2b8' },
      completed: { emoji: '✅', color: '#28a745' },
      failed: { emoji: '❌', color: '#dc3545' },
    };
    const badge = badges[status] || badges.pending;
    return (
      <span style={{ 
        backgroundColor: badge.color, 
        padding: '2px 8px', 
        borderRadius: '4px',
        fontSize: '12px',
        color: 'white'
      }}>
        {badge.emoji} {status}
      </span>
    );
  };

  if (workflows.length === 0) {
    return (
      <div className="empty-state">
        <h2>No workflows yet</h2>
        <p>Create your first workflow to get started!</p>
      </div>
    );
  }

  return (
    <div className="workflow-list">
      <h2>Your Workflows</h2>
      <div className="workflow-grid">
        {workflows.map((wf) => (
          <div key={wf.id} className="workflow-card">
            <div className="workflow-card-header">
              <h3>{wf.name}</h3>
              <span className="step-count">{wf.step_count} steps</span>
            </div>
            
            {wf.description && (
              <p className="workflow-description">{wf.description}</p>
            )}
            
            <div className="workflow-meta">
              <small>Created: {new Date(wf.created_at).toLocaleDateString()}</small>
            </div>

            {executionsMap[wf.id]?.length > 0 && (
              <div className="recent-executions">
                <h4>Recent Runs:</h4>
                {executionsMap[wf.id].map((ex) => (
                  <div 
                    key={ex.id} 
                    className="execution-item"
                    onClick={() => onViewExecution(ex.id)}
                  >
                    {getStatusBadge(ex.status)}
                    <small>{new Date(ex.started_at).toLocaleString()}</small>
                  </div>
                ))}
              </div>
            )}

            <div className="workflow-actions">
              <button 
                className="btn btn-primary"
                onClick={() => handleRun(wf.id)}
                disabled={runningWorkflows.has(wf.id) || wf.step_count === 0}
              >
                {runningWorkflows.has(wf.id) ? '🔄 Starting...' : '▶️ Run'}
              </button>
              <button 
                className="btn btn-secondary"
                onClick={() => onEdit(wf.id)}
              >
                ✏️ Edit
              </button>
              <button 
                className="btn btn-danger"
                onClick={() => handleDelete(wf.id, wf.name)}
              >
                🗑️
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default WorkflowList;