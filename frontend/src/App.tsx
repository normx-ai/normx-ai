import React from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import Comptes from './pages/Comptes'
import Journaux from './pages/Journaux'
import Exercices from './pages/Exercices'
import SaisieEcritures from './pages/SaisieEcritures'

// Pages temporaires
const Dashboard = () => <div><h2>Tableau de bord</h2></div>
const Ecritures = () => <div><h2>Écritures Comptables</h2></div>

function App() {
  return (
    <Router>
      <div style={{ display: 'flex', minHeight: '100vh' }}>
        {/* Menu latéral */}
        <nav style={{
          width: '250px',
          backgroundColor: '#f5f5f5',
          padding: '20px'
        }}>
          <h1>NORMX AI</h1>
          <ul style={{ listStyle: 'none', padding: 0 }}>
            <li style={{ marginBottom: '10px' }}>
              <Link to="/">Tableau de bord</Link>
            </li>
            <li style={{ marginBottom: '10px' }}>
              <Link to="/comptes">Plan Comptable</Link>
            </li>
            <li style={{ marginBottom: '10px' }}>
              <Link to="/ecritures">Écritures</Link>
            </li>
            <li style={{ marginBottom: '10px' }}>
              <Link to="/saisie-ecritures">Saisie Écritures</Link>
            </li>
            <li style={{ marginBottom: '10px' }}>
              <Link to="/journaux">Journaux</Link>
            </li>
            <li style={{ marginBottom: '10px' }}>
              <Link to="/exercices">Exercices</Link>
            </li>
          </ul>
        </nav>

        {/* Contenu principal */}
        <main style={{ flex: 1, padding: '20px' }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/comptes" element={<Comptes />} />
            <Route path="/ecritures" element={<Ecritures />} />
            <Route path="/saisie-ecritures" element={<SaisieEcritures />} />
            <Route path="/journaux" element={<Journaux />} />
            <Route path="/exercices" element={<Exercices />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App