# apps/accounting/views/test_serializers.py
"""
Vue de test temporaire pour vérifier les serializers
À supprimer une fois les tests terminés
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from apps.accounting.models import CompteOHADA, Journal
from apps.accounting.serializers import CompteOHADASerializer, JournalSerializer


@require_http_methods(["GET"])
def test_serializers(request):
    """
    Endpoint de test pour vérifier les serializers
    URL: /test-serializers/
    """

    try:
        results = {
            'status': 'success',
            'tests': {}
        }

        # Test 1: Compter les objets
        compte_count = CompteOHADA.objects.count()
        journal_count = Journal.objects.count()

        results['tests']['counts'] = {
            'comptes': compte_count,
            'journaux': journal_count
        }

        # Test 2: Tester CompteOHADASerializer
        if CompteOHADA.objects.exists():
            premier_compte = CompteOHADA.objects.first()
            compte_serializer = CompteOHADASerializer(premier_compte)

            results['tests']['compte_serializer'] = {
                'success': True,
                'data': compte_serializer.data
            }
        else:
            results['tests']['compte_serializer'] = {
                'success': False,
                'error': 'Aucun compte trouvé'
            }

        # Test 3: Tester JournalSerializer
        if Journal.objects.exists():
            premier_journal = Journal.objects.first()
            journal_serializer = JournalSerializer(premier_journal)

            results['tests']['journal_serializer'] = {
                'success': True,
                'data': journal_serializer.data
            }
        else:
            results['tests']['journal_serializer'] = {
                'success': False,
                'error': 'Aucun journal trouvé'
            }

        # Test 4: Tester sérialisation de liste
        comptes_sample = CompteOHADA.objects.all()[:5]
        comptes_serializer = CompteOHADASerializer(comptes_sample, many=True)

        results['tests']['comptes_list'] = {
            'success': True,
            'count': len(comptes_serializer.data),
            'sample': comptes_serializer.data
        }

        # Test 5: Tester validation
        test_data = {
            'code': '12345678',
            'libelle': 'Test Serializer',
            'classe': '1',
            'type': 'passif',
            'ref': 'TS'
        }

        validation_serializer = CompteOHADASerializer(data=test_data)

        results['tests']['validation'] = {
            'is_valid': validation_serializer.is_valid(),
            'errors': validation_serializer.errors if not validation_serializer.is_valid() else None,
            'validated_data': validation_serializer.validated_data if validation_serializer.is_valid() else None
        }

        return JsonResponse(results, json_dumps_params={'indent': 2})

    except Exception as e:
        import traceback
        return JsonResponse({
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


@require_http_methods(["GET"])
def test_serializers_minimal(request):
    """
    Test minimal des serializers
    URL: /test-serializers-minimal/
    """

    try:
        # Test très simple
        compte = CompteOHADA.objects.first()
        journal = Journal.objects.first()

        result = {
            'compte_exists': compte is not None,
            'journal_exists': journal is not None,
        }

        if compte:
            result['compte'] = {
                'id': compte.id,
                'code': compte.code,
                'libelle': compte.libelle,
                'classe': compte.classe,
                'type': compte.type
            }

        if journal:
            result['journal'] = {
                'id': journal.id,
                'code': journal.code,
                'libelle': journal.libelle,
                'type': journal.type
            }

        return JsonResponse(result)

    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)