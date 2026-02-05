import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import WorkflowList from './components/WorkflowList';
import WorkflowBuilder from './components/WorkflowBuilder';
import ExecutionViewer from './components/ExecutionViewer';
import { getWorkflows, getWorkflow, getExecution, importWorkflow } from './api';

const App = () => {
  const [view, setView] = useState('list'); // 'list', 'builder', 'execution'
  const [workflows, setWorkflows] = useState([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState(null);
  const [selectedExecution, setSelectedExecution] = useState(null);
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef(null);

  const loadWorkflows = async () => {
    setLoading(true);
    try {
      const response = await getWorkflows();
      setWorkflows(response.data);
    } catch (error) {
      console.error('Failed to load workflows:', error);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadWorkflows();
  }, []);

  const handleNewWorkflow = () => {
    setSelectedWorkflow(null);
    setView('builder');
  };

  const handleEditWorkflow = async (workflowId) => {
    setLoading(true);
    try {
      const response = await getWorkflow(workflowId);
      setSelectedWorkflow(response.data);
      setView('builder');
    } catch (error) {
      console.error('Failed to load workflow:', error);
    }
    setLoading(false);
  };

  const handleViewExecution = async (executionId) => {
    setLoading(true);
    try {
      const response = await getExecution(executionId);
      setSelectedExecution(response.data);
      setView('execution');
    } catch (error) {
      console.error('Failed to load execution:', error);
    }
    setLoading(false);
  };

  const handleBackToList = () => {
    setSelectedWorkflow(null);
    setSelectedExecution(null);
    setView('list');
    loadWorkflows();
  };

  const handleWorkflowSaved = () => {
    loadWorkflows();
    setView('list');
  };

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileImport = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    try {
      const text = await file.text();
      const data = JSON.parse(text);
      const response = await importWorkflow(data);
      alert(`Workflow "${response.data.name}" imported successfully with ${response.data.steps_count} steps!`);
      loadWorkflows();
      // Optionally open the imported workflow for editing
      handleEditWorkflow(response.data.workflow_id);
    } catch (error) {
      console.error('Import failed:', error);
      alert('Failed to import workflow: ' + (error.response?.data?.detail || error.message));
    }
    // Reset file input
    event.target.value = '';
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🤖 Agentic Workflow Builder</h1>
        <p className="subtitle">Chain AI agents together to automate complex tasks</p>
      </header>
      
      <nav className="App-nav">
        <button 
          onClick={handleBackToList} 
          className={view === 'list' ? 'active' : ''}
        >
          📋 Workflows
        </button>
        <button 
          onClick={handleNewWorkflow}
          className={view === 'builder' && !selectedWorkflow ? 'active' : ''}
        >
          ➕ New Workflow
        </button>
        <button onClick={handleImportClick}>
          📥 Import
        </button>
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: 'none' }}
          accept=".json"
          onChange={handleFileImport}
        />
      </nav>

      <main className="App-main">
        {loading && <div className="loading">Loading...</div>}
        
        {!loading && view === 'list' && (
          <WorkflowList 
            workflows={workflows}
            onEdit={handleEditWorkflow}
            onViewExecution={handleViewExecution}
            onRefresh={loadWorkflows}
          />
        )}
        
        {!loading && view === 'builder' && (
          <WorkflowBuilder 
            workflow={selectedWorkflow}
            onSave={handleWorkflowSaved}
            onCancel={handleBackToList}
            onRunComplete={handleViewExecution}
          />
        )}
        
        {!loading && view === 'execution' && selectedExecution && (
          <ExecutionViewer 
            execution={selectedExecution}
            onBack={handleBackToList}
            onRefresh={() => handleViewExecution(selectedExecution.id)}
          />
        )}
      </main>
    </div>
  );
};

export default App;