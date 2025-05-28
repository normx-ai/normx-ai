import json
import os
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.accounting.models import CompteOHADA


class Command(BaseCommand):
    help = 'Import les comptes OHADA depuis le fichier JSON'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='apps/accounting/fixtures/ohada_accounts.json',
            help='Chemin vers le fichier JSON des comptes OHADA'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Supprimer tous les comptes existants avant l\'import'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        
        # Vérifier que le fichier existe
        if not os.path.exists(file_path):
            self.stdout.write(
                self.style.ERROR(f'Fichier non trouvé : {file_path}')
            )
            return

        # Charger les données
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Supprimer les comptes existants si demandé
        if options['clear']:
            CompteOHADA.objects.all().delete()
            self.stdout.write(
                self.style.WARNING('Tous les comptes existants ont été supprimés')
            )

        # Import avec transaction
        with transaction.atomic():
            created_count = 0
            updated_count = 0
            
            for compte_data in data:
                compte, created = CompteOHADA.objects.update_or_create(
                    code=compte_data['code'],
                    defaults={
                        'libelle': compte_data['libelle'],
                        'classe': compte_data['classe'],
                        'type': compte_data['type'],
                        'ref': compte_data.get('ref', ''),
                    }
                )
                
                if created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Import terminé : {created_count} comptes créés, '
                f'{updated_count} comptes mis à jour'
            )
        )
