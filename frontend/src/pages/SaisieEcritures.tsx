// frontend/src/pages/SaisieEcritures.tsx
import React, { useState, useEffect, useRef, KeyboardEvent } from 'react';
import { ecrituresService, journauxService, comptesService, exercicesService } from '../services/api';

interface Journal {
  id: number;
  code: string;
  libelle: string;
  type: string;
}

interface Compte {
  id: number;
  code: string;
  libelle: string;
  type: string;
}

interface Periode {
  id: number;
  numero: number;
  date_debut: string;
  date_fin: string;
  periode_complete: string;
  statut: string;
}

interface LigneEcriture {
  id?: number;
  tempId: string;
  date?: string;
  compte: string;
  compteId?: number;
  tiers: string;
  libelle: string;
  debit: string;
  credit: string;
  piece?: string;
  isNew?: boolean;
  isHeader?: boolean;
}

function SaisieEcritures() {
  // États principaux
  const [journaux, setJournaux] = useState<Journal[]>([]);
  const [comptes, setComptes] = useState<Compte[]>([]);
  const [periodes, setPeriodes] = useState<Periode[]>([]);

  const [selectedJournal, setSelectedJournal] = useState<string>('');
  const [selectedPeriode, setSelectedPeriode] = useState<string>('');
  const [exerciceId, setExerciceId] = useState<number | null>(null);

  const [lignes, setLignes] = useState<LigneEcriture[]>([]);
  const [currentRow, setCurrentRow] = useState(0);
  const [currentCol, setCurrentCol] = useState(0);

  const [totalDebit, setTotalDebit] = useState(0);
  const [totalCredit, setTotalCredit] = useState(0);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Références pour la navigation
  const inputRefs = useRef<(HTMLInputElement | null)[][]>([]);
  const gridRef = useRef<HTMLDivElement>(null);

  // Charger les données initiales
  useEffect(() => {
    loadInitialData();
  }, []);

  // Formater la date pour afficher uniquement le jour
  const formatDateToDay = (dateString: string | undefined) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.getDate().toString().padStart(2, '0');
  };

  const loadInitialData = async () => {
    try {
      setLoading(true);

      // Charger les journaux
      const journauxResponse = await journauxService.getAll({ is_active: true });
      setJournaux(journauxResponse.data.results || []);

      // Charger les comptes
      const comptesResponse = await comptesService.getAll({ page_size: 2000 });
      setComptes(comptesResponse.data.results || []);

      // Charger l'exercice en cours
      const exerciceResponse = await exercicesService.getAll({ statut: 'OUVERT' });
      if (exerciceResponse.data.results && exerciceResponse.data.results.length > 0) {
        const exercice = exerciceResponse.data.results[0];
        setExerciceId(exercice.id);
        setPeriodes(exercice.periodes || []);

        // Sélectionner la période courante
        const today = new Date().toISOString().split('T')[0];
        const periodeCourante = exercice.periodes.find((p: Periode) =>
          p.date_debut <= today && p.date_fin >= today && p.statut === 'OUVERTE'
        );
        if (periodeCourante) {
          setSelectedPeriode(periodeCourante.id.toString());
        }
      }

      // Initialiser avec une ligne vide
      addNewEcriture();

    } catch (err) {
      setError('Erreur lors du chargement des données');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Ajouter une nouvelle écriture
  const addNewEcriture = () => {
    const newEcriture: LigneEcriture[] = [
      {
        tempId: Date.now().toString(),
        date: new Date().toISOString().split('T')[0],
        compte: '',
        tiers: '',
        libelle: '',
        debit: '',
        credit: '',
        piece: '',
        isNew: true,
        isHeader: true
      },
      {
        tempId: Date.now().toString() + '_1',
        compte: '',
        tiers: '',
        libelle: '',
        debit: '',
        credit: '',
        piece: '',
        isNew: true
      }
    ];

    setLignes([...lignes, ...newEcriture]);
  };

  // Ajouter une ligne à l'écriture courante
  const addLigneToCurrentEcriture = () => {
    const newLigne: LigneEcriture = {
      tempId: Date.now().toString(),
      compte: '',
      tiers: '',
      libelle: lignes[currentRow].libelle, // Reprendre le libellé de l'écriture
      debit: '',
      credit: '',
      piece: '',
      isNew: true
    };

    // Trouver l'index de la dernière ligne de l'écriture courante
    let insertIndex = currentRow + 1;
    while (insertIndex < lignes.length && !lignes[insertIndex].isHeader) {
      insertIndex++;
    }

    const newLignes = [...lignes];
    newLignes.splice(insertIndex, 0, newLigne);
    setLignes(newLignes);
  };

  // Navigation au clavier
  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>, row: number, col: number) => {
    const totalCols = 7; // date, piece, compte, tiers, libelle, debit, credit

    switch (e.key) {
      case 'Tab':
        e.preventDefault();
        if (e.shiftKey) {
          // Tab arrière
          if (col > 0) {
            setCurrentCol(col - 1);
          } else if (row > 0) {
            setCurrentRow(row - 1);
            setCurrentCol(totalCols - 1);
          }
        } else {
          // Tab avant
          if (col < totalCols - 1) {
            setCurrentCol(col + 1);
          } else if (row < lignes.length - 1) {
            setCurrentRow(row + 1);
            setCurrentCol(0);
          } else {
            // Dernière cellule, ajouter une ligne
            addLigneToCurrentEcriture();
            setCurrentRow(row + 1);
            setCurrentCol(0);
          }
        }
        break;

      case 'Enter':
        e.preventDefault();
        if (row < lignes.length - 1) {
          setCurrentRow(row + 1);
        } else {
          addLigneToCurrentEcriture();
          setCurrentRow(row + 1);
          setCurrentCol(0);
        }
        break;

      case 'ArrowUp':
        if (row > 0) {
          setCurrentRow(row - 1);
        }
        break;

      case 'ArrowDown':
        if (row < lignes.length - 1) {
          setCurrentRow(row + 1);
        }
        break;

      case 'F2': // Nouvelle écriture
        e.preventDefault();
        addNewEcriture();
        break;

      case 'F5': // Équilibrer
        e.preventDefault();
        equilibrerEcriture();
        break;
    }
  };

  // Focus sur la cellule active
  useEffect(() => {
    if (inputRefs.current[currentRow] && inputRefs.current[currentRow][currentCol]) {
      inputRefs.current[currentRow][currentCol]?.focus();
    }
  }, [currentRow, currentCol]);

  // Mise à jour d'une cellule
  const updateCell = (row: number, field: keyof LigneEcriture, value: string) => {
    const newLignes = [...lignes];
    newLignes[row] = { ...newLignes[row], [field]: value };

    // Si c'est le libellé de l'en-tête, propager aux lignes suivantes
    if (field === 'libelle' && lignes[row].isHeader) {
      let i = row + 1;
      while (i < lignes.length && !lignes[i].isHeader) {
        if (!newLignes[i].libelle || newLignes[i].libelle === lignes[row].libelle) {
          newLignes[i].libelle = value;
        }
        i++;
      }
    }

    setLignes(newLignes);
  };

  // Recherche de compte
  const handleCompteSearch = async (row: number, value: string) => {
    updateCell(row, 'compte', value);

    // Recherche du compte
    const compte = comptes.find(c => c.code.startsWith(value));
    if (compte) {
      const newLignes = [...lignes];
      newLignes[row].compteId = compte.id;
      setLignes(newLignes);
    }
  };

  // Calculer les totaux
  useEffect(() => {
    let debit = 0;
    let credit = 0;

    lignes.forEach(ligne => {
      if (!ligne.isHeader) {
        debit += parseFloat(ligne.debit || '0');
        credit += parseFloat(ligne.credit || '0');
      }
    });

    setTotalDebit(debit);
    setTotalCredit(credit);
  }, [lignes]);

  // Équilibrer l'écriture
  const equilibrerEcriture = () => {
    const ecart = totalDebit - totalCredit;
    if (Math.abs(ecart) < 0.01) return;

    // Trouver la dernière ligne non vide
    let lastIndex = -1;
    for (let i = lignes.length - 1; i >= 0; i--) {
      if (!lignes[i].isHeader && (lignes[i].compte || lignes[i].debit || lignes[i].credit)) {
        lastIndex = i;
        break;
      }
    }

    if (lastIndex === -1) return;

    const newLignes = [...lignes];
    if (ecart > 0) {
      // Ajouter au crédit
      newLignes[lastIndex].credit = ecart.toFixed(2);
      newLignes[lastIndex].debit = '';
    } else {
      // Ajouter au débit
      newLignes[lastIndex].debit = Math.abs(ecart).toFixed(2);
      newLignes[lastIndex].credit = '';
    }

    setLignes(newLignes);
  };

  // Valider et sauvegarder
  const validerEcriture = async () => {
    if (!selectedJournal || !selectedPeriode) {
      alert('Veuillez sélectionner un journal et une période');
      return;
    }

    if (Math.abs(totalDebit - totalCredit) >= 0.01) {
      alert('L\'écriture n\'est pas équilibrée');
      return;
    }

    // Grouper par écriture
    const ecritures: any[] = [];
    let currentEcriture: any = null;

    lignes.forEach(ligne => {
      if (ligne.isHeader && ligne.compte) {
        // Sauvegarder l'écriture précédente si elle existe
        if (currentEcriture && currentEcriture.lignes.length >= 2) {
          ecritures.push(currentEcriture);
        }

        // Nouvelle écriture
        currentEcriture = {
          journal: parseInt(selectedJournal),
          periode: parseInt(selectedPeriode),
          exercice: exerciceId,
          date_ecriture: ligne.date,
          libelle: ligne.libelle,
          reference: ligne.piece || '',
          lignes_data: []
        };
      } else if (currentEcriture && ligne.compte && ligne.compteId) {
        // Ajouter la ligne
        currentEcriture.lignes_data.push({
          compte: ligne.compteId,
          libelle: ligne.libelle,
          montant_debit: parseFloat(ligne.debit || '0'),
          montant_credit: parseFloat(ligne.credit || '0'),
          piece: ligne.piece || ''
        });
      }
    });

    // Sauvegarder la dernière écriture
    if (currentEcriture && currentEcriture.lignes_data.length >= 2) {
      ecritures.push(currentEcriture);
    }

    // Envoyer au serveur
    setSaving(true);
    try {
      for (const ecriture of ecritures) {
        await ecrituresService.create(ecriture);
      }

      alert(`${ecritures.length} écriture(s) créée(s) avec succès`);

      // Réinitialiser
      setLignes([]);
      addNewEcriture();

    } catch (err: any) {
      alert(err.response?.data?.error || 'Erreur lors de la sauvegarde');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div>Chargement...</div>;
  if (error) return <div style={{ color: 'red' }}>{error}</div>;

  return (
    <div style={{ padding: '20px' }}>
      <h2>Saisie d'Écritures</h2>

      {/* En-tête */}
      <div style={{ marginBottom: '20px', display: 'flex', gap: '20px', alignItems: 'center' }}>
        <div>
          <label>Journal:</label>
          <select
            value={selectedJournal}
            onChange={(e) => setSelectedJournal(e.target.value)}
            style={{ marginLeft: '10px', padding: '5px' }}
          >
            <option value="">Sélectionner...</option>
            {journaux.map(journal => (
              <option key={journal.id} value={journal.id}>
                {journal.code} - {journal.libelle}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label>Période:</label>
          <select
            value={selectedPeriode}
            onChange={(e) => setSelectedPeriode(e.target.value)}
            style={{ marginLeft: '10px', padding: '5px' }}
          >
            <option value="">Sélectionner...</option>
            {periodes.filter(p => p.statut === 'OUVERTE').map(periode => (
              <option key={periode.id} value={periode.id}>
                {periode.periode_complete}
              </option>
            ))}
          </select>
        </div>

        <div style={{ marginLeft: 'auto', display: 'flex', gap: '10px' }}>
          <button
            onClick={addNewEcriture}
            style={{
              padding: '8px 16px',
              backgroundColor: '#17a2b8',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Nouvelle Écriture (F2)
          </button>

          <button
            onClick={equilibrerEcriture}
            style={{
              padding: '8px 16px',
              backgroundColor: '#ffc107',
              color: 'black',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Équilibrer (F5)
          </button>

          <button
            onClick={validerEcriture}
            style={{
              padding: '8px 16px',
              backgroundColor: '#28a745',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
            disabled={saving || Math.abs(totalDebit - totalCredit) >= 0.01}
          >
            Valider
          </button>
        </div>
      </div>

      {/* Grille de saisie */}
      <div ref={gridRef} style={{ overflowX: 'auto', border: '1px solid #ddd' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ backgroundColor: '#f8f9fa' }}>
              <th style={{ ...thStyle, width: '50px' }}>Date</th>
              <th style={{ ...thStyle, width: '80px' }}>Pièce</th>
              <th style={{ ...thStyle, width: '120px' }}>Compte</th>
              <th style={{ ...thStyle, width: '150px' }}>Tiers</th>
              <th style={{ ...thStyle, width: '250px' }}>Libellé</th>
              <th style={{ ...thStyle, width: '100px' }}>Débit</th>
              <th style={{ ...thStyle, width: '100px' }}>Crédit</th>
            </tr>
          </thead>
          <tbody>
            {lignes.map((ligne, rowIndex) => (
              <React.Fragment key={ligne.tempId}>
                {ligne.isHeader && rowIndex > 0 && (
                  <tr>
                    <td colSpan={7} style={{ height: '2px', backgroundColor: '#007bff', padding: 0 }}></td>
                  </tr>
                )}
                <tr style={{ backgroundColor: rowIndex % 2 === 0 ? 'white' : '#f8f9fa' }}>
                  {/* Date - Afficher uniquement le jour */}
                  <td style={tdStyle}>
                    {ligne.isHeader ? (
                      <input
                        ref={el => {
                          if (!inputRefs.current[rowIndex]) inputRefs.current[rowIndex] = [];
                          inputRefs.current[rowIndex][0] = el;
                        }}
                        type="date"
                        value={ligne.date || ''}
                        onChange={(e) => updateCell(rowIndex, 'date', e.target.value)}
                        onKeyDown={(e) => handleKeyDown(e, rowIndex, 0)}
                        onFocus={() => { setCurrentRow(rowIndex); setCurrentCol(0); }}
                        style={{ ...inputStyle, width: '100%' }}
                      />
                    ) : (
                      <div style={{ padding: '4px', color: '#666', textAlign: 'center' }}>
                        {formatDateToDay(lignes.find((l, i) => i < rowIndex && l.isHeader)?.date)}
                      </div>
                    )}
                  </td>

                  {/* Pièce */}
                  <td style={tdStyle}>
                    <input
                      ref={el => {
                        if (!inputRefs.current[rowIndex]) inputRefs.current[rowIndex] = [];
                        inputRefs.current[rowIndex][1] = el;
                      }}
                      type="text"
                      value={ligne.piece || ''}
                      onChange={(e) => updateCell(rowIndex, 'piece', e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, rowIndex, 1)}
                      onFocus={() => { setCurrentRow(rowIndex); setCurrentCol(1); }}
                      placeholder="Réf..."
                      style={inputStyle}
                    />
                  </td>

                  {/* Compte */}
                  <td style={tdStyle}>
                    <input
                      ref={el => {
                        if (!inputRefs.current[rowIndex]) inputRefs.current[rowIndex] = [];
                        inputRefs.current[rowIndex][2] = el;
                      }}
                      type="text"
                      value={ligne.compte}
                      onChange={(e) => handleCompteSearch(rowIndex, e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, rowIndex, 2)}
                      onFocus={() => { setCurrentRow(rowIndex); setCurrentCol(2); }}
                      placeholder="Compte..."
                      style={{
                        ...inputStyle,
                        backgroundColor: ligne.isHeader ? '#e3f2fd' : 'white'
                      }}
                    />
                  </td>

                  {/* Tiers */}
                  <td style={tdStyle}>
                    <input
                      ref={el => {
                        if (!inputRefs.current[rowIndex]) inputRefs.current[rowIndex] = [];
                        inputRefs.current[rowIndex][3] = el;
                      }}
                      type="text"
                      value={ligne.tiers || ''}
                      onChange={(e) => updateCell(rowIndex, 'tiers', e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, rowIndex, 3)}
                      onFocus={() => { setCurrentRow(rowIndex); setCurrentCol(3); }}
                      placeholder="Tiers..."
                      style={inputStyle}
                    />
                  </td>

                  {/* Libellé */}
                  <td style={tdStyle}>
                    <input
                      ref={el => {
                        if (!inputRefs.current[rowIndex]) inputRefs.current[rowIndex] = [];
                        inputRefs.current[rowIndex][4] = el;
                      }}
                      type="text"
                      value={ligne.libelle}
                      onChange={(e) => updateCell(rowIndex, 'libelle', e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, rowIndex, 4)}
                      onFocus={() => { setCurrentRow(rowIndex); setCurrentCol(4); }}
                      placeholder="Libellé..."
                      style={inputStyle}
                    />
                  </td>

                  {/* Débit */}
                  <td style={tdStyle}>
                    <input
                      ref={el => {
                        if (!inputRefs.current[rowIndex]) inputRefs.current[rowIndex] = [];
                        inputRefs.current[rowIndex][5] = el;
                      }}
                      type="number"
                      value={ligne.debit}
                      onChange={(e) => updateCell(rowIndex, 'debit', e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, rowIndex, 5)}
                      onFocus={() => { setCurrentRow(rowIndex); setCurrentCol(5); }}
                      placeholder="0.00"
                      step="0.01"
                      style={{ ...inputStyle, textAlign: 'right' }}
                      disabled={ligne.isHeader}
                    />
                  </td>

                  {/* Crédit */}
                  <td style={tdStyle}>
                    <input
                      ref={el => {
                        if (!inputRefs.current[rowIndex]) inputRefs.current[rowIndex] = [];
                        inputRefs.current[rowIndex][6] = el;
                      }}
                      type="number"
                      value={ligne.credit}
                      onChange={(e) => updateCell(rowIndex, 'credit', e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, rowIndex, 6)}
                      onFocus={() => { setCurrentRow(rowIndex); setCurrentCol(6); }}
                      placeholder="0.00"
                      step="0.01"
                      style={{ ...inputStyle, textAlign: 'right' }}
                      disabled={ligne.isHeader}
                    />
                  </td>
                </tr>
              </React.Fragment>
            ))}
          </tbody>
          <tfoot>
            <tr style={{ backgroundColor: '#e9ecef', fontWeight: 'bold' }}>
              <td colSpan={5} style={{ ...tdStyle, textAlign: 'right' }}>Totaux:</td>
              <td style={{ ...tdStyle, textAlign: 'right' }}>{totalDebit.toFixed(2)}</td>
              <td style={{ ...tdStyle, textAlign: 'right' }}>{totalCredit.toFixed(2)}</td>
            </tr>
            <tr style={{ backgroundColor: '#e9ecef' }}>
              <td colSpan={7} style={{ ...tdStyle, textAlign: 'center' }}>
                {Math.abs(totalDebit - totalCredit) < 0.01 ? (
                  <span style={{ color: 'green' }}>✓ Équilibré</span>
                ) : (
                  <span style={{ color: 'red' }}>
                    Écart: {Math.abs(totalDebit - totalCredit).toFixed(2)}
                  </span>
                )}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      {/* Instructions */}
      <div style={{ marginTop: '20px', padding: '10px', backgroundColor: '#f8f9fa', borderRadius: '4px' }}>
        <h4>Raccourcis clavier:</h4>
        <ul style={{ margin: 0, paddingLeft: '20px' }}>
          <li><strong>Tab</strong> : Passer à la cellule suivante</li>
          <li><strong>Shift+Tab</strong> : Revenir à la cellule précédente</li>
          <li><strong>Enter</strong> : Passer à la ligne suivante</li>
          <li><strong>F2</strong> : Nouvelle écriture</li>
          <li><strong>F5</strong> : Équilibrer l'écriture</li>
        </ul>
      </div>
    </div>
  );
}

// Styles
const thStyle: React.CSSProperties = {
  padding: '8px',
  textAlign: 'left',
  borderBottom: '2px solid #dee2e6',
  fontWeight: '600',
  color: '#495057',
  position: 'sticky',
  top: 0,
  backgroundColor: '#f8f9fa'
};

const tdStyle: React.CSSProperties = {
  padding: '2px',
  borderBottom: '1px solid #eee'
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '4px 8px',
  border: '1px solid transparent',
  outline: 'none',
  backgroundColor: 'transparent'
};

export default SaisieEcritures;