import axios from 'axios';

// Use VITE_API_URL env var if set (production), otherwise use local
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL, 
});

// ============ WORKFLOW API ============

export const getWorkflows = () => api.get('/workflows/');
export const getWorkflow = (id) => api.get(`/workflows/${id}`);
export const createWorkflow = (data) => api.post('/workflows/', data);
export const updateWorkflow = (id, data) => api.put(`/workflows/${id}`, data);
export const deleteWorkflow = (id) => api.delete(`/workflows/${id}`);

// ============ STEP API ============

export const addStep = (workflowId, data) => api.post(`/workflows/${workflowId}/steps/`, data);
export const updateStep = (stepId, data) => api.put(`/steps/${stepId}`, data);
export const deleteStep = (stepId) => api.delete(`/steps/${stepId}`);

// ============ EXECUTION API ============

export const runWorkflow = (workflowId) => api.post(`/workflows/${workflowId}/run`);
export const getExecutions = () => api.get('/executions/');
export const getExecution = (id) => api.get(`/executions/${id}`);
export const getWorkflowExecutions = (workflowId) => api.get(`/workflows/${workflowId}/executions`);

// ============ UTILITY API ============

export const getModels = () => api.get('/models/');
export const getCriteriaTypes = () => api.get('/criteria-types/');
export const getContextModes = () => api.get('/context-modes/');

// ============ EXPORT/IMPORT API ============

export const exportWorkflow = (workflowId) => api.get(`/workflows/${workflowId}/export`);
export const importWorkflow = (data) => api.post('/workflows/import', data);

export default api;