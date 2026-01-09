import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import './ApplicationsList.css';

function StatusBadge({ status, decision }) {
  let label = status;
  let className = 'badge';

  if (decision) {
    if (decision.auto_executed) {
      label = decision.primary_recommendation === 'approve' ? 'Auto-Approved' : 'Auto-Rejected';
      className += decision.primary_recommendation === 'approve' ? ' badge-success' : ' badge-danger';
    } else if (decision.requires_human_review) {
      label = 'Needs Review';
      className += ' badge-warning';
    } else {
      label = decision.primary_recommendation === 'approve' ? 'Approved' : 'Rejected';
      className += decision.primary_recommendation === 'approve' ? ' badge-success' : ' badge-danger';
    }
  } else {
    className += ' badge-neutral';
  }

  return <span className={className}>{label}</span>;
}

export default function ApplicationsList() {
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadApplications();
  }, []);

  const loadApplications = async () => {
    try {
      setLoading(true);
      const apps = await api.listApplications();
      setApplications(apps);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const stats = {
    total: applications.length,
    autoApproved: applications.filter(a => a.decision?.auto_executed && a.decision?.primary_recommendation === 'approve').length,
    needsReview: applications.filter(a => a.decision?.requires_human_review).length,
  };

  if (loading) {
    return <div className="loading">Loading applications...</div>;
  }

  if (error) {
    return <div className="error">Error: {error}</div>;
  }

  return (
    <div className="applications-list">
      <div className="page-header">
        <div>
          <h1>Grant Applications</h1>
          <p className="subtitle">Review and manage grant applications</p>
        </div>
        <Link to="/submit" className="btn btn-primary">
          + New Application
        </Link>
      </div>

      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-value">{stats.total}</div>
          <div className="stat-label">Total Applications</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.autoApproved}</div>
          <div className="stat-label">Auto-Approved</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.needsReview}</div>
          <div className="stat-label">Needs Review</div>
        </div>
      </div>

      {applications.length === 0 ? (
        <div className="empty-state">
          <h3>No applications yet</h3>
          <p>Submit your first grant application to get started.</p>
          <Link to="/submit" className="btn btn-primary">Submit Application</Link>
        </div>
      ) : (
        <div className="applications-table">
          <table>
            <thead>
              <tr>
                <th>Application</th>
                <th>Team</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Consensus</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {applications.map(app => (
                <tr key={app.id}>
                  <td>
                    <Link to={`/applications/${app.id}`} className="app-link">
                      {app.parsed?.project_name || 'Untitled Application'}
                    </Link>
                  </td>
                  <td>{app.parsed?.team_name || '-'}</td>
                  <td>{app.parsed?.requested_amount ? `$${app.parsed.requested_amount.toLocaleString()}` : '-'}</td>
                  <td><StatusBadge status={app.status} decision={app.decision} /></td>
                  <td>
                    {app.decision?.consensus_strength
                      ? `${Math.round(app.decision.consensus_strength * 100)}%`
                      : '-'}
                  </td>
                  <td>{new Date(app.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
