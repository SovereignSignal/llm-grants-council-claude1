import { useState, useEffect } from 'react';
import { api } from '../api';
import './ObservationsList.css';

export default function ObservationsList() {
  const [observations, setObservations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterAgent, setFilterAgent] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [agents, setAgents] = useState([]);

  useEffect(() => {
    loadData();
  }, [filterAgent, filterStatus]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [obs, agentList] = await Promise.all([
        api.listObservations(filterAgent || null, filterStatus || null),
        api.listAgents()
      ]);
      setObservations(obs);
      setAgents(agentList);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (id) => {
    try {
      await api.approveObservation(id);
      loadData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeprecate = async (id) => {
    try {
      await api.deprecateObservation(id);
      loadData();
    } catch (err) {
      setError(err.message);
    }
  };

  const getStatusClass = (status) => {
    const classes = {
      draft: 'status-draft',
      reviewed: 'status-reviewed',
      active: 'status-active',
      deprecated: 'status-deprecated',
    };
    return classes[status] || '';
  };

  if (loading) return <div className="loading">Loading observations...</div>;
  if (error) return <div className="error">Error: {error}</div>;

  return (
    <div className="observations-list">
      <div className="page-header">
        <div>
          <h1>Agent Observations</h1>
          <p className="subtitle">Learned patterns from evaluations and outcomes</p>
        </div>
      </div>

      <div className="filters">
        <select value={filterAgent} onChange={(e) => setFilterAgent(e.target.value)}>
          <option value="">All Agents</option>
          {agents.map(a => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>
        <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="reviewed">Reviewed</option>
          <option value="active">Active</option>
          <option value="deprecated">Deprecated</option>
        </select>
      </div>

      {observations.length === 0 ? (
        <div className="empty-state">
          <h3>No observations yet</h3>
          <p>Observations are generated when agents learn from overrides and outcomes.</p>
        </div>
      ) : (
        <div className="observations-grid">
          {observations.map(obs => (
            <div key={obs.id} className="observation-card">
              <div className="obs-header">
                <span className="obs-agent">{obs.agent_id}</span>
                <span className={`obs-status ${getStatusClass(obs.status)}`}>{obs.status}</span>
              </div>
              <div className="obs-pattern">{obs.pattern}</div>
              {obs.context && <div className="obs-context">{obs.context}</div>}
              <div className="obs-meta">
                <span>Evidence: {obs.evidence_count || 0}</span>
                <span>Confidence: {obs.confidence}</span>
              </div>
              {obs.tags?.length > 0 && (
                <div className="obs-tags">
                  {obs.tags.map((t, i) => (
                    <span key={i} className="tag">{t}</span>
                  ))}
                </div>
              )}
              {(obs.status === 'draft' || obs.status === 'reviewed') && (
                <div className="obs-actions">
                  <button className="btn btn-sm btn-success" onClick={() => handleApprove(obs.id)}>
                    Approve
                  </button>
                  <button className="btn btn-sm btn-danger" onClick={() => handleDeprecate(obs.id)}>
                    Deprecate
                  </button>
                </div>
              )}
              {obs.status === 'active' && (
                <div className="obs-actions">
                  <button className="btn btn-sm btn-secondary" onClick={() => handleDeprecate(obs.id)}>
                    Deprecate
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
