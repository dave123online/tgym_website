import secrets
import string

from django import forms
from django.contrib.auth.models import User
from django.utils.text import slugify

from abonnements.models import Plan

from .utils import normaliser_telephone


def generer_mot_de_passe(longueur: int = 10) -> str:
    """
    Génère un mot de passe aléatoire lisible (lettres + chiffres).
    Pas de caractères ambigus (0/O, 1/l/I) pour limiter les erreurs de
    recopie manuelle par le staff vers WhatsApp.
    """
    alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(longueur))


def generer_username(nom_complet: str) -> str:
    """
    Génère un identifiant de connexion à partir du nom du client
    (ex: "Awa Koffi" -> "awakoffi"), en ajoutant un suffixe numérique
    si l'identifiant est déjà pris.
    """
    base = slugify(nom_complet).replace("-", "") or "client"
    username = base
    compteur = 1
    while User.objects.filter(username__iexact=username).exists():
        compteur += 1
        username = f"{base}{compteur}"
    return username


class CreationCompteAdherentForm(forms.Form):
    """
    Formulaire staff : juste le nom du client + son numéro WhatsApp.
    L'identifiant de connexion ET le mot de passe sont générés côté serveur
    à la validation, puis affichés une seule fois au staff (charge à lui de
    les transmettre).
    """
    nom_complet = forms.CharField(
        label="Nom complet du client",
        max_length=150,
        help_text="Utilisé pour générer automatiquement l'identifiant de connexion.",
    )
    telephone = forms.CharField(
        label="Numéro WhatsApp du client",
        max_length=20,
        help_text="Numéro local (ex: 94140535) ou déjà préfixé 229.",
    )
    plan = forms.ModelChoiceField(
        label="Formule initiale",
        queryset=Plan.objects.filter(actif=True),
        required=False,
        empty_label="— Aucune (à ajouter plus tard) —",
    )

    def clean_nom_complet(self):
        nom = self.cleaned_data["nom_complet"].strip()
        if not nom:
            raise forms.ValidationError("Le nom est requis.")
        return nom

    def clean_telephone(self):
        return normaliser_telephone(self.cleaned_data["telephone"])



