// apps/accounting/static/admin/js/ecriture_equilibre.js
// JavaScript pour reproduire l'interactivité Sage dans Django Admin

(function($) {
    'use strict';

    // Variables globales
    let equilibreContainer = null;
    let isCalculating = false;

    // ============================================
    // INITIALISATION AU CHARGEMENT DE LA PAGE
    // ============================================

    $(document).ready(function() {
        console.log('🧮 Initialisation du système d\'équilibre Sage...');

        // Attendre que la page soit complètement chargée
        setTimeout(function() {
            // Initialiser seulement sur les pages d'écritures
            if (isEcriturePage()) {
                initializeSageInterface();
                bindEvents();
                createEquilibreZone();
                calculateEquilibre();

                console.log('✅ Interface Sage initialisée');

                // Debug pour vérifier la présence des éléments
                console.log('📊 Conteneurs trouvés:', $('.tabular.inline-related').length);
                console.log('🎛️ Barre d\'outils:', $('.sage-toolbar').length);
            }
        }, 500); // Délai pour s'assurer que tout est chargé
    });

    // ============================================
    // DETECTION DE LA PAGE D'ECRITURE
    // ============================================

    function isEcriturePage() {
        // Vérifications multiples pour s'assurer qu'on est sur la bonne page
        const urlContainsEcriture = window.location.href.includes('ecriturecomptable');
        const hasTabularInline = $('.tabular.inline-related').length > 0;
        const hasLignesEcriture = $('input[name*="lignes-"]').length > 0;

        console.log('🔍 Détection page:', {
            url: urlContainsEcriture,
            tabular: hasTabularInline,
            lignes: hasLignesEcriture
        });

        return urlContainsEcriture || hasTabularInline || hasLignesEcriture;
    }

    // ============================================
    // INITIALISATION DE L'INTERFACE SAGE
    // ============================================

    function initializeSageInterface() {
        // Ajouter les classes CSS spéciales
        $('.tabular.inline-related').addClass('sage-style');

        // Masquer tous les éléments Django parasites
        hideUnnecessaryElements();

        // Créer la barre d'outils Sage
        createSageToolbar();

        // Styliser les en-têtes de colonnes dans l'ordre Sage
        const headers = ['☑', 'Date(j)', 'Compte', 'Tiers', 'Pièce', 'Libellé', 'Débit', 'Crédit'];
        $('.tabular thead th').each(function(index) {
            if (index < headers.length) {
                $(this).text(headers[index]).show();
            } else {
                // Masquer les colonnes supplémentaires (9ème et plus)
                $(this).hide();
                $('.tabular tbody tr td:nth-child(' + (index + 1) + ')').hide();
            }
        });

        // Ajouter les checkbox de sélection
        addLineSelectors();

        // Formatter les champs montants
        formatMoneyFields();

        // Ajouter des raccourcis clavier
        addKeyboardShortcuts();
    }

    // ============================================
    // MASQUAGE DES ELEMENTS DJANGO PARASITES
    // ============================================

    function hideUnnecessaryElements() {
        // Masquer seulement les éléments vraiment parasites
        const selectorsToHide = [
            '.add-row',
            '.delete-row',
            '.inline-deletelink',
            '.related-widget-wrapper-link',
            'a.add-another',
            'a.related-lookup',
            '.field-DELETE',
            '.DateTimeShortcuts',
            '.datetimeshortcuts',
            '.calendar',
            '.clockbox',
            '.timezonewarning'
        ];

        selectorsToHide.forEach(selector => {
            $(selector).hide();
        });

        // Masquer le texte "Aujourd'hui" qui apparaît sous les champs date
        $('.tabular tbody td').each(function() {
            const text = $(this).text();
            if (text.includes('Aujourd\'hui')) {
                // Masquer seulement le texte en trop, pas le champ
                $(this).contents().filter(function() {
                    return this.nodeType === 3 && this.textContent.includes('Aujourd\'hui');
                }).remove();
            }
        });

        // Ne masquer que les colonnes au-delà de la 8ème
        $('.tabular thead th:nth-child(n+9)').hide();
        $('.tabular tbody td:nth-child(n+9)').hide();

        // Masquer seulement si le texte contient exactement "Supprimer"
        $('.tabular thead th').each(function() {
            const text = $(this).text().trim();
            if (text === 'Supprimer ?' || text === 'SUPPRIMER ?') {
                const index = $(this).index();
                $(this).hide();
                $('.tabular tbody tr td:nth-child(' + (index + 1) + ')').hide();
            }
        });

        // Forcer les bordures sur toutes les cellules
        $('.tabular tbody td').css({
            'border': '1px solid #ecf0f1',
            'border-collapse': 'collapse'
        });
    }

    // ============================================
    // CREATION DE LA BARRE D'OUTILS SAGE
    // ============================================

    function createSageToolbar() {
        // Supprimer l'ancienne barre si elle existe
        $('.sage-toolbar').remove();

        // Créer la barre d'outils
        const toolbar = $(`
            <div class="sage-toolbar">
                <div class="btn-tool btn-delete" data-tooltip="Supprimer la ligne sélectionnée">
                    ❌
                </div>
                <div class="btn-tool btn-add" data-tooltip="Ajouter une nouvelle ligne">
                    ➕
                </div>
                <div class="btn-tool btn-attachment" data-tooltip="Pièces jointes">
                    📎
                </div>
            </div>
        `);

        // Ajouter la barre au conteneur
        $('.tabular.inline-related').prepend(toolbar);

        // Événements des boutons
        bindToolbarEvents();
    }

    function bindToolbarEvents() {
        // Bouton ajouter
        $('.sage-toolbar .btn-add').on('click', function() {
            $('.add-row a').click();
            setTimeout(function() {
                initializeNewRow();
                calculateEquilibre();
            }, 100);
        });

        // Bouton supprimer
        $('.sage-toolbar .btn-delete').on('click', function() {
            if ($(this).hasClass('active')) {
                const selectedRow = $('.tabular tbody tr.selected');
                if (selectedRow.length) {
                    if (confirm('Supprimer cette ligne ?')) {
                        selectedRow.find('.delete-row input[type="checkbox"]').prop('checked', true);
                        selectedRow.addClass('to-delete').fadeOut();
                        updateDeleteButton();
                        setTimeout(calculateEquilibre, 200);
                    }
                }
            }
        });

        // Bouton pièces jointes
        $('.sage-toolbar .btn-attachment').on('click', function() {
            // TODO: Implémenter la gestion des pièces jointes
            showAlert('🔧 Fonctionnalité pièces jointes à venir', 'info');
        });
    }

    // ============================================
    // GESTION DES SELECTIONS DE LIGNES
    // ============================================

    function addLineSelectors() {
        // Ajouter une checkbox de sélection à chaque ligne
        $('.tabular tbody tr').each(function() {
            if (!$(this).hasClass('empty-form') && !$(this).find('.sage-line-selector').length) {
                const selector = $('<input type="checkbox" class="sage-line-selector">');
                $(this).find('td:first').prepend(selector);

                // Événement de sélection
                selector.on('change', function() {
                    const row = $(this).closest('tr');
                    if ($(this).is(':checked')) {
                        // Déselectionner les autres lignes
                        $('.sage-line-selector').not(this).prop('checked', false);
                        $('.tabular tbody tr').removeClass('selected');
                        row.addClass('selected');
                    } else {
                        row.removeClass('selected');
                    }
                    updateDeleteButton();
                });
            }
        });
    }

    function updateDeleteButton() {
        const hasSelection = $('.tabular tbody tr.selected').length > 0;
        const deleteBtn = $('.sage-toolbar .btn-delete');

        if (hasSelection) {
            deleteBtn.addClass('active');
        } else {
            deleteBtn.removeClass('active');
        }
    }

    // ============================================
    // CREATION DE LA ZONE D'EQUILIBRE SAGE
    // ============================================

    function createEquilibreZone() {
        // Supprimer l'ancienne zone si elle existe
        $('.equilibre-container').remove();

        // Créer la nouvelle zone d'équilibre
        equilibreContainer = $(`
            <div class="equilibre-container">
                <div class="equilibre-totaux">
                    <span class="total-debit">Débit: <strong>0,00</strong></span>
                    <span class="total-credit">Crédit: <strong>0,00</strong></span>
                    <span class="difference">Différence: <strong>0,00</strong></span>
                </div>
                <div class="equilibre-status">
                    <span class="equilibre-indicator"></span>
                    <span class="status-text">En cours de saisie...</span>
                </div>
            </div>
        `);

        // Ajouter après le tableau
        $('.tabular.inline-related').append(equilibreContainer);
    }

    // ============================================
    // CALCUL DE L'EQUILIBRE TEMPS REEL
    // ============================================

    function calculateEquilibre() {
        if (isCalculating) return;
        isCalculating = true;

        try {
            let totalDebit = 0;
            let totalCredit = 0;
            let lignesValides = 0;

            // Parcourir toutes les lignes d'écriture
            $('.tabular tbody tr').each(function() {
                if ($(this).hasClass('empty-form') || $(this).hasClass('add-row')) {
                    return; // Ignorer les lignes vides et d'ajout
                }

                const debitField = $(this).find('input[name*="montant_debit"]');
                const creditField = $(this).find('input[name*="montant_credit"]');
                const compteField = $(this).find('select[name*="compte"]');

                // Vérifier si la ligne a un compte sélectionné
                if (compteField.val()) {
                    const debit = parseFloat(debitField.val()) || 0;
                    const credit = parseFloat(creditField.val()) || 0;

                    // Validation : pas de débit ET crédit simultanés
                    if (debit > 0 && credit > 0) {
                        showFieldError(debitField, 'Une ligne ne peut avoir débit ET crédit');
                        showFieldError(creditField, 'Une ligne ne peut avoir débit ET crédit');
                    } else {
                        clearFieldError(debitField);
                        clearFieldError(creditField);
                    }

                    totalDebit += debit;
                    totalCredit += credit;

                    if (debit > 0 || credit > 0) {
                        lignesValides++;
                    }
                }
            });

            // Mettre à jour l'affichage
            updateEquilibreDisplay(totalDebit, totalCredit, lignesValides);

        } catch (error) {
            console.error('❌ Erreur calcul équilibre:', error);
        } finally {
            isCalculating = false;
        }
    }

    // ============================================
    // MISE A JOUR DE L'AFFICHAGE EQUILIBRE
    // ============================================

    function updateEquilibreDisplay(totalDebit, totalCredit, lignesValides) {
        if (!equilibreContainer) return;

        const difference = totalDebit - totalCredit;
        const isEquilibree = Math.abs(difference) < 0.01 && totalDebit > 0;

        // Mettre à jour les totaux
        equilibreContainer.find('.total-debit strong').text(formatMoney(totalDebit));
        equilibreContainer.find('.total-credit strong').text(formatMoney(totalCredit));
        equilibreContainer.find('.difference strong').text(formatMoney(Math.abs(difference)));

        // Mettre à jour le statut
        const indicator = equilibreContainer.find('.equilibre-indicator');
        const statusText = equilibreContainer.find('.status-text');

        if (lignesValides === 0) {
            indicator.removeClass('ok error').addClass('empty');
            statusText.text('Aucune ligne saisie');
        } else if (isEquilibree) {
            indicator.removeClass('error empty').addClass('ok');
            statusText.text(`✓ Équilibrée (${lignesValides} lignes)`);
            equilibreContainer.removeClass('error').addClass('success');
        } else {
            indicator.removeClass('ok empty').addClass('error');
            const ecartText = difference > 0 ? 'Débit supérieur' : 'Crédit supérieur';
            statusText.text(`❌ ${ecartText} (${formatMoney(Math.abs(difference))})`);
            equilibreContainer.removeClass('success').addClass('error');
        }

        // Notifier le serveur si nécessaire
        notifyEquilibreChange(totalDebit, totalCredit, isEquilibree);
    }

    // ============================================
    // FORMATAGE DES MONTANTS
    // ============================================

    function formatMoney(amount) {
        return new Intl.NumberFormat('fr-FR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(amount);
    }

    function formatMoneyFields() {
        // Formater les champs montants lors de la frappe
        $(document).on('input blur', 'input[name*="montant_debit"], input[name*="montant_credit"]', function() {
            let value = $(this).val().replace(/[^\d.,]/g, '');
            value = value.replace(',', '.');

            if (value && !isNaN(value)) {
                const numValue = parseFloat(value);
                if ($(this).is(':focus')) {
                    $(this).val(numValue);
                } else {
                    $(this).val(formatMoney(numValue));
                }
            }
        });
    }

    // ============================================
    // GESTION DES EVENEMENTS
    // ============================================

    function bindEvents() {
        // Calcul automatique lors des changements
        $(document).on('input change', 'input[name*="montant_debit"], input[name*="montant_credit"]', function() {
            $(this).closest('tr').addClass('editing');
            setTimeout(calculateEquilibre, 100);
        });

        // Validation des tiers selon le compte
        $(document).on('change', 'select[name*="compte"]', function() {
            validateTiersForAccount($(this));
            calculateEquilibre();
        });

        // Auto-complétion du libellé
        $(document).on('change', 'select[name*="compte"], input[name*="piece"]', function() {
            autoCompleteLibelle($(this).closest('tr'));
        });

        // Gestion des nouvelles lignes
        $(document).on('click', '.add-row a', function() {
            setTimeout(function() {
                addLineSelectors();
                initializeNewRow();
                calculateEquilibre();
            }, 100);
        });

        // Suppression de lignes
        $(document).on('click', '.delete-row', function() {
            setTimeout(calculateEquilibre, 100);
        });

        // Validation en temps réel
        $(document).on('blur', 'input, select', function() {
            $(this).closest('tr').removeClass('editing');
            validateField($(this));
        });
    }

    // ============================================
    // VALIDATION DES CHAMPS
    // ============================================

    function validateTiersForAccount(compteField) {
        const compteCode = compteField.find('option:selected').text();
        const tiersField = compteField.closest('tr').find('select[name*="tiers"]');

        if (compteCode && compteCode.startsWith('4')) {
            // Compte de classe 4 : tiers obligatoire
            tiersField.prop('required', true);
            if (!tiersField.val()) {
                showFieldError(tiersField, 'Tiers obligatoire pour les comptes de classe 4');
            }
        } else {
            // Autres comptes : tiers optionnel
            tiersField.prop('required', false);
            clearFieldError(tiersField);
        }
    }

    function validateField(field) {
        clearFieldError(field);

        const value = field.val();
        const fieldName = field.attr('name') || '';

        // Validation spécifique selon le type de champ
        if (fieldName.includes('montant_')) {
            if (value && (isNaN(value) || parseFloat(value) < 0)) {
                showFieldError(field, 'Montant invalide');
                return false;
            }
        }

        return true;
    }

    // ============================================
    // GESTION DES ERREURS
    // ============================================

    function showFieldError(field, message) {
        clearFieldError(field);

        field.addClass('error');
        const errorDiv = $(`<div class="field-error">${message}</div>`);
        field.after(errorDiv);

        // Supprimer automatiquement après 5 secondes
        setTimeout(() => clearFieldError(field), 5000);
    }

    function clearFieldError(field) {
        field.removeClass('error');
        field.siblings('.field-error').remove();
    }

    // ============================================
    // AUTO-COMPLETION INTELLIGENTE
    // ============================================

    function autoCompleteLibelle(row) {
        const compteField = row.find('select[name*="compte"]');
        const pieceField = row.find('input[name*="piece"]');
        const libelleField = row.find('input[name*="libelle"]');

        // Si le libellé est vide, essayer de le remplir automatiquement
        if (!libelleField.val()) {
            const compteText = compteField.find('option:selected').text();
            const pieceText = pieceField.val();

            let autoLibelle = '';

            if (pieceText) {
                autoLibelle = pieceText.toUpperCase();
            } else if (compteText) {
                // Extraire le libellé du compte
                const match = compteText.match(/^\d+\s*-\s*(.+)$/);
                if (match) {
                    autoLibelle = match[1].substring(0, 30);
                }
            }

            if (autoLibelle) {
                libelleField.val(autoLibelle);
            }
        }
    }

    // ============================================
    // INITIALISATION NOUVELLE LIGNE
    // ============================================

    function initializeNewRow() {
        const newRow = $('.tabular tbody tr').last();

        // Ajouter le sélecteur de ligne
        addLineSelectors();

        // Auto-numérotation
        const numeroField = newRow.find('input[name*="numero_ligne"]');
        if (!numeroField.val()) {
            const maxNumero = Math.max(0, ...$('input[name*="numero_ligne"]').map(function() {
                return parseInt($(this).val()) || 0;
            }).get());
            numeroField.val(maxNumero + 1);
        }

        // Auto-remplir la date de ligne avec la date de l'écriture
        const dateField = newRow.find('input[name*="date_ligne"]');
        if (!dateField.val()) {
            const ecritureDate = $('#id_date_ecriture').val();
            if (ecritureDate) {
                const date = new Date(ecritureDate);
                dateField.val(date.getDate()); // Juste le jour
            }
        }

        // Focus sur le compte
        newRow.find('select[name*="compte"]').focus();
    }

    // ============================================
    // RACCOURCIS CLAVIER SAGE
    // ============================================

    function addKeyboardShortcuts() {
        $(document).on('keydown', function(e) {
            // Ctrl + Entrée : Valider l'écriture
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                submitEcriture();
            }

            // F9 : Ajouter une ligne
            if (e.key === 'F9') {
                e.preventDefault();
                $('.add-row a').click();
            }

            // Échap : Annuler la saisie en cours
            if (e.key === 'Escape') {
                $('input:focus, select:focus').blur();
                clearAllErrors();
            }
        });

        // Navigation avec Tab entre les colonnes importantes
        $(document).on('keydown', 'input, select', function(e) {
            if (e.key === 'Tab') {
                // Logique de navigation intelligente
                const currentRow = $(this).closest('tr');
                const currentField = $(this);

                if (e.shiftKey) {
                    // Tab inverse
                    navigateToPreviousField(currentField, currentRow);
                } else {
                    // Tab normal
                    navigateToNextField(currentField, currentRow);
                }
            }
        });
    }

    function navigateToNextField(currentField, currentRow) {
        const fieldOrder = ['compte', 'tiers', 'piece', 'libelle', 'montant_debit', 'montant_credit'];
        const currentFieldName = currentField.attr('name') || '';

        let currentIndex = -1;
        for (let i = 0; i < fieldOrder.length; i++) {
            if (currentFieldName.includes(fieldOrder[i])) {
                currentIndex = i;
                break;
            }
        }

        if (currentIndex >= 0 && currentIndex < fieldOrder.length - 1) {
            const nextFieldName = fieldOrder[currentIndex + 1];
            const nextField = currentRow.find(`[name*="${nextFieldName}"]`);
            if (nextField.length) {
                nextField.focus();
                return false;
            }
        }
    }

    // ============================================
    // SOUMISSION ET VALIDATION
    // ============================================

    function submitEcriture() {
        // Vérifier l'équilibre avant soumission
        calculateEquilibre();

        if (!equilibreContainer.hasClass('success')) {
            showAlert('❌ L\'écriture doit être équilibrée avant validation', 'error');
            return false;
        }

        // Vérifier qu'il y a au moins 2 lignes
        const lignesValides = $('.tabular tbody tr').filter(function() {
            const compte = $(this).find('select[name*="compte"]').val();
            const debit = parseFloat($(this).find('input[name*="montant_debit"]').val()) || 0;
            const credit = parseFloat($(this).find('input[name*="montant_credit"]').val()) || 0;
            return compte && (debit > 0 || credit > 0);
        }).length;

        if (lignesValides < 2) {
            showAlert('❌ Une écriture doit contenir au moins 2 lignes', 'error');
            return false;
        }

        // Soumettre le formulaire
        $('form').submit();
    }

    // ============================================
    // NOTIFICATION SERVEUR
    // ============================================

    function notifyEquilibreChange(totalDebit, totalCredit, isEquilibree) {
        // Mettre à jour les champs cachés si ils existent
        $('input[name="montant_total"]').val(totalDebit.toFixed(2));
        $('input[name="is_equilibree"]').prop('checked', isEquilibree);

        // Optionnel : notification AJAX au serveur
        const ecritureId = getEcritureId();
        if (ecritureId && window.location.pathname.includes('change')) {
            // Seulement pour les écritures existantes en modification
            $.ajax({
                url: '/admin/accounting/ecriturecomptable/equilibre-ajax/',
                method: 'POST',
                data: {
                    'ecriture_id': ecritureId,
                    'total_debit': totalDebit.toFixed(2),
                    'total_credit': totalCredit.toFixed(2),
                    'is_equilibree': isEquilibree,
                    'csrfmiddlewaretoken': $('[name=csrfmiddlewaretoken]').val()
                },
                success: function(response) {
                    if (!response.success) {
                        console.warn('⚠️ Erreur serveur équilibre:', response.error);
                    }
                },
                error: function() {
                    // Erreur silencieuse, pas critique
                }
            });
        }
    }

    // ============================================
    // UTILITAIRES
    // ============================================

    function getEcritureId() {
        const match = window.location.pathname.match(/\/(\d+)\/change/);
        return match ? match[1] : null;
    }

    function clearAllErrors() {
        $('.error').removeClass('error');
        $('.field-error').remove();
    }

    function showAlert(message, type = 'info') {
        // Créer une notification temporaire
        const alertDiv = $(`
            <div class="alert alert-${type}" style="position: fixed; top: 20px; right: 20px; z-index: 9999; padding: 10px 15px; border-radius: 5px; background: ${type === 'error' ? '#f8d7da' : '#d4edda'}; border: 1px solid ${type === 'error' ? '#f5c6cb' : '#c3e6cb'}; color: ${type === 'error' ? '#721c24' : '#155724'};">
                ${message}
            </div>
        `);

        $('body').append(alertDiv);

        setTimeout(() => {
            alertDiv.fadeOut(() => alertDiv.remove());
        }, 5000);
    }

    // ============================================
    // DEBUG ET LOGS
    // ============================================

    function debugEquilibre() {
        console.group('🔍 Debug Équilibre Sage');
        console.log('Total lignes:', $('.tabular tbody tr').length);
        console.log('Lignes valides:', $('.tabular tbody tr').filter(function() {
            return $(this).find('select[name*="compte"]').val();
        }).length);
        console.log('Container équilibre:', equilibreContainer);
        console.groupEnd();
    }

    // Exposer pour debug
    window.SageEquilibre = {
        calculate: calculateEquilibre,
        debug: debugEquilibre,
        format: formatMoney
    };

})(django.jQuery || jQuery);

console.log('🚀 Module Équilibre Sage chargé');