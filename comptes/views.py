from abonnements.models import Abonnement
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .decorators import role_required
from .forms import CreationCompteAdherentForm, generer_mot_de_passe, generer_username
from .models import Profil


class ConnexionView(auth_views.LoginView):
    template_name = "comptes/connexion.html"
    redirect_authenticated_user = True


class DeconnexionView(auth_views.LogoutView):
    next_page = "core:accueil"


@login_required
def mon_espace(request):
    """
    Point d'entrée unique après connexion, qui affiche le bon contenu selon
    le rôle. Pour un adhérent : abonnement en cours + historique (Étape 2).
    La saisie coach reste à brancher (fonctionnalité de contrôle de résultat).
    """
    profil = getattr(request.user, "profil", None)
    abonnement_actif = None
    historique_abonnements = []

    if profil is not None and profil.est_adherent():
        abonnements = list(
            Abonnement.objects.filter(user=request.user)
            .select_related("plan")
            .order_by("-date_debut", "-date_creation")
        )
        for a in abonnements:
            if a.est_en_cours() and abonnement_actif is None:
                abonnement_actif = a
            else:
                historique_abonnements.append(a)

    return render(request, "comptes/mon_espace.html", {
        "profil": profil,
        "abonnement_actif": abonnement_actif,
        "historique_abonnements": historique_abonnements,
    })


@role_required(Profil.Role.STAFF)
def creer_compte_adherent(request):
    """
    Remplace le flow "staff crée le compte à la main depuis l'admin" :
    le staff ne saisit qu'un identifiant + un numéro WhatsApp, le mot de
    passe est généré aléatoirement côté serveur puis affiché une seule
    fois pour que le staff le transmette au client (WhatsApp, en main
    propre, etc.). Le Profil (rôle adhérent) est créé automatiquement par
    le signal `creer_profil` sur la création du User ; on complète juste
    le téléphone ici.

    Pattern Post/Redirect/Get : après soumission on redirige vers la même
    vue en GET, avec les identifiants générés stockés en session le temps
    d'un seul affichage (ils sont retirés dès la lecture) — un rafraîchi-
    ssement de page ne les réaffiche pas, pour éviter qu'ils traînent.
    """
    identifiants = request.session.pop("identifiants_generes", None)

    if request.method == "POST":
        form = CreationCompteAdherentForm(request.POST)
        if form.is_valid():
            nom_complet = form.cleaned_data["nom_complet"]
            telephone = form.cleaned_data["telephone"]
            plan = form.cleaned_data["plan"]
            username = generer_username(nom_complet)
            mot_de_passe = generer_mot_de_passe()

            prenom, _, nom = nom_complet.partition(" ")
            user = User.objects.create_user(
                username=username,
                password=mot_de_passe,
                first_name=prenom,
                last_name=nom,
            )
            profil = user.profil
            profil.telephone = telephone
            profil.save(update_fields=["telephone"])

            if plan is not None:
                Abonnement.objects.create(user=user, plan=plan)

            request.session["identifiants_generes"] = {
                "nom_complet": nom_complet,
                "username": username,
                "mot_de_passe": mot_de_passe,
                "telephone": telephone,
                "plan": plan.nom if plan is not None else None,
            }
            return redirect("comptes:creer_compte_adherent")
    else:
        form = CreationCompteAdherentForm()

    return render(request, "comptes/creer_compte.html", {
        "form": form,
        "identifiants": identifiants,
    })


class ChangerMotDePasseView(LoginRequiredMixin, auth_views.PasswordChangeView):
    template_name = "comptes/changer_mot_de_passe.html"
    success_url = reverse_lazy("comptes:changer_mot_de_passe_termine")


class ChangerMotDePasseTermineView(LoginRequiredMixin, auth_views.PasswordChangeDoneView):
    template_name = "comptes/changer_mot_de_passe_termine.html"



