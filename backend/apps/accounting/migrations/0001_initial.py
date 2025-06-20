# Generated by Django 5.2.1 on 2025-05-25 14:40

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CompteOHADA',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=10, unique=True, validators=[django.core.validators.RegexValidator('^\\d{8}$', 'Le code doit contenir exactement 8 chiffres')])),
                ('libelle', models.CharField(max_length=255)),
                ('classe', models.CharField(max_length=1)),
                ('type', models.CharField(choices=[('actif', 'Actif'), ('passif', 'Passif'), ('charge', 'Charge'), ('produit', 'Produit')], max_length=10)),
                ('ref', models.CharField(blank=True, max_length=5)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Compte OHADA',
                'verbose_name_plural': 'Comptes OHADA',
                'ordering': ['code'],
            },
        ),
    ]
