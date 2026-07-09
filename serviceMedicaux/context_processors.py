from _auth.models import ServiceMedicaux
from serviceMedicaux.models import DemandeDeSang


def demandes_badge(request):
    """Compte des demandes « En attente » pour le badge du menu, selon le rôle.

    - blood_bank : toutes les demandes en attente rattachées à un service (à traiter).
    - medical    : les demandes du service courant en attente (de réponse).

    Rendu au premier chargement de la page ; ensuite rafraîchi côté client par le
    script de polling. Renvoie aussi le nom d'URL de l'item de menu à décorer.
    """
    user = getattr(request, 'user', None)
    if user is None or not getattr(user, 'is_authenticated', False):
        return {'demandes_badge_count': 0, 'demandes_badge_url_name': None}

    role = getattr(user, 'role', None)
    count = 0
    url_name = None

    if role == 'blood_bank':
        count = DemandeDeSang.objects.filter(
            etat='En attente', serviceMedicaux__isnull=False,
        ).count()
        url_name = 'listeDemandesDeSang'
    elif role == 'medical':
        url_name = 'mesDemandesDeSang'
        try:
            service = user.service_medical
        except ServiceMedicaux.DoesNotExist:
            service = None
        if service is not None:
            count = DemandeDeSang.objects.filter(
                etat='En attente', serviceMedicaux=service,
            ).count()

    return {'demandes_badge_count': count, 'demandes_badge_url_name': url_name}
