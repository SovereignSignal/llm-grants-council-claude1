import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import './TeamsList.css';

export default function TeamsList() {
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadTeams();
  }, []);

  const loadTeams = async () => {
    try {
      setLoading(true);
      const data = await api.listTeams();
      setTeams(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const filteredTeams = teams.filter(t =>
    t.name?.toLowerCase().includes(search.toLowerCase()) ||
    t.aliases?.some(a => a.toLowerCase().includes(search.toLowerCase()))
  );

  if (loading) return <div className="loading">Loading teams...</div>;
  if (error) return <div className="error">Error: {error}</div>;

  return (
    <div className="teams-list">
      <div className="page-header">
        <div>
          <h1>Teams</h1>
          <p className="subtitle">Team profiles and grant history</p>
        </div>
      </div>

      <div className="search-bar">
        <input
          type="text"
          placeholder="Search teams..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {filteredTeams.length === 0 ? (
        <div className="empty-state">
          <h3>No teams found</h3>
          <p>Teams are created automatically when applications are submitted.</p>
        </div>
      ) : (
        <div className="teams-grid">
          {filteredTeams.map(team => (
            <Link to={`/teams/${team.id}`} key={team.id} className="team-card">
              <div className="team-name">{team.name}</div>
              <div className="team-stats">
                <div className="stat">
                  <span className="stat-value">{team.grants_received || 0}</span>
                  <span className="stat-label">Grants</span>
                </div>
                <div className="stat">
                  <span className="stat-value">{team.grants_completed || 0}</span>
                  <span className="stat-label">Completed</span>
                </div>
                <div className="stat">
                  <span className="stat-value">{team.reputation_score?.toFixed(1) || '-'}</span>
                  <span className="stat-label">Score</span>
                </div>
              </div>
              {team.members?.length > 0 && (
                <div className="team-members">
                  {team.members.slice(0, 3).map((m, i) => (
                    <span key={i} className="member">{m.name}</span>
                  ))}
                  {team.members.length > 3 && <span className="member more">+{team.members.length - 3}</span>}
                </div>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
