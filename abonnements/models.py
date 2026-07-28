from datetime import date, timedelta

from django.conf import settings
from django.db import models


class Plan(models.Model):
    """
    Une formule tarifaire T-GYM (Premium mensuel ou formule flexible).
    Modèle volontairement simple : pas de tailles, pas de multi-devise —
    une salle de sport a une poignée de formules, pas un catalogue.
    """

    class Categorie(models.TextChoices):
        PREMIUM = "premium", "Abonnement Standard (Premium)"
        FLEXIBLE = "flexible", "Formule flexible (à la carte)"

    nom = models.CharField("Nom de la formule", max_length=100)
    categorie = models.CharField(
        "Catégorie", max_length=20, choices=Categorie.choices, default=Categorie.FLEXIBLE
    )
    prix_fcfa = models.PositiveIntegerField("Prix (FCFA)")
    periode = models.CharField(
        "Période", max_length=50, help_text="Ex: /mois, pour 14 séances/mois, /semaine"
    )
    duree_jours = models.PositiveIntegerField(
        "Durée (jours)", null=True, blank=True,
        help_text="Utilisée pour calculer automatiquement la date de fin d'un abonnement "
                   "(ex: 30 pour un mensuel). Laisser vide pour les formules sans durée "
                   "calculable (ex: à la carte) — la date de fin restera alors saisie manuellement.",
    )
    description_courte = models.CharField(
        "Description courte", max_length=150, blank=True,
        help_text="Ex: '14 séances dans le mois'"
    )
    inclus = models.JSONField(
        "Éléments inclus", default=list, blank=True,
        help_text="Liste de points affichés sous forme de checklist (ex: ['Accès salle', 'Suivi coach permanent'])",
    )
    is_populaire = models.BooleanField(
        "Mettre en avant", default=False,
        help_text="Affiche cette formule comme le choix recommandé sur la grille tarifaire."
    )
    actif = models.BooleanField("Actif (visible sur le site)", default=True)
    ordre_affichage = models.PositiveIntegerField("Ordre d'affichage", default=0)

    def prix_affiche(self) -> str:
        return f"{self.prix_fcfa:,} FCFA {self.periode}".replace(",", ".")

    def __str__(self):
        return f"{self.nom} — {self.prix_affiche()}"

    class Meta:
        verbose_name = "Formule tarifaire"
        verbose_name_plural = "Formules tarifaires"
        ordering = ["ordre_affichage", "prix_fcfa"]


class Abonnement(models.Model):
    """
    Souscription d'un user à une formule (Plan), avec historique.

    Un user peut avoir plusieurs Abonnement dans le temps (renouvellements,
    changements de formule). `actif` + `est_en_cours()` permettent de
    retrouver rapidement l'abonnement courant sans supprimer l'historique.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="abonnements", verbose_name="Adhérent",
    )
    plan = models.ForeignKey(
        Plan, on_delete=models.PROTECT,
        related_name="abonnements", verbose_name="Formule",
    )
    date_debut = models.DateField("Date de début", default=date.today)
    date_fin = models.DateField(
        "Date de fin", null=True, blank=True,
        help_text="Calculée automatiquement si la formule a une durée définie (écrase la saisie "
                   "manuelle à chaque enregistrement). Sinon, à renseigner à la main.",
    )
    actif = models.BooleanField(
        "Actif", default=True,
        help_text="Décoche pour clore/annuler cet abonnement sans le supprimer.",
    )
    date_creation = models.DateTimeField("Créé le", auto_now_add=True)

    def save(self, *args, **kwargs):
        # Si la formule a une durée définie, la date de fin est toujours
        # recalculée depuis date_debut + duree_jours (écrase toute saisie
        # manuelle). Sinon (formule "à la carte" sans duree_jours), on ne
        # touche pas à date_fin — laissée à la main du staff.
        if self.plan_id and self.plan.duree_jours is not None:
            self.date_fin = self.date_debut + timedelta(days=self.plan.duree_jours)
        super().save(*args, **kwargs)

    def est_en_cours(self) -> bool:
        if not self.actif:
            return False
        if self.date_fin and self.date_fin < date.today():
            return False
        return self.date_debut <= date.today()

    est_en_cours.boolean = True
    est_en_cours.short_description = "En cours"

    def jours_restants(self):
        """Nombre de jours avant expiration, ou None si pas de date_fin définie."""
        if not self.date_fin:
            return None
        return (self.date_fin - date.today()).days

    def __str__(self):
        return f"{self.user.get_username()} — {self.plan.nom} ({self.date_debut})"

    class Meta:
        verbose_name = "Abonnement"
        verbose_name_plural = "Abonnements"
        ordering = ["-date_debut", "-date_creation"]


class RelanceMessage(models.Model):
    """
    Message de relance généré (via IA) pour un abonnement qui arrive à
    expiration. Tant que l'Étape 4 (API WhatsApp Business) n'est pas
    branchée, ces messages restent au statut A_ENVOYER : le staff les
    consulte dans l'admin et les copie manuellement vers WhatsApp.
    """

    class Statut(models.TextChoices):
        A_ENVOYER = "a_envoyer", "À envoyer (copier manuellement)"
        ENVOYE = "envoye", "Envoyé"
        IGNORE = "ignore", "Ignoré"

    abonnement = models.ForeignKey(
        Abonnement, on_delete=models.CASCADE,
        related_name="relances", verbose_name="Abonnement",
    )
    date_expiration_ciblee = models.DateField(
        "Date d'expiration ciblée",
        help_text="Copie de la date de fin de l'abonnement au moment de la génération — "
                   "sert à éviter de régénérer un message pour la même échéance.",
    )
    contenu = models.TextField("Message généré")
    genere_par_ia = models.BooleanField(
        "Généré par l'IA", default=True,
        help_text="Décoché si l'IA était indisponible au moment de la génération "
                   "et qu'un message de secours (gabarit fixe) a été utilisé à la place.",
    )
    statut = models.CharField(
        "Statut", max_length=20, choices=Statut.choices, default=Statut.A_ENVOYER,
    )
    date_generation = models.DateTimeField("Généré le", auto_now_add=True)
    envoye_le = models.DateTimeField("Envoyé le", null=True, blank=True)
    envoye_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="relances_envoyees", verbose_name="Envoyé par",
        help_text="Membre du staff qui a envoyé le message manuellement. "
                   "Vide si l'envoi a été automatique (voir « Envoyé automatiquement »).",
    )
    envoye_automatiquement = models.BooleanField(
        "Envoyé automatiquement", default=False,
        help_text="Coché si envoyé via l'API WhatsApp Business (Étape 4), "
                   "décoché si envoyé/à envoyer manuellement par le staff.",
    )

    def __str__(self):
        return f"Relance {self.abonnement} — {self.get_statut_display()}"

    class Meta:
        verbose_name = "Message de relance"
        verbose_name_plural = "Messages de relance"
        ordering = ["-date_generation"]
class ConversationWhatsApp(models.Model):
    """
    Regroupe les échanges WhatsApp avec un numéro donné. Une conversation
    par numéro de contact — pas de notion de fenêtre 24h ici, c'est un
    regroupement d'affichage, pas une entité facturée par Meta.
    """

    wa_id = models.CharField(
        "Numéro WhatsApp (wa_id)", max_length=20, unique=True,
        help_text="Numéro au format international sans '+', ex: 22997393766",
    )
    nom_contact = models.CharField(
        "Nom du contact", max_length=150, blank=True,
        help_text="Renseigné automatiquement depuis le profil WhatsApp si disponible.",
    )
    abonnement = models.ForeignKey(
        Abonnement, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="conversations_whatsapp", verbose_name="Abonnement lié",
        help_text="Rapproché manuellement si besoin — aucun lien automatique par défaut.",
    )
    derniere_activite = models.DateTimeField("Dernière activité", auto_now=True)

    class ModeBot(models.TextChoices):
        BOT = "bot", "Gemini répond automatiquement"
        HUMAIN = "humain", "Escaladé — réponse humaine requise"

    mode_bot = models.CharField(
        "Mode de réponse", max_length=10, choices=ModeBot.choices, default=ModeBot.BOT,
        help_text="Passe automatiquement en 'Humain' si le client se montre insatisfait ou si "
                   "Gemini ne sait pas répondre. Remets sur 'Bot' une fois la situation gérée.",
    )
    raison_escalade = models.CharField("Raison de l'escalade", max_length=255, blank=True)

    def __str__(self):
        return self.nom_contact or self.wa_id

    class Meta:
        verbose_name = "Conversation WhatsApp"
        verbose_name_plural = "Conversations WhatsApp"
        ordering = ["-derniere_activite"]


class MessageWhatsApp(models.Model):
    """
    Un message individuel (entrant ou sortant) au sein d'une conversation.
    Le champ `est_facturable` reflète les règles de facturation Meta en
    vigueur : un template envoyé proactivement (hors fenêtre de service
    ouverte) est facturé, une réponse libre ou un template Utility envoyé
    en réponse dans les 24h ne l'est pas.
    """

    class Sens(models.TextChoices):
        ENTRANT = "entrant", "Reçu du client"
        SORTANT = "sortant", "Envoyé par T GYM"

    class Categorie(models.TextChoices):
        SESSION = "session", "Message libre (session 24h)"
        MARKETING = "marketing", "Template Marketing"
        UTILITY = "utility", "Template Utility"
        AUTHENTICATION = "authentication", "Template Authentication"

    conversation = models.ForeignKey(
        ConversationWhatsApp, on_delete=models.CASCADE,
        related_name="messages", verbose_name="Conversation",
    )
    sens = models.CharField("Sens", max_length=10, choices=Sens.choices)
    wamid = models.CharField(
        "ID message (wamid)", max_length=150, unique=True, null=True, blank=True,
        help_text="Identifiant Meta du message — sert à éviter les doublons sur retry webhook.",
    )
    contenu = models.TextField("Contenu")
    categorie = models.CharField(
        "Catégorie", max_length=20, choices=Categorie.choices, default=Categorie.SESSION,
    )
    est_facturable = models.BooleanField(
        "Facturé par Meta", default=False,
        help_text="Coché si ce message correspond à un envoi facturé selon les règles Meta "
                   "en vigueur (template hors fenêtre de service).",
    )
    statut_livraison = models.CharField(
        "Statut de livraison", max_length=20, blank=True,
        help_text="sent / delivered / read / failed — mis à jour via les webhooks 'statuses'.",
    )
    date_envoi = models.DateTimeField("Date", auto_now_add=True)
    payload_brut = models.JSONField(
        "Payload brut", null=True, blank=True,
        help_text="Copie du payload webhook Meta pour ce message, utile pour du débug.",
    )

    def __str__(self):
        return f"{self.get_sens_display()} — {self.conversation} ({self.date_envoi:%d/%m %H:%M})"

    class Meta:
        verbose_name = "Message WhatsApp"
        verbose_name_plural = "Messages WhatsApp"
        ordering = ["date_envoi"]


class ContactMasse(models.Model):
    """
    Liste éditable de contacts pour l'envoi de messages WhatsApp en masse
    (annonces, promos...) — indépendante des Abonnement/User, pour couvrir
    aussi les prospects ou anciens clients qui n'ont pas de compte.
    """

    nom = models.CharField("Nom", max_length=150)
    telephone = models.CharField(
        "Téléphone", max_length=20,
        help_text="Format international, ex: 22997393766 ou +22997393766.",
    )
    actif = models.BooleanField(
        "Actif", default=True,
        help_text="Décoche pour exclure ce contact des prochains envois en masse sans le supprimer.",
    )
    note = models.CharField("Note", max_length=255, blank=True)
    date_ajout = models.DateTimeField("Ajouté le", auto_now_add=True)

    def __str__(self):
        return f"{self.nom} ({self.telephone})"

    class Meta:
        verbose_name = "Contact (envoi de masse)"
        verbose_name_plural = "Contacts (envoi de masse)"
        ordering = ["nom"]


def synchroniser_contact_masse_pour_user(user) -> None:
    """
    Recalcule ContactMasse.actif pour le contact correspondant à `user`, à
    partir du rôle de son Profil ET de son statut d'abonnement réel
    (Abonnement.est_en_cours()) — pas seulement du rôle : un adhérent dont
    l'abonnement a expiré ne doit pas rester compté comme actif dans la
    liste de diffusion tant qu'il n'a pas renouvelé.

    Appelée depuis deux points, pour rester à jour dans les deux sens :
      - comptes.signals (post_save sur Profil) : rôle qui devient/reste
        ADHERENT, ou téléphone renseigné après coup.
      - abonnements.signals (post_save sur Abonnement) : nouvel
        abonnement souscrit, renouvelé, ou expiré/résilié (actif=False).

    Ne crée jamais de contact ici (uniquement mis à jour si déjà
    existant) — la création reste la responsabilité de comptes.signals,
    déclenchée au moment où le rôle passe à ADHERENT.

    Import de Profil fait localement pour éviter toute dépendance
    circulaire au chargement des apps entre `abonnements` et `comptes`.
    """
    from comptes.models import Profil
    from core.whatsapp import numero_international

    profil = getattr(user, "profil", None)
    if profil is None or profil.role != Profil.Role.ADHERENT or not profil.telephone:
        return

    telephone = numero_international(profil.telephone)
    contact = ContactMasse.objects.filter(telephone=telephone).first()
    if contact is None:
        return

    en_cours = any(a.est_en_cours() for a in user.abonnements.all())
    if contact.actif != en_cours:
        contact.actif = en_cours
        contact.save(update_fields=["actif"])


class TemplateWhatsApp(models.Model):
    """
    Référence un template WhatsApp pré-approuvé par Meta, avec la liste de
    ses variables — sert de source de vérité pour l'écran de diffusion,
    afin que le staff choisisse un template par son intitulé plutôt que de
    retaper le nom technique Meta à chaque envoi.
    """

    intitule = models.CharField(
        "Intitulé (affiché au staff)", max_length=100, unique=True,
        help_text="Ex: Promo rentrée, Relance abonnement...",
    )
    nom_meta = models.CharField(
        "Nom technique du template (Meta)", max_length=100,
        help_text="Doit correspondre EXACTEMENT au nom du template approuvé dans le dashboard Meta.",
    )
    categorie = models.CharField(
        "Catégorie Meta", max_length=20, choices=MessageWhatsApp.Categorie.choices,
        default=MessageWhatsApp.Categorie.MARKETING,
        help_text="Doit correspondre à la catégorie approuvée sur Meta (Marketing/Utility/Authentication) "
                   "— utilisée pour un suivi correct de la facturation dans les conversations.",
    )
    langue = models.CharField("Code langue", max_length=10, default="fr")
    variables = models.JSONField(
        "Variables du corps, dans l'ordre", default=list, blank=True,
        help_text='Liste des noms de variables dans l\'ordre {{1}}, {{2}}... '
                   'Ex: ["prenom", "nom_promo"]. Laisser vide si le template n\'a pas de variable.',
    )
    actif = models.BooleanField("Actif (proposé dans la diffusion)", default=True)
    date_creation = models.DateTimeField("Créé le", auto_now_add=True)

    def __str__(self):
        return self.intitule

    class Meta:
        verbose_name = "Template WhatsApp"
        verbose_name_plural = "Templates WhatsApp"
        ordering = ["intitule"]


