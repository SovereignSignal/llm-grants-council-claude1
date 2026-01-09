import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import ApplicationsList from './pages/ApplicationsList';
import SubmitApplication from './pages/SubmitApplication';
import ApplicationDetail from './pages/ApplicationDetail';
import TeamsList from './pages/TeamsList';
import ObservationsList from './pages/ObservationsList';
import AgentsOverview from './pages/AgentsOverview';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<ApplicationsList />} />
          <Route path="submit" element={<SubmitApplication />} />
          <Route path="applications/:id" element={<ApplicationDetail />} />
          <Route path="teams" element={<TeamsList />} />
          <Route path="teams/:id" element={<TeamsList />} />
          <Route path="observations" element={<ObservationsList />} />
          <Route path="agents" element={<AgentsOverview />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
