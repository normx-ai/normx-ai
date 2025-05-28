// frontend/src/pages/Exercices.tsx
import React, { useEffect, useState } from 'react';
import { exercicesService } from '../services/api';

interface Periode {
  id: number;
  numero: number;
  date_debut: string;
  date_fin: string;
  periode_complete: string;
  statut: string;
}

interface Exercice {
  id: number;
  code: string;
  libelle: string;
  date_debut: string;
  date_fin: string;
  statut: string;
  date_cloture_provisoire: string | null;
  date_cloture_definitive: string | null;
  is_premier_exercice: boolean;
  report_a_nouveau_genere: boolean;
  periodes: Periode[];
  duree_jours: number;
  duree_mois: number;
  progression_pourcent: number;
  nb_periodes_cloturees: number;
  nb_ecritures_total: number;
  peut_etre_cloture: boolean;
  statut_display: string;
  created_at: string;
  updated_at: string;
}

function Exercices() {
  const [exercices, setExercices] = useState<Exercice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [modalType, setModalType] = useState<'create' | 'edit' | 'view' | 'periodes'>('create');
  const [selectedExercice, setSelectedExercice] = useState<Exercice | null>(null);
  const [showPeriodesDetail, setShowPeriodesDetail] = useState<number | null>(null);

  useEffect(() => {
    loadExercices();
  }, []);

  const loadExercices = async () => {
    try {
      setLoading(true);
      const response = await exercicesService.getAll({ page_size: 100 });

      if (response.data.results) {
        setExercices(response.data.results);
      }
      setError(null);
    } catch (err) {
      setError('Erreur lors du chargement des exercices');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Gestion des actions
  const handleCreate = () => {
    setSelectedExercice(null);
    setModalType('create');
    setShowModal(true);
  };

  const handleEdit = (exercice: Exercice) => {
    setSelectedExercice(exercice);
    setModalType('edit');
    setShowModal(true);
  };

  const handleView = (exercice: Exercice) => {
    setSelectedExercice(exercice);
    setModalType('view');
    setShowModal(true);
  };

  const handleViewPeriodes = (exercice: Exercice) => {
    setSelectedExercice(exercice);
    setModalType('periodes');
    setShowModal(true);
  };

  const handleOuvrir = async (exercice: Exercice) => {
    if (confirm(`Êtes-vous sûr de vouloir ouvrir l'exercice ${exercice.libelle} ?`)) {
      try {
        await exercicesService.ouvrir(exercice.id);
        alert('Exercice ouvert avec succès');
        loadExercices();
      } catch (err) {
        alert('Erreur lors de l\'ouverture de l\'exercice');
        console.error(err);
      }
    }
  };

  const handleCloturer = async (exercice: Exercice) => {
    if (!exercice.peut_etre_cloture) {
      alert('Cet exercice ne peut pas être clôturé. Vérifiez que toutes les périodes sont clôturées.');
      return;
    }

    if (confirm(`Êtes-vous sûr de vouloir clôturer définitivement l'exercice ${exercice.libelle} ?`)) {
      try {
        await exercicesService.cloturer(exercice.id);
        alert('Exercice clôturé avec succès');
        loadExercices();
      } catch (err) {
        alert('Erreur lors de la clôture de l\'exercice');
        console.error(err);
      }
    }
  };

  const handleDelete = async (exercice: Exercice) => {
    if (exercice.statut !== 'PREPARATION') {
      alert('Seul un exercice en préparation peut être supprimé');
      return;
    }

    if (exercice.nb_ecritures_total > 0) {
      alert('Impossible de supprimer un exercice contenant des écritures');
      return;
    }

    if (confirm(`Êtes-vous sûr de vouloir supprimer l'exercice ${exercice.libelle} ?`)) {
      try {
        await exercicesService.delete(exercice.id);
        alert('Exercice supprimé avec succès');
        loadExercices();
      } catch (err) {
        alert('Erreur lors de la suppression');
        console.error(err);
      }
    }
  };

  const handleGenererPeriodes = async (exercice: Exercice) => {
    if (confirm(`Voulez-vous générer toutes les périodes mensuelles pour l'exercice ${exercice.libelle} ?`)) {
      try {
        const response = await exercicesService.genererPeriodes(exercice.id);
        alert(response.data.message || 'Périodes générées avec succès');
        loadExercices();
      } catch (err: any) {
        alert(err.response?.data?.error || 'Erreur lors de la génération des périodes');
        console.error(err);
      }
    }
  };

  const handleSave = async (data: any) => {
    try {
      if (modalType === 'edit' && selectedExercice) {
        await exercicesService.update(selectedExercice.id, data);
        alert('Exercice modifié avec succès');
      } else if (modalType === 'create') {
        await exercicesService.create(data);
        alert('Exercice créé avec succès');
      }
      setShowModal(false);
      loadExercices();
    } catch (err: any) {
      alert(err.response?.data?.error || 'Erreur lors de l\'enregistrement');
      console.error(err);
    }
  };

  const getStatutColor = (statut: string) => {
    switch (statut) {
      case 'OUVERT': return '#28a745';
      case 'CLOTURE': return '#dc3545';
      case 'PREPARATION': return '#ffc107';
      default: return '#6c757d';
    }
  };

  const getPeriodeStatutColor = (statut: string) => {
    switch (statut) {
      case 'OUVERTE': return '#28a745';
      case 'CLOTUREE': return '#dc3545';
      case 'VERROUILLEE': return '#6c757d';
      default: return '#6c757d';
    }
  };

  if (loading) return <div>Chargement...</div>;
  if (error) return <div style={{ color: 'red' }}>{error}</div>;

  return (
    <div style={{ padding: '20px' }}>
      <h2>Exercices Comptables</h2>

      <div style={{ marginBottom: '20px' }}>
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
          + Nouvel Exercice
        </button>
      </div>

      <div style={{ display: 'grid', gap: '20px' }}>
        {exercices.map(exercice => (
          <div
            key={exercice.id}
            style={{
              backgroundColor: 'white',
              border: '1px solid #ddd',
              borderRadius: '8px',
              padding: '20px',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ flex: 1 }}>
                <h3 style={{ margin: 0, marginBottom: '10px' }}>
                  {exercice.libelle}
                  {exercice.is_premier_exercice && (
                    <span style={{
                      marginLeft: '10px',
                      fontSize: '12px',
                      backgroundColor: '#007bff',
                      color: 'white',
                      padding: '2px 6px',
                      borderRadius: '3px'
                    }}>
                      Premier exercice
                    </span>
                  )}
                </h3>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '10px', marginBottom: '15px' }}>
                  <div>
                    <strong>Code:</strong> {exercice.code}
                  </div>
                  <div>
                    <strong>Période:</strong> {new Date(exercice.date_debut).toLocaleDateString('fr-FR')} - {new Date(exercice.date_fin).toLocaleDateString('fr-FR')}
                  </div>
                  <div>
                    <strong>Durée:</strong> {exercice.duree_mois} mois ({exercice.duree_jours} jours)
                  </div>
                  <div>
                    <strong>Statut:</strong>{' '}
                    <span style={{
                      padding: '2px 8px',
                      borderRadius: '4px',
                      fontSize: '12px',
                      backgroundColor: getStatutColor(exercice.statut) + '20',
                      color: getStatutColor(exercice.statut),
                      fontWeight: 'bold'
                    }}>
                      {exercice.statut_display}
                    </span>
                  </div>
                </div>

                {/* Barre de progression */}
                {exercice.statut === 'OUVERT' && (
                  <div style={{ marginBottom: '15px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
                      <span style={{ fontSize: '14px' }}>Progression</span>
                      <span style={{ fontSize: '14px', fontWeight: 'bold' }}>{exercice.progression_pourcent}%</span>
                    </div>
                    <div style={{
                      height: '8px',
                      backgroundColor: '#e9ecef',
                      borderRadius: '4px',
                      overflow: 'hidden'
                    }}>
                      <div style={{
                        height: '100%',
                        width: `${exercice.progression_pourcent}%`,
                        backgroundColor: '#007bff',
                        transition: 'width 0.3s ease'
                      }} />
                    </div>
                  </div>
                )}

                {/* Statistiques */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '10px' }}>
                  <div style={{ textAlign: 'center', padding: '10px', backgroundColor: '#f8f9fa', borderRadius: '4px' }}>
                    <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#007bff' }}>
                      {exercice.periodes.length}
                    </div>
                    <div style={{ fontSize: '12px', color: '#666' }}>Périodes</div>
                  </div>
                  <div style={{ textAlign: 'center', padding: '10px', backgroundColor: '#f8f9fa', borderRadius: '4px' }}>
                    <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#28a745' }}>
                      {exercice.nb_periodes_cloturees}
                    </div>
                    <div style={{ fontSize: '12px', color: '#666' }}>Périodes clôturées</div>
                  </div>
                  <div style={{ textAlign: 'center', padding: '10px', backgroundColor: '#f8f9fa', borderRadius: '4px' }}>
                    <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#6c757d' }}>
                      {exercice.nb_ecritures_total}
                    </div>
                    <div style={{ fontSize: '12px', color: '#666' }}>Écritures</div>
                  </div>
                </div>

                {/* Aperçu des périodes */}
                {showPeriodesDetail === exercice.id && (
                  <div style={{ marginTop: '15px', padding: '10px', backgroundColor: '#f8f9fa', borderRadius: '4px' }}>
                    <h4 style={{ margin: 0, marginBottom: '10px' }}>Périodes</h4>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: '5px' }}>
                      {exercice.periodes.map(periode => (
                        <div
                          key={periode.id}
                          style={{
                            padding: '5px',
                            fontSize: '12px',
                            textAlign: 'center',
                            backgroundColor: 'white',
                            border: '1px solid #ddd',
                            borderRadius: '3px'
                          }}
                        >
                          <div style={{ fontWeight: 'bold' }}>{periode.periode_complete}</div>
                          <div style={{
                            color: getPeriodeStatutColor(periode.statut),
                            fontSize: '11px'
                          }}>
                            {periode.statut}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '5px', marginLeft: '20px' }}>
                <button
                  onClick={() => handleEdit(exercice)}
                  style={{
                    padding: '6px 12px',
                    fontSize: '12px',
                    backgroundColor: '#007bff',
                    color: 'white',
                    border: 'none',
                    borderRadius: '3px',
                    cursor: 'pointer'
                  }}
                  disabled={exercice.statut === 'CLOTURE'}
                >
                  ✏️ Modifier
                </button>
                <button
                  onClick={() => handleView(exercice)}
                  style={{
                    padding: '6px 12px',
                    fontSize: '12px',
                    backgroundColor: '#28a745',
                    color: 'white',
                    border: 'none',
                    borderRadius: '3px',
                    cursor: 'pointer'
                  }}
                >
                  👁️ Détails
                </button>
                <button
                  onClick={() => setShowPeriodesDetail(showPeriodesDetail === exercice.id ? null : exercice.id)}
                  style={{
                    padding: '6px 12px',
                    fontSize: '12px',
                    backgroundColor: '#17a2b8',
                    color: 'white',
                    border: 'none',
                    borderRadius: '3px',
                    cursor: 'pointer'
                  }}
                >
                  📅 Périodes
                </button>
                {exercice.statut === 'PREPARATION' && (
                  <button
                    onClick={() => handleOuvrir(exercice)}
                    style={{
                      padding: '6px 12px',
                      fontSize: '12px',
                      backgroundColor: '#ffc107',
                      color: 'white',
                      border: 'none',
                      borderRadius: '3px',
                      cursor: 'pointer'
                    }}
                  >
                    🔓 Ouvrir
                  </button>
                )}
                {exercice.statut === 'OUVERT' && exercice.periodes.length < 12 && (
                  <button
                    onClick={() => handleGenererPeriodes(exercice)}
                    style={{
                      padding: '6px 12px',
                      fontSize: '12px',
                      backgroundColor: '#6f42c1',
                      color: 'white',
                      border: 'none',
                      borderRadius: '3px',
                      cursor: 'pointer'
                    }}
                  >
                    📆 Générer périodes
                  </button>
                )}
                {exercice.statut === 'OUVERT' && exercice.peut_etre_cloture && (
                  <button
                    onClick={() => handleCloturer(exercice)}
                    style={{
                      padding: '6px 12px',
                      fontSize: '12px',
                      backgroundColor: '#dc3545',
                      color: 'white',
                      border: 'none',
                      borderRadius: '3px',
                      cursor: 'pointer'
                    }}
                  >
                    🔒 Clôturer
                  </button>
                )}
                <button
                  onClick={() => handleDelete(exercice)}
                  style={{
                    padding: '6px 12px',
                    fontSize: '12px',
                    backgroundColor: '#dc3545',
                    color: 'white',
                    border: 'none',
                    borderRadius: '3px',
                    cursor: 'pointer'
                  }}
                  disabled={exercice.statut !== 'PREPARATION' || exercice.nb_ecritures_total > 0}
                >
                  🗑️ Supprimer
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

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
            width: '600px',
            maxHeight: '80vh',
            overflowY: 'auto'
          }}>
            <h3>
              {modalType === 'create' ? 'Nouvel Exercice' :
               modalType === 'edit' ? 'Modifier Exercice' :
               modalType === 'periodes' ? 'Périodes de l\'exercice' :
               'Détails de l\'Exercice'}
            </h3>

            {modalType === 'view' ? (
              <div>
                <p><strong>Code:</strong> {selectedExercice?.code}</p>
                <p><strong>Libellé:</strong> {selectedExercice?.libelle}</p>
                <p><strong>Date début:</strong> {selectedExercice && new Date(selectedExercice.date_debut).toLocaleDateString('fr-FR')}</p>
                <p><strong>Date fin:</strong> {selectedExercice && new Date(selectedExercice.date_fin).toLocaleDateString('fr-FR')}</p>
                <p><strong>Statut:</strong> {selectedExercice?.statut_display}</p>
                <p><strong>Durée:</strong> {selectedExercice?.duree_mois} mois ({selectedExercice?.duree_jours} jours)</p>
                <p><strong>Progression:</strong> {selectedExercice?.progression_pourcent}%</p>
                <p><strong>Nombre de périodes:</strong> {selectedExercice?.periodes.length}</p>
                <p><strong>Périodes clôturées:</strong> {selectedExercice?.nb_periodes_cloturees}</p>
                <p><strong>Nombre d'écritures:</strong> {selectedExercice?.nb_ecritures_total}</p>
                <p><strong>Premier exercice:</strong> {selectedExercice?.is_premier_exercice ? 'Oui' : 'Non'}</p>
                <p><strong>Peut être clôturé:</strong> {selectedExercice?.peut_etre_cloture ? 'Oui' : 'Non'}</p>
                {selectedExercice?.date_cloture_provisoire && (
                  <p><strong>Clôture provisoire:</strong> {new Date(selectedExercice.date_cloture_provisoire).toLocaleDateString('fr-FR')}</p>
                )}
                {selectedExercice?.date_cloture_definitive && (
                  <p><strong>Clôture définitive:</strong> {new Date(selectedExercice.date_cloture_definitive).toLocaleDateString('fr-FR')}</p>
                )}
              </div>
            ) : modalType === 'periodes' ? (
              <div>
                <h4>Périodes de l'exercice {selectedExercice?.libelle}</h4>
                <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '10px' }}>
                  <thead>
                    <tr style={{ backgroundColor: '#f8f9fa' }}>
                      <th style={{ padding: '8px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>N°</th>
                      <th style={{ padding: '8px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>Période</th>
                      <th style={{ padding: '8px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>Dates</th>
                      <th style={{ padding: '8px', textAlign: 'center', borderBottom: '2px solid #dee2e6' }}>Statut</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedExercice?.periodes.map(periode => (
                      <tr key={periode.id} style={{ borderBottom: '1px solid #eee' }}>
                        <td style={{ padding: '8px' }}>{periode.numero}</td>
                        <td style={{ padding: '8px' }}>{periode.periode_complete}</td>
                        <td style={{ padding: '8px', fontSize: '12px' }}>
                          {new Date(periode.date_debut).toLocaleDateString('fr-FR')} - {new Date(periode.date_fin).toLocaleDateString('fr-FR')}
                        </td>
                        <td style={{ padding: '8px', textAlign: 'center' }}>
                          <span style={{
                            padding: '2px 8px',
                            borderRadius: '4px',
                            fontSize: '12px',
                            backgroundColor: getPeriodeStatutColor(periode.statut) + '20',
                            color: getPeriodeStatutColor(periode.statut),
                            fontWeight: 'bold'
                          }}>
                            {periode.statut}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <form onSubmit={(e) => {
                e.preventDefault();
                const formData = new FormData(e.currentTarget);
                const data = {
                  code: formData.get('code'),
                  libelle: formData.get('libelle'),
                  date_debut: formData.get('date_debut'),
                  date_fin: formData.get('date_fin'),
                  statut: formData.get('statut') || 'OUVERT',
                  is_premier_exercice: formData.get('is_premier_exercice') === 'true'
                };
                handleSave(data);
              }}>
                <div style={{ marginBottom: '15px' }}>
                  <label style={{ display: 'block', marginBottom: '5px' }}>Code:</label>
                  <input
                    name="code"
                    type="text"
                    defaultValue={selectedExercice?.code || ''}
                    required
                    maxLength={10}
                    style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
                  />
                </div>

                <div style={{ marginBottom: '15px' }}>
                  <label style={{ display: 'block', marginBottom: '5px' }}>Libellé:</label>
                  <input
                    name="libelle"
                    type="text"
                    defaultValue={selectedExercice?.libelle || ''}
                    required
                    style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
                  />
                </div>

                <div style={{ marginBottom: '15px' }}>
                  <label style={{ display: 'block', marginBottom: '5px' }}>Date de début:</label>
                  <input
                    name="date_debut"
                    type="date"
                    defaultValue={selectedExercice?.date_debut || ''}
                    required
                    style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
                  />
                </div>

                <div style={{ marginBottom: '15px' }}>
                  <label style={{ display: 'block', marginBottom: '5px' }}>Date de fin:</label>
                  <input
                    name="date_fin"
                    type="date"
                    defaultValue={selectedExercice?.date_fin || ''}
                    required
                    style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
                  />
                </div>

                {modalType === 'create' && (
                  <div style={{ marginBottom: '15px' }}>
                    <label style={{ display: 'block', marginBottom: '5px' }}>
                      <input
                        name="is_premier_exercice"
                        type="checkbox"
                        value="true"
                        defaultChecked={selectedExercice?.is_premier_exercice || false}
                        style={{ marginRight: '5px' }}
                      />
                      Premier exercice de l'entreprise
                    </label>
                  </div>
                )}

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

            {(modalType === 'view' || modalType === 'periodes') && (
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

export default Exercices;