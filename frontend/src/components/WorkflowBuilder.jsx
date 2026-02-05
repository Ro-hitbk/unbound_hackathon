import React, { useState, useEffect, useRef } from 'react';
import { 
  createWorkflow, updateWorkflow, addStep, updateStep, deleteStep,
  getModels, getCriteriaTypes, getContextModes, runWorkflow, exportWorkflow
} from '../api';
import StepEditor from './StepEditor';

const WorkflowBuilder = ({ workflow, onSave, onCancel, onRunComplete }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [steps, setSteps] = useState([]);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [models, setModels] = useState([]);
  const [criteriaTypes, setCriteriaTypes] = useState([]);
  const [contextModes, setContextModes] = useState([]);
  const [workflowId, setWorkflowId] = useState(null);

  useEffect(() => {
    // Load options
    const loadOptions = async () => {
      try {
        const [modelsRes, criteriaRes, contextRes] = await Promise.all([
          getModels(),
          getCriteriaTypes(),
          getContextModes()
        ]);
        setModels(modelsRes.data.models);
        setCriteriaTypes(criteriaRes.data.criteria_types);
        setContextModes(contextRes.data.context_modes);
      } catch (error) {
        console.error('Failed to load options:', error);
      }
    };
    loadOptions();

    // Load existing workflow if editing
    if (workflow) {
      setWorkflowId(workflow.id);
      setName(workflow.name);
      setDescription(workflow.description || '');
      setSteps(workflow.steps.map(s => ({
        ...s,
        _saved: true  // Mark as already saved
      })));
    }
  }, [workflow]);

  const handleAddStep = () => {
    const newOrder = steps.length + 1;
    setSteps([...steps, {
      id: null,  // New step, no ID yet
      name: `Step ${newOrder}`,
      order: newOrder,
      model: 'kimi-k2p5',
      prompt: '',
      criteria_type: 'always_pass',
      criteria_value: '',
      max_retries: 3,
      context_mode: 'full',
      context_template: '',
      _saved: false,
      _expanded: true
    }]);
  };

  const handleUpdateStep = (index, updates) => {
    const newSteps = [...steps];
    newSteps[index] = { ...newSteps[index], ...updates, _saved: false };
    setSteps(newSteps);
  };

  const handleRemoveStep = async (index) => {
    const step = steps[index];
    if (step.id && step._saved) {
      // Delete from server
      try {
        await deleteStep(step.id);
      } catch (error) {
        alert('Failed to delete step');
        return;
      }
    }
    const newSteps = steps.filter((_, i) => i !== index);
    // Reorder
    newSteps.forEach((s, i) => {
      s.order = i + 1;
    });
    setSteps(newSteps);
  };

  const handleMoveStep = (index, direction) => {
    const newIndex = index + direction;
    if (newIndex < 0 || newIndex >= steps.length) return;
    
    const newSteps = [...steps];
    [newSteps[index], newSteps[newIndex]] = [newSteps[newIndex], newSteps[index]];
    // Update order numbers
    newSteps.forEach((s, i) => {
      s.order = i + 1;
      s._saved = false;
    });
    setSteps(newSteps);
  };

  const handleSave = async () => {
    if (!name.trim()) {
      alert('Please enter a workflow name');
      return;
    }

    if (steps.length === 0) {
      alert('Please add at least one step');
      return;
    }

    for (const step of steps) {
      if (!step.prompt.trim()) {
        alert(`Step "${step.name}" needs a prompt`);
        return;
      }
    }

    setSaving(true);

    try {
      let wfId = workflowId;

      if (!wfId) {
        // Create new workflow with steps
        const stepsData = steps.map(s => ({
          name: s.name,
          order: s.order,
          model: s.model,
          prompt: s.prompt,
          criteria_type: s.criteria_type,
          criteria_value: s.criteria_value || null,
          max_retries: s.max_retries,
          context_mode: s.context_mode,
          context_template: s.context_template || null
        }));

        const response = await createWorkflow({
          name,
          description: description || null,
          steps: stepsData
        });
        wfId = response.data.id;
      } else {
        // Update existing workflow
        await updateWorkflow(wfId, { name, description: description || null });

        // Update/create steps
        for (const step of steps) {
          const stepData = {
            name: step.name,
            order: step.order,
            model: step.model,
            prompt: step.prompt,
            criteria_type: step.criteria_type,
            criteria_value: step.criteria_value || null,
            max_retries: step.max_retries,
            context_mode: step.context_mode,
            context_template: step.context_template || null
          };

          if (step.id) {
            await updateStep(step.id, stepData);
          } else {
            await addStep(wfId, stepData);
          }
        }
      }

      onSave();
    } catch (error) {
      alert('Failed to save workflow: ' + (error.response?.data?.detail || error.message));
    }

    setSaving(false);
  };

  const handleRun = async () => {
    // First save
    await handleSave();
    
    if (!workflowId) {
      alert('Please save the workflow first');
      return;
    }

    setRunning(true);
    try {
      const response = await runWorkflow(workflowId);
      onRunComplete(response.data.execution_id);
    } catch (error) {
      alert('Failed to run workflow: ' + (error.response?.data?.detail || error.message));
    }
    setRunning(false);
  };

  const handleExport = async () => {
    if (!workflowId) {
      alert('Please save the workflow first before exporting.');
      return;
    }
    try {
      const response = await exportWorkflow(workflowId);
      const dataStr = JSON.stringify(response.data, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(dataBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${name.replace(/[^a-z0-9]/gi, '_')}_workflow.json`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
      alert('Failed to export workflow');
    }
  };

  return (
    <div className="workflow-builder">
      <div className="builder-header">
        <h2>{workflowId ? 'Edit Workflow' : 'Create New Workflow'}</h2>
        <div className="builder-actions">
          <button className="btn btn-secondary" onClick={onCancel}>
            Cancel
          </button>
          {workflowId && (
            <button 
              className="btn btn-outline" 
              onClick={handleExport}
              title="Export workflow as JSON"
            >
              📤 Export
            </button>
          )}
          <button 
            className="btn btn-primary" 
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Saving...' : '💾 Save'}
          </button>
          {workflowId && (
            <button 
              className="btn btn-success" 
              onClick={handleRun}
              disabled={running || steps.length === 0}
            >
              {running ? 'Starting...' : '▶️ Save & Run'}
            </button>
          )}
        </div>
      </div>

      <div className="workflow-form">
        <div className="form-group">
          <label>Workflow Name *</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., Code Generator Pipeline"
          />
        </div>

        <div className="form-group">
          <label>Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What does this workflow do?"
            rows={2}
          />
        </div>
      </div>

      <div className="steps-section">
        <div className="steps-header">
          <h3>Steps ({steps.length})</h3>
          <button className="btn btn-add" onClick={handleAddStep}>
            ➕ Add Step
          </button>
        </div>

        {steps.length === 0 ? (
          <div className="empty-steps">
            <p>No steps yet. Add your first step to get started!</p>
          </div>
        ) : (
          <div className="steps-list">
            {steps.map((step, index) => (
              <StepEditor
                key={step.id || `new-${index}`}
                step={step}
                index={index}
                totalSteps={steps.length}
                models={models}
                criteriaTypes={criteriaTypes}
                contextModes={contextModes}
                onChange={(updates) => handleUpdateStep(index, updates)}
                onRemove={() => handleRemoveStep(index)}
                onMoveUp={() => handleMoveStep(index, -1)}
                onMoveDown={() => handleMoveStep(index, 1)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default WorkflowBuilder;