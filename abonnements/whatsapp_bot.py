"""
Bot Gemini pour les messages WhatsApp entrants.

Priorité absolue : la vitesse d'escalade vers un humain quand le client
est insatisfait — plus importante que la qualité de la réponse du bot.
D'où la vérification de mots-clés d'insatisfaction AVANT tout appel à
Gemini (aucune latence réseau ajoutée sur ce chemin).

Ne répond JAMAIS avec du texte libre en dehors d'un message entrant
récent (la fenêtre de service 24h est nécessairement ouverte puisqu'on
est appelé depuis le webhook, en réaction à un message du client).

Ne lève jamais d'exception vers l'appelant (le webhook) : toute erreur
est loguée et, par prudence, déclenche une escalade humaine plutôt que
de laisser le client sans réponse.
"""
import json
import logging

from django.conf import settings

from .models import ConversationWhatsApp
from .whatsapp_api import EnvoiWhatsAppIndisponible, envoyer_texte_libre

logger = logging.getLogger(__name__)

MESSAGE_ESCALADE = (
    "Je transmets ta demande à un conseiller T GYM, il te répond très vite. Merci pour ta patience 🙏"
)

# Mots-clés déclenchant une escalade immédiate, sans passer par Gemini.
# Volontairement large plutôt que précis : le coût d'une escalade
# inutile est faible, celui de rater une vraie insatisfaction est élevé.
MOTS_INSATISFACTION = [
    "arnaque", "scam", "voleur", "plainte", "remboursement", "rembourse",
    "nul", "déçu", "decu", "insatisfait", "colère", "colere", "inadmissible",
    "inacceptable", "réclamation", "reclamation", "avocat", "signaler",
    "annuler mon abonnement", "je veux annuler", "résilier", "resilier",
]


def _client_insatisfait(texte: str) -> bool:
    texte_normalise = texte.lower()
    return any(mot in texte_normalise for mot in MOTS_INSATISFACTION)


def _escalader(conversation: ConversationWhatsApp, raison: str) -> None:
    conversation.mode_bot = ConversationWhatsApp.ModeBot.HUMAIN
    conversation.raison_escalade = raison
    conversation.save(update_fields=["mode_bot", "raison_escalade"])

    try:
        envoyer_texte_libre(conversation.wa_id, MESSAGE_ESCALADE)
    except EnvoiWhatsAppIndisponible:
        logger.exception(
            "Échec d'envoi du message d'escalade pour la conversation %s.", conversation.wa_id
        )


def _contexte_client(conversation: ConversationWhatsApp) -> str:
    """Récupère les infos du client (abonnement, dates) si son numéro
    correspond à un compte connu — pour que Gemini puisse répondre à des
    questions du type 'quand expire mon abonnement ?' avec les vraies
    données, jamais en inventant."""
    from comptes.models import Profil

    numero_local = conversation.wa_id[-8:]  # comparaison sur les 8 derniers chiffres
    profil = Profil.objects.filter(telephone__endswith=numero_local).select_related("user").first()
    if not profil:
        return "Ce numéro ne correspond à aucun compte client connu dans notre base."

    abonnement = profil.user.abonnements.filter(actif=True).select_related("plan").first()
    if not abonnement:
        return f"Client : {profil.user.get_full_name() or profil.user.username}. Aucun abonnement actif actuellement."

    return (
        f"Client : {profil.user.get_full_name() or profil.user.username}\n"
        f"Formule : {abonnement.plan.nom}\n"
        f"Date de fin : {abonnement.date_fin or 'non définie'}\n"
        f"Jours restants : {abonnement.jours_restants()}"
    )


def _contexte_site() -> str:
    from core.chatbot import _contexte_site as contexte_site_chatbot
    return contexte_site_chatbot()


def _instructions_systeme(conversation: ConversationWhatsApp) -> str:
    return (
        "Tu es l'assistant WhatsApp de T-GYM, une salle de sport au Bénin. Tu réponds "
        "en français, ton chaleureux, 1 à 3 phrases maximum (c'est WhatsApp, pas un email).\n\n"
        "Règles strictes :\n"
        "- N'utilise QUE les informations fournies ci-dessous. N'invente JAMAIS un prix, "
        "un horaire, une date d'expiration d'abonnement ou une information non fournie.\n"
        "- Aucun conseil médical, nutritionnel ou d'entraînement personnalisé.\n"
        "- Si tu ne peux pas répondre avec certitude à partir des informations fournies, "
        "ou si la demande nécessite une action humaine (paiement, réclamation, inscription, "
        "modification de compte), NE RÉPONDS PAS toi-même : indique needs_human=true.\n\n"
        "Réponds STRICTEMENT en JSON, sans texte autour, au format :\n"
        '{"reponse": "...", "needs_human": false}\n\n'
        f"Informations sur T-GYM :\n{_contexte_site()}\n\n"
        f"Informations sur ce client :\n{_contexte_client(conversation)}"
    )


def _demander_a_gemini(conversation: ConversationWhatsApp, message: str) -> dict | None:
    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not api_key:
        logger.info("GEMINI_API_KEY absente — bot WhatsApp indisponible.")
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=message,
            config=types.GenerateContentConfig(
                system_instruction=_instructions_systeme(conversation)
            ),
        )
        texte = (response.text or "").strip()
        # Gemini peut entourer le JSON de ```json ... ``` malgré la consigne : on nettoie.
        texte = texte.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(texte)
    except Exception:
        logger.exception("Échec de l'appel Gemini pour le bot WhatsApp (conversation %s).", conversation.wa_id)
        return None


def traiter_message_entrant(conversation: ConversationWhatsApp, texte: str) -> None:
    """Point d'entrée appelé par le webhook juste après l'enregistrement
    d'un message entrant. Ne fait rien si la conversation est déjà en
    mode humain (escaladée) — le staff garde la main tant qu'il ne la
    repasse pas manuellement en mode bot."""
    if conversation.mode_bot != ConversationWhatsApp.ModeBot.BOT:
        return

    # 1. Détection d'insatisfaction — priorité absolue, aucun appel réseau.
    if _client_insatisfait(texte):
        _escalader(conversation, raison=f"Mot-clé d'insatisfaction détecté dans : « {texte[:100]} »")
        return

    # 2. Tentative de réponse par Gemini, à partir des données réelles.
    resultat = _demander_a_gemini(conversation, texte)
    if resultat is None or resultat.get("needs_human"):
        raison = "Gemini indisponible" if resultat is None else "Gemini a indiqué needs_human=true"
        _escalader(conversation, raison=raison)
        return

    reponse = (resultat.get("reponse") or "").strip()
    if not reponse:
        _escalader(conversation, raison="Réponse Gemini vide")
        return

    try:
        envoyer_texte_libre(conversation.wa_id, reponse)
    except EnvoiWhatsAppIndisponible:
        logger.exception("Échec d'envoi de la réponse bot pour la conversation %s.", conversation.wa_id)
        _escalader(conversation, raison="Échec technique d'envoi de la réponse bot")
