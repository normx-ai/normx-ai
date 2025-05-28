# backend/apps/accounting/management/commands/update_journaux_contrepartie.py

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.accounting.models import Journal, CompteOHADA


class Command(BaseCommand):
    help = 'Met à jour les comptes de contrepartie des journaux de banque et caisse'

    def add_arguments(self, parser):
        parser.add_argument(
            '--auto',
            action='store_true',
            help='Association automatique basée sur les conventions OHADA'
        )

    def handle(self, *args, **options):
        # Associations recommandées selon OHADA
        # Format: code_journal -> code_compte
        associations_ohada = {
            # Banques - Classe 52
            'BQ1': '52110000',  # Banque principale
            'BQ2': '52120000',  # Banque secondaire
            'BQ3': '52130000',  # Autres banques

            # Caisses - Classe 57
            'CA1': '57110000',  # Caisse principale
            'CA2': '57120000',  # Caisse secondaire
            'CA3': '57130000',  # Autres caisses
        }

        if options['auto']:
            self.auto_associate()
        else:
            self.manual_associate(associations_ohada)

    def manual_associate(self, associations):
        """Association manuelle basée sur le dictionnaire fourni"""
        self.stdout.write(self.style.MIGRATE_HEADING('Association des comptes de contrepartie...'))

        success_count = 0
        errors = []

        with transaction.atomic():
            for code_journal, code_compte in associations.items():
                try:
                    journal = Journal.objects.get(code=code_journal)

                    # Vérifier si un compte est déjà associé
                    if journal.compte_contrepartie:
                        self.stdout.write(
                            f"ℹ {journal.code} a déjà le compte {journal.compte_contrepartie.code}"
                        )
                        continue

                    # Chercher le compte
                    try:
                        compte = CompteOHADA.objects.get(code=code_compte)
                        journal.compte_contrepartie = compte
                        journal.save()

                        success_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"✓ {journal.code} - {journal.libelle} → "
                                f"{compte.code} - {compte.libelle}"
                            )
                        )
                    except CompteOHADA.DoesNotExist:
                        errors.append(f"Compte {code_compte} non trouvé pour {journal.code}")

                except Journal.DoesNotExist:
                    # Journal non trouvé, on passe silencieusement
                    pass

        # Résumé
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(
            self.style.SUCCESS(f'✓ {success_count} associations créées')
        )

        if errors:
            self.stdout.write(self.style.ERROR(f'✗ {len(errors)} erreurs :'))
            for error in errors:
                self.stdout.write(f"  - {error}")

        # Afficher les journaux sans contrepartie
        self.show_unassociated_journals()

    def auto_associate(self):
        """Association automatique intelligente basée sur les codes et types"""
        self.stdout.write(
            self.style.MIGRATE_HEADING('Association automatique des comptes de contrepartie...')
        )

        success_count = 0

        with transaction.atomic():
            # Journaux de type Banque
            for journal in Journal.objects.filter(type='BQ', compte_contrepartie__isnull=True):
                # Chercher un compte 521xxxxx correspondant
                comptes_banque = CompteOHADA.objects.filter(
                    code__startswith='521',
                    is_active=True
                ).order_by('code')

                if comptes_banque.exists():
                    # Prendre le premier disponible ou celui qui correspond au numéro
                    if 'BQ1' in journal.code:
                        compte = comptes_banque.filter(code='52110000').first() or comptes_banque.first()
                    elif 'BQ2' in journal.code:
                        compte = comptes_banque.filter(code='52120000').first() or comptes_banque[
                            1] if comptes_banque.count() > 1 else comptes_banque.first()
                    else:
                        compte = comptes_banque.first()

                    journal.compte_contrepartie = compte
                    journal.save()
                    success_count += 1

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ {journal.code} → {compte.code} - {compte.libelle}"
                        )
                    )

            # Journaux de type Caisse
            for journal in Journal.objects.filter(type='CA', compte_contrepartie__isnull=True):
                # Chercher un compte 571xxxxx correspondant
                comptes_caisse = CompteOHADA.objects.filter(
                    code__startswith='571',
                    is_active=True
                ).order_by('code')

                if comptes_caisse.exists():
                    # Prendre le premier disponible ou celui qui correspond au numéro
                    if 'CA1' in journal.code:
                        compte = comptes_caisse.filter(code='57110000').first() or comptes_caisse.first()
                    elif 'CA2' in journal.code:
                        compte = comptes_caisse.filter(code='57120000').first() or comptes_caisse[
                            1] if comptes_caisse.count() > 1 else comptes_caisse.first()
                    else:
                        compte = comptes_caisse.first()

                    journal.compte_contrepartie = compte
                    journal.save()
                    success_count += 1

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ {journal.code} → {compte.code} - {compte.libelle}"
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(f'\n✓ {success_count} associations automatiques créées')
        )
        self.show_unassociated_journals()

    def show_unassociated_journals(self):
        """Afficher les journaux qui devraient avoir une contrepartie mais n'en ont pas"""
        journaux_sans_contrepartie = Journal.objects.filter(
            type__in=['BQ', 'CA'],
            compte_contrepartie__isnull=True,
            is_active=True
        )

        if journaux_sans_contrepartie.exists():
            self.stdout.write(
                self.style.WARNING(
                    f'\n⚠ {journaux_sans_contrepartie.count()} journaux de banque/caisse '
                    'sans compte de contrepartie :'
                )
            )
            for journal in journaux_sans_contrepartie:
                self.stdout.write(f"  - {journal.code} - {journal.libelle}")

                # Suggérer des comptes possibles
                if journal.type == 'BQ':
                    suggestions = CompteOHADA.objects.filter(
                        code__startswith='521',
                        is_active=True
                    )[:3]
                else:  # CA
                    suggestions = CompteOHADA.objects.filter(
                        code__startswith='571',
                        is_active=True
                    )[:3]

                if suggestions:
                    self.stdout.write("    Suggestions :")
                    for compte in suggestions:
                        self.stdout.write(f"      • {compte.code} - {compte.libelle}")

        # Afficher tous les journaux avec leur contrepartie
        self.stdout.write('\n' + self.style.MIGRATE_HEADING('État des journaux :'))
        for journal in Journal.objects.filter(is_active=True).order_by('type', 'code'):
            if journal.compte_contrepartie:
                self.stdout.write(
                    f"  {journal.code} ({journal.get_type_display()}) → "
                    f"{journal.compte_contrepartie.code}"
                )
            else:
                self.stdout.write(f"  {journal.code} ({journal.get_type_display()}) → -")