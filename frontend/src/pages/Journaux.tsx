// frontend/src/pages/Journaux.tsx
import React, { useEffect, useState } from 'react';
import { journauxService } from '../services/api';

interface CompteContrepartie {
  id: number;
  code: string;
  libelle: string;
  compte_complet: string;
}

interface Journal {
  id: number;
  code: string;
  libelle: string;
  type: string;
  type_display: string;
  compte_contrepartie: number | null;
  compte_contrepartie_detail: CompteContrepartie | null;
  is_active: boolean;
  nb_ecritures: number;
  derniere_utilisation: string | null;
  created_at: string;
  updated_at: string;
}

function Journaux() {
  const [journaux, setJournaux] = useState<Journal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [modalType, setModalType] = useState<'create' | 'edit' | 'view'>('create');
  const [selectedJournal, setSelectedJournal] = useState<Journal | null>(null);

  useEffect(() => {
    loadJournaux();
  }, []);

  const loadJournaux = async () => {
    try {
      setLoading(true);
      const response = await journauxService.getAll({ page_size: 100 });

      if (response.data.results) {
        setJournaux(response.data.results);
      }
      setError(null);
    } catch (err) {
      setError('Erreur lors du chargement des journaux');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Gestion des actions
  const handleCreate = () => {
    setSelectedJournal(null);
    setModalType('create');
    setShowModal(true);
  };

  const handleEdit = (journal: Journal) => {
    setSelectedJournal(journal);
    setModalType('edit');
    setShowModal(true);
  };

  const handleView = (journal: Journal) => {
    setSelectedJournal(journal);
    setModalType('view');
    setShowModal(true);
  };

  const handleDelete = async (journal: Journal) => {
    if (journal.nb_ecritures > 0) {
      alert('Impossible de supprimer un journal contenant des écritures');
      return;
    }

    if (confirm(`Êtes-vous sûr de vouloir supprimer le journal ${journal.code} ?`)) {
      try {
        await journauxService.delete(journal.id);
        alert('Journal supprimé avec succès');
        loadJournaux();
      } catch (err) {
        alert('Erreur lors de la suppression du journal');
        console.error(err);
      }
    }
  };

  const handleSave = async (data: any) => {
    try {
      if (modalType === 'edit' && selectedJournal) {
        await journauxService.update(selectedJournal.id, data);
        alert('Journal modifié avec succès');
      } else if (modalType === 'create') {
        await journauxService.create(data);
        alert('Journal créé avec succès');
      }
      setShowModal(false);
      loadJournaux();
    } catch (err) {
      alert('Erreur lors de l\'enregistrement');
      console.error(err);
    }
  };

  // Filtrer les journaux par type
  const filteredJournaux = journaux.filter(journal => {
    if (!filterType) return true;
    return journal.type === filterType;
  });

  // Types de journaux pour le filtre
  const typesJournaux = [
    { code: '', label: 'Tous les types' },
    { code: 'AC', label: 'Achats' },
    { code: 'VT', label: 'Ventes' },
    { code: 'BQ', label: 'Banque' },
    { code: 'CA', label: 'Caisse' },
    { code: 'PA', label: 'Paie' },
    { code: 'FI', label: 'Fiscal' },
    { code: 'SO', label: 'Social' },
    { code: 'ST', label: 'Stocks' },
    { code: 'IM', label: 'Immobilisations' },
    { code: 'PR', label: 'Provisions' },
    { code: 'AN', label: 'À nouveaux' },
    { code: 'CL', label: 'Clôture' },
    { code: 'OD', label: 'Opérations Diverses' },
    { code: 'EX', label: 'Extra-comptable' },
  ];

  const getTypeColor = (type: string) => {
    const colors: { [key: string]: string } = {
      'AC': '#e74c3c',  // Rouge - Achats
      'VT': '#27ae60',  // Vert - Ventes
      'BQ': '#3498db',  // Bleu - Banque
      'CA': '#f39c12',  // Orange - Caisse
      'PA': '#9b59b6',  // Violet - Paie
      'FI': '#1abc9c',  // Turquoise - Fiscal
      'SO': '#34495e',  // Gris foncé - Social
      'OD': '#95a5a6',  // Gris - Opérations diverses
    };
    return colors[type] || '#7f8c8d';
  };

  if (loading) return <div>Chargement...</div>;
  if (error) return <div style={{ color: 'red' }}>{error}</div>;

  return (
    <div style={{ padding: '20px' }}>
      <h2>Journaux Comptables ({journaux.length} journaux)</h2>

      <div style={{ marginBottom: '20px', display: 'flex', gap: '10px', alignItems: 'center' }}>
        <button
          onClick={handleCreate}
          style={{
            padding: '8px 16px',
            backgroundColor: '#28a745',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontWeight: 'bold'
          }}
        >
          + Nouveau Journal
        </button>

        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          style={{
            padding: '8px 12px',
            border: '1px solid #ddd',
            borderRadius: '4px',
            minWidth: '200px'
          }}
        >
          {typesJournaux.map(type => (
            <option key={type.code} value={type.code}>
              {type.label}
            </option>
          ))}
        </select>

        <button
          onClick={loadJournaux}
          style={{
            padding: '8px 16px',
            backgroundColor: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Actualiser
        </button>
      </div>

      <div style={{ overflowX: 'auto', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', backgroundColor: 'white' }}>
          <thead>
            <tr style={{ backgroundColor: '#f8f9fa' }}>
              <th style={thStyle}>Code</th>
              <th style={thStyle}>Libellé</th>
              <th style={thStyle}>Type</th>
              <th style={thStyle}>Compte Contrepartie</th>
              <th style={thStyle}>Écritures</th>
              <th style={thStyle}>Dernière Utilisation</th>
              <th style={thStyle}>Statut</th>
              <th style={thStyle}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredJournaux.map((journal, index) => (
              <tr
                key={journal.id}
                style={{
                  borderBottom: '1px solid #eee',
                  backgroundColor: index % 2 === 0 ? 'white' : '#f8f9fa'
                }}
              >
                <td style={{ ...tdStyle, fontWeight: 'bold' }}>
                  <span style={{ fontFamily: 'monospace' }}>{journal.code}</span>
                </td>
                <td style={tdStyle}>{journal.libelle}</td>
                <td style={tdStyleCenter}>
                  <span style={{
                    padding: '4px 8px',
                    borderRadius: '4px',
                    fontSize: '12px',
                    backgroundColor: getTypeColor(journal.type) + '20',
                    color: getTypeColor(journal.type),
                    fontWeight: '500'
                  }}>
                    {journal.type_display}
                  </span>
                </td>
                <td style={tdStyle}>
                  {journal.compte_contrepartie_detail ? (
                    <span style={{ fontSize: '13px', color: '#666' }}>
                      {journal.compte_contrepartie_detail.code} - {journal.compte_contrepartie_detail.libelle}
                    </span>
                  ) : (
                    <span style={{ color: '#999' }}>-</span>
                  )}
                </td>
                <td style={tdStyleCenter}>
                  {journal.nb_ecritures > 0 ? (
                    <span style={{
                      padding: '2px 6px',
                      borderRadius: '12px',
                      fontSize: '12px',
                      backgroundColor: '#e3f2fd',
                      color: '#1976d2'
                    }}>
                      {journal.nb_ecritures}
                    </span>
                  ) : (
                    <span style={{ color: '#999' }}>0</span>
                  )}
                </td>
                <td style={tdStyleCenter}>
                  {journal.derniere_utilisation ? (
                    <span style={{ fontSize: '13px' }}>
                      {new Date(journal.derniere_utilisation).toLocaleDateString('fr-FR')}
                    </span>
                  ) : (
                    <span style={{ color: '#999' }}>-</span>
                  )}
                </td>
                <td style={tdStyleCenter}>
                  <span style={{
                    padding: '2px 8px',
                    borderRadius: '12px',
                    fontSize: '12px',
                    backgroundColor: journal.is_active ? '#28a745' : '#dc3545',
                    color: 'white'
                  }}>
                    {journal.is_active ? 'Actif' : 'Inactif'}
                  </span>
                </td>
                <td style={tdStyleCenter}>
                  <div style={{ display: 'flex', gap: '5px', justifyContent: 'center' }}>
                    <button
                      onClick={() => handleEdit(journal)}
                      style={{
                        padding: '4px 8px',
                        fontSize: '12px',
                        backgroundColor: '#007bff',
                        color: 'white',
                        border: 'none',
                        borderRadius: '3px',
                        cursor: 'pointer'
                      }}
                      title="Modifier"
                    >
                      ✏️
                    </button>
                    <button
                      onClick={() => handleView(journal)}
                      style={{
                        padding: '4px 8px',
                        fontSize: '12px',
                        backgroundColor: '#28a745',
                        color: 'white',
                        border: 'none',
                        borderRadius: '3px',
                        cursor: 'pointer'
                      }}
                      title="Voir détails"
                    >
                      👁️
                    </button>
                    <button
                      onClick={() => handleDelete(journal)}
                      style={{
                        padding: '4px 8px',
                        fontSize: '12px',
                        backgroundColor: '#dc3545',
                        color: 'white',
                        border: 'none',
                        borderRadius: '3px',
                        cursor: 'pointer'
                      }}
                      title="Supprimer"
                      disabled={journal.nb_ecritures > 0}
                    >
                      🗑️
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#f8f9fa', borderRadius: '4px' }}>
        <h3 style={{ marginTop: 0, marginBottom: '10px' }}>Légende des types de journaux</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '8px' }}>
          {typesJournaux.filter(t => t.code).map(type => (
            <div key={type.code} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{
                width: '12px',
                height: '12px',
                borderRadius: '2px',
                backgroundColor: getTypeColor(type.code)
              }}></div>
              <span style={{ fontSize: '13px' }}>
                <strong>{type.code}</strong> - {type.label}
              </span>
            </div>
          ))}
        </div>
      </div>

      {filterType && (
        <div style={{ marginTop: '10px', color: '#666', fontSize: '14px' }}>
          Affichage de {filteredJournaux.length} journal(aux) de type "{typesJournaux.find(t => t.code === filterType)?.label}"
        </div>
      )}

      {/* Modal pour créer/éditer/voir */}
      {showModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white',
            padding: '20px',
            borderRadius: '8px',
            width: '500px',
            maxHeight: '80vh',
            overflowY: 'auto'
          }}>
            <h3>
              {modalType === 'create' ? 'Nouveau Journal' :
               modalType === 'edit' ? 'Modifier Journal' :
               'Détails du Journal'}
            </h3>

            {modalType === 'view' ? (
              <div>
                <p><strong>Code:</strong> {selectedJournal?.code}</p>
                <p><strong>Libellé:</strong> {selectedJournal?.libelle}</p>
                <p><strong>Type:</strong> {selectedJournal?.type_display}</p>
                <p><strong>Compte contrepartie:</strong> {
                  selectedJournal?.compte_contrepartie_detail ?
                  `${selectedJournal.compte_contrepartie_detail.code} - ${selectedJournal.compte_contrepartie_detail.libelle}` :
                  'Aucun'
                }</p>
                <p><strong>Nombre d'écritures:</strong> {selectedJournal?.nb_ecritures || 0}</p>
                <p><strong>Statut:</strong> {selectedJournal?.is_active ? 'Actif' : 'Inactif'}</p>
              </div>
            ) : (
              <form onSubmit={(e) => {
                e.preventDefault();
                const formData = new FormData(e.currentTarget);
                const data = {
                  code: formData.get('code'),
                  libelle: formData.get('libelle'),
                  type: formData.get('type'),
                  is_active: formData.get('is_active') === 'true'
                };
                handleSave(data);
              }}>
                <div style={{ marginBottom: '15px' }}>
                  <label style={{ display: 'block', marginBottom: '5px' }}>Code:</label>
                  <input
                    name="code"
                    type="text"
                    defaultValue={selectedJournal?.code || ''}
                    required
                    style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
                  />
                </div>

                <div style={{ marginBottom: '15px' }}>
                  <label style={{ display: 'block', marginBottom: '5px' }}>Libellé:</label>
                  <input
                    name="libelle"
                    type="text"
                    defaultValue={selectedJournal?.libelle || ''}
                    required
                    style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
                  />
                </div>

                <div style={{ marginBottom: '15px' }}>
                  <label style={{ display: 'block', marginBottom: '5px' }}>Type:</label>
                  <select
                    name="type"
                    defaultValue={selectedJournal?.type || ''}
                    required
                    style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
                  >
                    <option value="">Sélectionner un type</option>
                    {typesJournaux.filter(t => t.code).map(type => (
                      <option key={type.code} value={type.code}>
                        {type.code} - {type.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div style={{ marginBottom: '15px' }}>
                  <label style={{ display: 'block', marginBottom: '5px' }}>Statut:</label>
                  <select
                    name="is_active"
                    defaultValue={selectedJournal?.is_active ? 'true' : 'false'}
                    style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
                  >
                    <option value="true">Actif</option>
                    <option value="false">Inactif</option>
                  </select>
                </div>

                <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    style={{
                      padding: '8px 16px',
                      backgroundColor: '#6c757d',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer'
                    }}
                  >
                    Annuler
                  </button>
                  <button
                    type="submit"
                    style={{
                      padding: '8px 16px',
                      backgroundColor: '#007bff',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer'
                    }}
                  >
                    {modalType === 'create' ? 'Créer' : 'Modifier'}
                  </button>
                </div>
              </form>
            )}

            {modalType === 'view' && (
              <div style={{ marginTop: '20px', textAlign: 'right' }}>
                <button
                  onClick={() => setShowModal(false)}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: '#6c757d',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Fermer
                </button>
              </div>
            )}
          </div>
        </div>
      )}
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

export default Journaux;