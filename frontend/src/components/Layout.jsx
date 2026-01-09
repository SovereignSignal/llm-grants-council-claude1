import { NavLink, Outlet } from 'react-router-dom';
import './Layout.css';

export default function Layout() {
  return (
    <div className="layout">
      <nav className="nav">
        <div className="nav-brand">
          <span className="nav-logo">AGC</span>
          <span className="nav-title">Grants Council</span>
        </div>
        <div className="nav-links">
          <NavLink to="/" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'} end>
            Applications
          </NavLink>
          <NavLink to="/submit" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            Submit
          </NavLink>
          <NavLink to="/teams" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            Teams
          </NavLink>
          <NavLink to="/observations" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            Observations
          </NavLink>
          <NavLink to="/agents" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            Agents
          </NavLink>
        </div>
      </nav>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
