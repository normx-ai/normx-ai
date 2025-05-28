import json
import os
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.accounting.models import Journal, CompteOHADA


class Command(BaseCommand):
    help = 'Import les journaux OHADA depuis le fichier JSON ou créer les journaux de base'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='apps/accounting/fixtures/journaux_base.json',
            help='Chemin vers le fichier JSON des journaux'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Supprimer tous les journaux existants avant l\'import'
        )
        parser.add_argument(
            '--create-defaults',
            action='store_true',
            help='Créer les journaux par défaut sans fichier JSON'
        )

    def handle(self, *args, **options):
        # Si on veut créer les journaux par défaut
        if options['create_defaults']:
            self.create_default_journals(options['clear'])
            return

        # Sinon, importer depuis le fichier JSON
        file_path = options['file']

        # Vérifier que le fichier existe
        if not os.path.exists(file_path):
            self.stdout.write(
                self.style.ERROR(f'Fichier non trouvé : {file_path}')
            )
            # Proposer de créer les journaux par défaut
            self.stdout.write(
                self.style.WARNING('Utilisation des journaux par défaut...')
            )
            self.create_default_journals(options['clear'])
            return

        # Charger les données JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Supprimer les journaux existants si demandé
        if options['clear']:
            Journal.objects.all().delete()
            self.stdout.write(
                self.style.WARNING('Tous les journaux existants ont été supprimés')
            )

        # Import avec transaction
        with transaction.atomic():
            created_count = 0
            updated_count = 0

            for item in data:
                journal_data = item['fields']

                # Vérifier que le type est valide
                valid_types = dict(Journal.TYPES_JOURNAL).keys()
                if journal_data['type'] not in valid_types:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Type invalide '{journal_data['type']}' pour le journal {journal_data['code']}. "
                            f"Types valides : {', '.join(valid_types)}"
                        )
                    )
                    continue

                # Gérer le compte de contrepartie
                compte_contrepartie = None
                if journal_data.get('compte_contrepartie'):
                    try:
                        compte_contrepartie = CompteOHADA.objects.get(
                            code=journal_data['compte_contrepartie']
                        )
                    except CompteOHADA.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Compte de contrepartie {journal_data['compte_contrepartie']} "
                                f"non trouvé pour le journal {journal_data['code']}"
                            )
                        )

                journal, created = Journal.objects.update_or_create(
                    code=journal_data['code'],
                    defaults={
                        'libelle': journal_data['libelle'],
                        'type': journal_data['type'],
                        'compte_contrepartie': compte_contrepartie,
                        'is_active': journal_data.get('is_active', True),
                    }
                )

                if created:
                    created_count += 1
                    status = f"✓ Créé : {journal.code} - {journal.libelle}"
                    if compte_contrepartie:
                        status += f" → {compte_contrepartie.code}"
                    self.stdout.write(self.style.SUCCESS(status))
                else:
                    updated_count += 1
                    status = f"↻ Mis à jour : {journal.code} - {journal.libelle}"
                    if compte_contrepartie:
                        status += f" → {compte_contrepartie.code}"
                    self.stdout.write(status)

        self.stdout.write(
            self.style.SUCCESS(
                f'\nImport terminé : {created_count} journaux créés, '
                f'{updated_count} journaux mis à jour'
            )
        )

    def create_default_journals(self, clear=False):
        """Créer les journaux par défaut selon OHADA"""

        if clear:
            Journal.objects.all().delete()
            self.stdout.write(
                self.style.WARNING('Tous les journaux existants ont été supprimés')
            )

        # Journaux standards OHADA
        journaux = [
            # Journaux principaux
            {'code': 'AC', 'libelle': 'Journal des Achats', 'type': 'AC'},
            {'code': 'VT', 'libelle': 'Journal des Ventes', 'type': 'VT'},
            {'code': 'BQ1', 'libelle': 'Banque Principale', 'type': 'BQ'},
            {'code': 'CA1', 'libelle': 'Caisse Principale', 'type': 'CA'},

            # Journaux spécialisés
            {'code': 'PA', 'libelle': 'Journal de Paie et Salaires', 'type': 'PA'},
            {'code': 'FI', 'libelle': 'Journal Fiscal - TVA, IS, IRPP', 'type': 'FI'},
            {'code': 'SO', 'libelle': 'Journal Social - CNPS', 'type': 'SO'},
            {'code': 'ST', 'libelle': 'Journal des Stocks et Inventaires', 'type': 'ST'},
            {'code': 'IM', 'libelle': 'Journal des Immobilisations', 'type': 'IM'},
            {'code': 'PR', 'libelle': 'Journal des Provisions', 'type': 'PR'},

            # Journaux techniques
            {'code': 'AN', 'libelle': 'Journal des À Nouveaux', 'type': 'AN'},
            {'code': 'CL', 'libelle': 'Journal de Clôture', 'type': 'CL'},
            {'code': 'OD', 'libelle': 'Opérations Diverses', 'type': 'OD'},
            {'code': 'EX', 'libelle': 'Journal Extra-comptable', 'type': 'EX'},

            # Journaux additionnels pour multi-banques/caisses
            {'code': 'BQ2', 'libelle': 'Banque Secondaire', 'type': 'BQ'},
            {'code': 'CA2', 'libelle': 'Caisse Secondaire', 'type': 'CA'},
        ]

        with transaction.atomic():
            created_count = 0
            updated_count = 0

            for journal_data in journaux:
                journal, created = Journal.objects.update_or_create(
                    code=journal_data['code'],
                    defaults={
                        'libelle': journal_data['libelle'],
                        'type': journal_data['type'],
                        'is_active': True,
                    }
                )

                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ Créé : {journal.code} - {journal.libelle}")
                    )
                else:
                    updated_count += 1
                    self.stdout.write(
                        f"↻ Existe déjà : {journal.code} - {journal.libelle}"
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nCréation terminée : {created_count} journaux créés, '
                f'{updated_count} journaux existants'
            )
        )

        # Afficher un résumé par type
        self.stdout.write('\n' + self.style.MIGRATE_HEADING('Résumé par type :'))
        for type_code, type_label in Journal.TYPES_JOURNAL:
            count = Journal.objects.filter(type=type_code).count()
            if count > 0:
                self.stdout.write(f"  • {type_label} ({type_code}) : {count} journal(x)")