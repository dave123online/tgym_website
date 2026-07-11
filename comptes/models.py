from django.contrib.auth.models import User
from django.db import models


class Profil(models.Model):
    """
    Rôle applicatif d'un utilisateur Django, en plus de is_staff/is_superuser.

    - STAFF   : admin salle, accès complet (généralement is_staff=True côté Django).
    - COACH   : accès limité — consultation/saisie des contrôles de résultat
                des adhérents qui lui sont confiés (fonctionnalité à venir).
    - ADHERENT: compte client — historique, abonnement en cours (Étape 2).

    On garde le User Django standard (pas de AUTH_USER_MODEL custom) pour ne
    pas toucher aux migrations auth déjà appliquées ; ce modèle ajoute juste
    la couche "rôle métier" par-dessus.
    """

    class Role(models.TextChoices):
        STAFF = "staff", "Staff (admin salle)"
        COACH = "coach", "Coach"
        ADHERENT = "adherent", "Adhérent"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profil")
    role = models.CharField("Rôle", max_length=20, choices=Role.choices, default=Role.ADHERENT)
    telephone = models.CharField(
        "Téléphone", max_length=20, blank=True,
        help_text="Numéro local (ex: 94140535), utilisé pour le contact/relance WhatsApp.",
    )
    date_creation = models.DateTimeField("Créé le", auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} — {self.get_role_display()}"

    def est_staff(self):
        return self.role == self.Role.STAFF

    def est_coach(self):
        return self.role == self.Role.COACH

    def est_adherent(self):
        return self.role == self.Role.ADHERENT

    class Meta:
        verbose_name = "Profil"
        verbose_name_plural = "Profils"
        ordering = ["user__username"]



