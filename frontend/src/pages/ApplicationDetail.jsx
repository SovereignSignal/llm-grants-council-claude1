import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api';
import './ApplicationDetail.css';

function AgentCard({ evaluation }) {
  const [expanded, setExpanded] = useState(false);

  const getScoreColor = (score) => {
    if (score >= 7) return '#16a34a';
    if (score >= 5) return '#ca8a04';
    return '#dc2626';
  };

  return (
    <div className="agent-card">
      <div className="agent-header" onClick={() => setExpanded(!expanded)}>
        <div className="agent-info">
          <span className="agent-name">{evaluation.agent_id}</span>
          <span className="agent-recommendation">{evaluation.recommendation?.replace(/_/g, ' ')}</span>
        </div>
        <div className="agent-score" style={{ color: getScoreColor(evaluation.score) }}>
          {evaluation.score}/10
        </div>
      </div>

      {expanded && (
        <div className="agent-details">
          <div className="detail-section">
            <h4>Rationale</h4>
            <p>{evaluation.rationale}</p>
          </div>

          {evaluation.strengths?.length > 0 && (
            <div className="detail-section">
              <h4>Strengths</h4>
              <ul>
                {evaluation.strengths.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
          )}

          {evaluation.concerns?.length > 0 && (
            <div className="detail-section">
              <h4>Concerns</h4>
              <ul>
                {evaluation.concerns.map((c, i) => <li key={i}>{c}</li>)}
              </ul>
            </div>
          )}

          {evaluation.position_changed && (
            <div className="detail-section deliberation-note">
              <h4>After Deliberation</h4>
              <p>Position: {evaluation.position_changed}</p>
              {evaluation.deliberation_response && <p>{evaluation.deliberation_response}</p>}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ApplicationDetail() {
  const { id } = useParams();
  const [application, setApplication] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('evaluations');
  const [decisionNotes, setDecisionNotes] = useState('');
  const [submittingDecision, setSubmittingDecision] = useState(false);

  useEffect(() => {
    loadApplication();
  }, [id]);

  const loadApplication = async () => {
    try {
      setLoading(true);
      const app = await api.getApplication(id);
      setApplication(app);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDecision = async (decision) => {
    try {
      setSubmittingDecision(true);
      await api.recordDecision(id, decision, decisionNotes);
      await loadApplication();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmittingDecision(false);
    }
  };

  if (loading) return <div className="loading">Loading application...</div>;
  if (error) return <div className="error">Error: {error}</div>;
  if (!application) return <div className="error">Application not found</div>;

  // API returns { application: {...}, evaluations: [...], decision: {...}, ... }
  const appData = application.application || application;
  const parsed = appData.parsed;
  const evaluations = application.evaluations || [];
  const decision = application.decision;
  const deliberation = application.deliberation;
  const createdAt = appData.created_at;

  return (
    <div className="application-detail">
      <Link to="/" className="back-link">← Back to Applications</Link>

      <div className="app-header">
        <div className="app-title-section">
          <h1>{parsed?.project_name || 'Untitled Application'}</h1>
          <div className="app-meta">
            <span>Team: {parsed?.team_name || 'Unknown'}</span>
            <span>Amount: {parsed?.requested_amount ? `$${parsed.requested_amount.toLocaleString()}` : 'N/A'}</span>
            <span>Submitted: {createdAt ? new Date(createdAt).toLocaleDateString() : 'N/A'}</span>
          </div>
        </div>

        {decision && (
          <div className={`decision-badge ${decision.primary_recommendation}`}>
            {decision.auto_executed ? 'Auto-' : ''}{decision.primary_recommendation}
            <span className="consensus">{Math.round(decision.consensus_strength * 100)}% consensus</span>
          </div>
        )}
      </div>

      <div className="tabs">
        <button className={activeTab === 'evaluations' ? 'active' : ''} onClick={() => setActiveTab('evaluations')}>
          Agent Evaluations
        </button>
        <button className={activeTab === 'parsed' ? 'active' : ''} onClick={() => setActiveTab('parsed')}>
          Parsed Data
        </button>
        <button className={activeTab === 'decision' ? 'active' : ''} onClick={() => setActiveTab('decision')}>
          Decision
        </button>
      </div>

      <div className="tab-content">
        {activeTab === 'evaluations' && (
          <div className="evaluations-tab">
            {evaluations?.length > 0 ? (
              <div className="agent-cards">
                {evaluations.map((e, i) => (
                  <AgentCard key={i} evaluation={e} />
                ))}
              </div>
            ) : (
              <p className="no-data">No evaluations yet</p>
            )}

            {deliberation && (
              <div className="deliberation-section">
                <h3>Deliberation</h3>
                <p>Agents reviewed each other's evaluations. {deliberation.position_changes || 0} position changes occurred.</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'parsed' && (
          <div className="parsed-tab">
            {parsed ? (
              <div className="parsed-sections">
                <div className="parsed-section">
                  <h3>Project Summary</h3>
                  <p>{parsed.project_summary || parsed.project_description || 'No summary available'}</p>
                </div>

                {parsed.team_members?.length > 0 && (
                  <div className="parsed-section">
                    <h3>Team Members</h3>
                    <ul>
                      {parsed.team_members.map((m, i) => (
                        <li key={i}>{m.name} - {m.role || 'Team Member'}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {parsed.budget_breakdown?.length > 0 && (
                  <div className="parsed-section">
                    <h3>Budget Breakdown</h3>
                    <table className="budget-table">
                      <thead>
                        <tr><th>Category</th><th>Amount</th><th>Justification</th></tr>
                      </thead>
                      <tbody>
                        {parsed.budget_breakdown.map((b, i) => (
                          <tr key={i}>
                            <td>{b.category}</td>
                            <td>${b.amount?.toLocaleString()}</td>
                            <td>{b.justification}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {parsed.milestones?.length > 0 && (
                  <div className="parsed-section">
                    <h3>Milestones</h3>
                    <div className="milestones">
                      {parsed.milestones.map((m, i) => (
                        <div key={i} className="milestone">
                          <div className="milestone-header">
                            <span className="milestone-num">M{i + 1}</span>
                            <span className="milestone-title">{m.title}</span>
                            <span className="milestone-timeline">{m.timeline}</span>
                          </div>
                          {m.deliverables?.length > 0 && (
                            <ul>
                              {m.deliverables.map((d, j) => <li key={j}>{d}</li>)}
                            </ul>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="no-data">Application not yet parsed</p>
            )}
          </div>
        )}

        {activeTab === 'decision' && (
          <div className="decision-tab">
            {decision ? (
              <div className="decision-details">
                <div className="decision-summary">
                  <h3>Council Decision</h3>
                  <p className="decision-result">
                    {decision.auto_executed ? 'Auto-' : 'Manual '}{decision.primary_recommendation}
                  </p>
                  <p>Consensus: {Math.round(decision.consensus_strength * 100)}%</p>
                  <p>Unanimous: {decision.unanimous ? 'Yes' : 'No'}</p>
                  {decision.routing_reason && <p>Routing: {decision.routing_reason}</p>}
                </div>

                {decision.votes?.length > 0 && (
                  <div className="votes-section">
                    <h3>Individual Votes</h3>
                    <div className="votes-grid">
                      {decision.votes.map((v, i) => (
                        <div key={i} className={`vote-card ${v.recommendation}`}>
                          <div className="vote-agent">{v.agent_id}</div>
                          <div className="vote-rec">{v.recommendation?.replace(/_/g, ' ')}</div>
                          <div className="vote-confidence">{v.confidence} confidence</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : decision === null && application.status === 'pending_review' ? (
              <div className="human-review">
                <h3>Human Review Required</h3>
                <p>This application requires your decision.</p>

                <textarea
                  placeholder="Add notes about your decision..."
                  value={decisionNotes}
                  onChange={(e) => setDecisionNotes(e.target.value)}
                />

                <div className="decision-buttons">
                  <button
                    className="btn btn-success"
                    onClick={() => handleDecision('approve')}
                    disabled={submittingDecision}
                  >
                    Approve
                  </button>
                  <button
                    className="btn btn-danger"
                    onClick={() => handleDecision('reject')}
                    disabled={submittingDecision}
                  >
                    Reject
                  </button>
                </div>
              </div>
            ) : (
              <p className="no-data">No decision yet - evaluation in progress</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
