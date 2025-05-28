# apps/accounting/serializers/__init__.py
"""
Serializers pour l'application accounting
"""

from .base import (
    CompteOHADASerializer,
    CompteOHADAMinimalSerializer,
    CompteOHADAStatsSerializer,
    JournalSerializer,
    JournalMinimalSerializer,
    JournalStatsSerializer
)

from .tiers import (
    TiersSerializer,
    TiersMinimalSerializer,
    TiersStatsSerializer,
    TiersCreationSerializer
)

from .exercices import (
    ExerciceComptableSerializer,
    ExerciceComptableMinimalSerializer,
    ExerciceComptableStatsSerializer,
    PeriodeComptableSerializer,
    PeriodeComptableMinimalSerializer,
    ClotureExerciceSerializer
)

from .ecritures import (
    EcritureComptableSerializer,
    EcritureComptableMinimalSerializer,
    EcritureComptableStatsSerializer,
    LigneEcritureSerializer,
    LigneEcritureCreateSerializer,
    ValidationEcritureSerializer,
    SaisieRapideSerializer
)

__all__ = [
    # Comptes OHADA
    'CompteOHADASerializer',
    'CompteOHADAMinimalSerializer',
    'CompteOHADAStatsSerializer',

    # Journaux
    'JournalSerializer',
    'JournalMinimalSerializer',
    'JournalStatsSerializer',

    # Tiers
    'TiersSerializer',
    'TiersMinimalSerializer',
    'TiersStatsSerializer',
    'TiersCreationSerializer',

    # Exercices et périodes
    'ExerciceComptableSerializer',
    'ExerciceComptableMinimalSerializer',
    'ExerciceComptableStatsSerializer',
    'PeriodeComptableSerializer',
    'PeriodeComptableMinimalSerializer',
    'ClotureExerciceSerializer',

    # Écritures et lignes
    'EcritureComptableSerializer',
    'EcritureComptableMinimalSerializer',
    'EcritureComptableStatsSerializer',
    'LigneEcritureSerializer',
    'LigneEcritureCreateSerializer',
    'ValidationEcritureSerializer',
    'SaisieRapideSerializer'
]