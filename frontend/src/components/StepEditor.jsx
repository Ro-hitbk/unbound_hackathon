import React, { useState } from 'react';

const StepEditor = ({ 
  step, 
  index, 
  totalSteps,
  models, 
  criteriaTypes, 
  contextModes,
  onChange, 
  onRemove, 
  onMoveUp, 
  onMoveDown 
}) => {
  const [expanded, setExpanded] = useState(step._expanded || false);

  const needsCriteriaValue = ['contains', 'regex', 'code_block', 'llm_judge'].includes(step.criteria_type);
  const needsContextTemplate = step.context_mode === 'custom';

  const getCriteriaPlaceholder = () => {
    switch (step.criteria_type) {
      case 'contains': return 'Text that must appear in output...';
      case 'regex': return 'Regular expression pattern...';
      case 'code_block': return 'Language (optional, e.g., python)...';
      case 'llm_judge': return 'Describe what makes a good response...';
      default: return '';
    }
  };

  return (
    <div className={`step-editor ${expanded ? 'expanded' : 'collapsed'}`}>
      <div className="step-header" onClick={() => setExpanded(!expanded)}>
        <div className="step-order">
          <span className="order-badge">{step.order}</span>
          <div className="order-controls">
            <button 
              onClick={(e) => { e.stopPropagation(); onMoveUp(); }} 
              disabled={index === 0}
              title="Move up"
            >
              ↑
            </button>
            <button 
              onClick={(e) => { e.stopPropagation(); onMoveDown(); }} 
              disabled={index === totalSteps - 1}
              title="Move down"
            >
              ↓
            </button>
          </div>
        </div>
        
        <div className="step-title">
          <strong>{step.name}</strong>
          <span className="step-model">{step.model}</span>
        </div>

        <div className="step-actions">
          <button 
            className="btn btn-icon" 
            onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
          >
            {expanded ? '▼' : '▶'}
          </button>
          <button 
            className="btn btn-icon btn-danger" 
            onClick={(e) => { e.stopPropagation(); onRemove(); }}
            title="Delete step"
          >
            🗑️
          </button>
        </div>
      </div>

      {expanded && (
        <div className="step-content">
          <div className="form-row">
            <div className="form-group">
              <label>Step Name</label>
              <input
                type="text"
                value={step.name}
                onChange={(e) => onChange({ name: e.target.value })}
                placeholder="Step name"
              />
            </div>

            <div className="form-group">
              <label>Model</label>
              <select 
                value={step.model} 
                onChange={(e) => onChange({ model: e.target.value })}
              >
                {models.map(m => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-group">
            <label>Prompt *</label>
            <textarea
              value={step.prompt}
              onChange={(e) => onChange({ prompt: e.target.value })}
              placeholder="What should this step do? Be specific about the task..."
              rows={4}
            />
            <small className="help-text">
              Context from the previous step will be automatically included.
            </small>
          </div>

          <div className="form-section">
            <h4>Completion Criteria</h4>
            <p className="section-description">
              How do we know when this step succeeded?
            </p>

            <div className="form-row">
              <div className="form-group">
                <label>Criteria Type</label>
                <select 
                  value={step.criteria_type} 
                  onChange={(e) => onChange({ criteria_type: e.target.value })}
                >
                  {criteriaTypes.map(c => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Max Retries</label>
                <input
                  type="number"
                  min="0"
                  max="10"
                  value={step.max_retries}
                  onChange={(e) => onChange({ max_retries: parseInt(e.target.value) || 0 })}
                />
              </div>
            </div>

            {needsCriteriaValue && (
              <div className="form-group">
                <label>Criteria Value</label>
                <input
                  type="text"
                  value={step.criteria_value || ''}
                  onChange={(e) => onChange({ criteria_value: e.target.value })}
                  placeholder={getCriteriaPlaceholder()}
                />
              </div>
            )}
          </div>

          <div className="form-section">
            <h4>Context Passing</h4>
            <p className="section-description">
              What gets passed to the next step?
            </p>

            <div className="form-group">
              <label>Context Mode</label>
              <select 
                value={step.context_mode} 
                onChange={(e) => onChange({ context_mode: e.target.value })}
              >
                {contextModes.map(c => (
                  <option key={c.id} value={c.id}>{c.name} - {c.description}</option>
                ))}
              </select>
            </div>

            {needsContextTemplate && (
              <div className="form-group">
                <label>Context Template</label>
                <textarea
                  value={step.context_template || ''}
                  onChange={(e) => onChange({ context_template: e.target.value })}
                  placeholder="Use {{output}} for full output, {{code}} for code blocks only"
                  rows={2}
                />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default StepEditor;