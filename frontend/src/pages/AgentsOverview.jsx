import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import './AgentsOverview.css';

const agentColors = {
  technical: '#6366f1',
  ecosystem: '#10b981',
  budget: '#f59e0b',
  impact: '#ef4444',
};

const agentDescriptions = {
  technical: 'Skeptical engineer evaluating feasibility, team capability, and timeline realism.',
  ecosystem: 'Strategic thinker assessing program fit, ecosystem gaps, and adoption paths.',
  budget: 'Financial analyst examining budget reasonableness and cost-benefit ratios.',
  impact: 'Outcome-focused evaluator considering reach, lasting value, and counterfactual impact.',
};

export default function AgentsOverview() {
  const [agents, setAgents] = useState([]);
  const [observations, setObservations] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const agentList = await api.listAgents();
      setAgents(agentList);

      // Load observation counts for each agent
      const obsCounts = {};
      for (const agent of agentList) {
        try {
          const obs = await api.listObservations(agent.id, 'active');
          obsCounts[agent.id] = obs.length;
        } catch {
          obsCounts[agent.id] = 0;
        }
      }
      setObservations(obsCounts);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="loading">Loading agents...</div>;
  if (error) return <div className="error">Error: {error}</div>;

  return (
    <div className="agents-overview">
      <div className="page-header">
        <div>
          <h1>Council Agents</h1>
          <p className="subtitle">The four specialized AI agents that evaluate grant applications</p>
        </div>
      </div>

      <div className="agents-grid">
        {agents.map(agent => (
          <div key={agent.id} className="agent-card" style={{ borderTopColor: agentColors[agent.id] }}>
            <div className="agent-icon" style={{ background: agentColors[agent.id] }}>
              {agent.id.charAt(0).toUpperCase()}
            </div>
            <h2 className="agent-name">{agent.name}</h2>
            <p className="agent-role">{agent.role}</p>
            <p className="agent-description">
              {agentDescriptions[agent.id] || 'Specialized agent for grant evaluation.'}
            </p>

            <div className="agent-stats">
              <div className="stat">
                <span className="stat-value">{observations[agent.id] || 0}</span>
                <span className="stat-label">Active Observations</span>
              </div>
            </div>

            <div className="agent-model">
              <span className="model-label">Model:</span>
              <span className="model-name">{agent.model || 'Default'}</span>
            </div>

            <Link
              to={`/observations?agent=${agent.id}`}
              className="view-observations"
            >
              View Observations →
            </Link>
          </div>
        ))}
      </div>

      <div className="agents-explainer">
        <h3>How Agents Work</h3>
        <div className="explainer-content">
          <div className="explainer-item">
            <span className="explainer-num">1</span>
            <div>
              <strong>Independent Evaluation</strong>
              <p>Each agent evaluates applications from their unique perspective, producing a score, recommendation, and detailed rationale.</p>
            </div>
          </div>
          <div className="explainer-item">
            <span className="explainer-num">2</span>
            <div>
              <strong>Deliberation</strong>
              <p>Agents see anonymized peer evaluations and can revise their positions based on arguments they find compelling.</p>
            </div>
          </div>
          <div className="explainer-item">
            <span className="explainer-num">3</span>
            <div>
              <strong>Learning</strong>
              <p>When humans override decisions or outcomes are recorded, agents reflect and develop new observations to improve future evaluations.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
