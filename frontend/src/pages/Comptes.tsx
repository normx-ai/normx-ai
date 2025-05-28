import React, { useEffect, useState } from 'react';
import { comptesService } from '../services/api';

interface Compte {
  id: number;
  code: string;
  libelle: string;
  classe: string;
  type: string;
  ref: string;
  solde_normal: string;
  is_active: boolean;
}

function Comptes() {
  const [comptes, setComptes] = useState<Compte[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterClasse, setFilterClasse] = useState('');
  const [allComptes, setAllComptes] = useState<Compte[]>([]);

  // Charger tous les comptes au démarrage
  useEffect(() => {
    loadAllComptesAtStart();
  }, []);

  // Recharger quand la classe change
  useEffect(() => {
    if (filterClasse !== '') {
      loadComptes();
    } else if (allComptes.length > 0) {
      setComptes(allComptes);
      setTotalCount(allComptes.length);
    }
  }, [filterClasse]);

  const loadAllComptesAtStart = async () => {
    try {
      setLoading(true);
      const response = await comptesService.getAll({ page_size: 2000 });

      if (response.data.results) {
        setAllComptes(response.data.results);
        setComptes(response.data.results);
        setTotalCount(response.data.count);
      }
    } catch (err) {
      setError('Erreur lors du chargement des comptes');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadComptes = async () => {
    try {
      setLoading(true);

      if (filterClasse) {
        const params: any = {
          classe: filterClasse,
          page_size: 2000
        };

        const response = await comptesService.getAll(params);

        if (response.data.results) {
          setComptes(response.data.results);
          setTotalCount(response.data.results.length);
        }
      }

      setError(null);
    } catch (err) {
      setError('Erreur lors du chargement des comptes');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadAllComptes = async () => {
    await loadAllComptesAtStart();
  };

  // Filtrer les comptes localement
  const filteredComptes = comptes.filter(compte => {
    if (!searchTerm) return true;

    const searchLower = searchTerm.toLowerCase();

    // Support du wildcard *
    if (searchTerm.includes('*')) {
      // Remplacer * par .* pour la regex, mais traiter différemment selon la position
      let pattern = searchTerm;

      // Si le pattern commence par *, on cherche n'importe où
      // Si le pattern finit par *, on cherche au début
      // Si * est au milieu, on fait une recherche avec pattern

      if (searchTerm.startsWith('*') && searchTerm.endsWith('*')) {
        // *text* - chercher n'importe où
        const searchText = searchTerm.slice(1, -1).toLowerCase();
        return compte.code.toLowerCase().includes(searchText) ||
               compte.libelle.toLowerCase().includes(searchText);
      } else if (searchTerm.endsWith('*')) {
        // text* - doit commencer par
        const searchText = searchTerm.slice(0, -1).toLowerCase();
        return compte.code.toLowerCase().startsWith(searchText) ||
               compte.libelle.toLowerCase().startsWith(searchText);
      } else if (searchTerm.startsWith('*')) {
        // *text - doit finir par
        const searchText = searchTerm.slice(1).toLowerCase();
        return compte.code.toLowerCase().endsWith(searchText) ||
               compte.libelle.toLowerCase().endsWith(searchText);
      } else {
        // Wildcard au milieu - utiliser regex
        pattern = pattern
          .split('*')
          .map(part => part.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
          .join('.*');

        try {
          const regex = new RegExp(`^${pattern}$`, 'i');
          return regex.test(compte.code) || regex.test(compte.libelle);
        } catch (e) {
          return compte.code.toLowerCase().includes(searchLower) ||
                 compte.libelle.toLowerCase().includes(searchLower);
        }
      }
    }

    return compte.code.toLowerCase().includes(searchLower) ||
           compte.libelle.toLowerCase().includes(searchLower);
  });

  const getSoldeNormalDisplay = (solde: string) => {
    switch(solde) {
      case 'debiteur': return 'Débiteur';
      case 'crediteur': return 'Créditeur';
      case 'variable': return 'Variable';
      default: return solde;
    }
  };

  const getTypeDisplay = (type: string) => {
    switch(type) {
      case 'actif': return 'Actif';
      case 'passif': return 'Passif';
      case 'charge': return 'Charge';
      case 'produit': return 'Produit';
      case 'actif_ou_passif': return 'Actif/Passif';
      default: return type;
    }
  };

  if (loading) return <div>Chargement...</div>;
  if (error) return <div style={{ color: 'red' }}>{error}</div>;

  return (
    <div style={{ padding: '20px' }}>
      <h2>Plan Comptable OHADA ({totalCount} comptes au total)</h2>

      {filterClasse && (
        <div style={{ marginBottom: '10px', padding: '10px', backgroundColor: '#e3f2fd', borderRadius: '4px' }}>
          Filtre actif : Classe {filterClasse} - {comptes.length} comptes affichés
        </div>
      )}

      <div style={{ marginBottom: '20px', display: 'flex', gap: '10px', alignItems: 'center' }}>
        <input
          type="text"
          placeholder="Rechercher par code ou libellé..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{
            padding: '8px 12px',
            border: '1px solid #ddd',
            borderRadius: '4px',
            width: '300px'
          }}
        />

        {searchTerm && (
          <span style={{
            padding: '8px',
            color: '#666',
            fontSize: '14px'
          }}>
            {filteredComptes.length} compte(s) trouvé(s)
          </span>
        )}

        <select
          value={filterClasse}
          onChange={(e) => setFilterClasse(e.target.value)}
          style={{
            padding: '8px 12px',
            border: '1px solid #ddd',
            borderRadius: '4px'
          }}
        >
          <option value="">Toutes les classes</option>
          <option value="1">Classe 1 - Capitaux</option>
          <option value="2">Classe 2 - Immobilisations</option>
          <option value="3">Classe 3 - Stocks</option>
          <option value="4">Classe 4 - Tiers</option>
          <option value="5">Classe 5 - Trésorerie</option>
          <option value="6">Classe 6 - Charges</option>
          <option value="7">Classe 7 - Produits</option>
          <option value="8">Classe 8 - Spéciaux</option>
        </select>

        <button
          onClick={loadAllComptes}
          style={{
            padding: '8px 16px',
            backgroundColor: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Recharger tous les comptes
        </button>
      </div>

      <div style={{ overflowX: 'auto', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', backgroundColor: 'white' }}>
          <thead>
            <tr style={{ backgroundColor: '#f8f9fa' }}>
              <th style={thStyle}>Code</th>
              <th style={thStyle}>Libellé</th>
              <th style={thStyle}>Classe</th>
              <th style={thStyle}>Type</th>
              <th style={thStyle}>Ref</th>
              <th style={thStyle}>Solde Normal</th>
              <th style={thStyle}>Statut</th>
            </tr>
          </thead>
          <tbody>
            {filteredComptes.map((compte, index) => (
              <tr
                key={compte.id}
                style={{
                  borderBottom: '1px solid #eee',
                  backgroundColor: index % 2 === 0 ? 'white' : '#f8f9fa'
                }}
              >
                <td style={tdStyle}>{compte.code}</td>
                <td style={tdStyle}>{compte.libelle}</td>
                <td style={tdStyleCenter}>{compte.classe}</td>
                <td style={tdStyle}>{getTypeDisplay(compte.type)}</td>
                <td style={tdStyleCenter}>{compte.ref || '-'}</td>
                <td style={tdStyle}>{getSoldeNormalDisplay(compte.solde_normal)}</td>
                <td style={tdStyleCenter}>
                  <span style={{
                    padding: '2px 8px',
                    borderRadius: '12px',
                    fontSize: '12px',
                    backgroundColor: compte.is_active ? '#28a745' : '#dc3545',
                    color: 'white'
                  }}>
                    {compte.is_active ? 'Actif' : 'Inactif'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: '10px', color: '#666', fontSize: '14px' }}>
        {searchTerm ? (
          <>Affichage de {filteredComptes.length} compte(s) sur {comptes.length}
          {searchTerm.includes('*') && <em> (recherche avec wildcard *)</em>}</>
        ) : (
          <>Affichage de {comptes.length} comptes{filterClasse && ` de la classe ${filterClasse}`}</>
        )}
      </div>
    </div>
  );
}

// Styles
const thStyle: React.CSSProperties = {
  padding: '12px',
  textAlign: 'left',
  borderBottom: '2px solid #dee2e6',
  fontWeight: '600',
  color: '#495057'
};

const tdStyle: React.CSSProperties = {
  padding: '10px 12px',
  color: '#212529'
};

const tdStyleCenter: React.CSSProperties = {
  ...tdStyle,
  textAlign: 'center'
};

export default Comptes;