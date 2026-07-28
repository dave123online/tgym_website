"""
Bot Gemini pour les messages WhatsApp entrants.

Priorité absolue : la vitesse d'escalade vers un humain quand le client
est insatisfait — plus importante que la qualité de la réponse du bot.
D'où la vérification de mots-clés d'insatisfaction AVANT tout appel à
Gemini (aucune latence réseau ajoutée sur ce chemin).

Ne répond JAMAIS avec du texte libre en dehors d'un message entrant
récent (la fenêtre de service 24h est nécessairement ouverte puisqu'on
est appelé depuis le webhook, en réaction à un message du client).

Chaque appel à Gemini reçoit l'historique récent de la conversation
(HISTORIQUE_MAX_MESSAGES messages, voir `_historique_conversation`), pas
seulement le dernier message entrant — sinon le bot ne peut pas gérer une
relance du type "parle-moi en plus" ou "ah oui ?" sans contexte.

Ne lève jamais d'exception vers l'appelant (le webhook) : toute erreur
est loguée et, par prudence, déclenche une escalade humaine plutôt que
de laisser le client sans réponse.
"""
import json
import logging

from django.conf import settings

from .models import ConversationWhatsApp, MessageWhatsApp
from .whatsapp_api import EnvoiWhatsAppIndisponible, envoyer_template, envoyer_texte_libre

logger = logging.getLogger(__name__)

# gemini-1.5-flash est arrêté par Google (retiré, renvoie 404 sur tout appel).
GEMINI_MODEL = "gemini-3.5-flash-lite"

# Nombre de messages (entrants + sortants confondus) conservés dans
# l'historique envoyé à Gemini à chaque tour. Sans ça, chaque message est
# traité de façon totalement isolée : le bot ne sait pas de quoi parlait
# l'échange précédent et régénère une réponse générique sur des relances
# comme "parle-moi en plus" ou "ah oui ?" (voir audit du 27/07/2026).
HISTORIQUE_MAX_MESSAGES = 14

MESSAGE_ESCALADE = (
    "Je transmets ta demande à un conseiller T GYM, il te répond très vite. Merci pour ta patience 🙏"
)

# Template Meta approuvé pour la notification admin à l'escalade — nécessaire
# car le texte libre (envoyer_texte_libre) exige une fenêtre de session
# ouverte de 24h côté destinataire, ce qui n'est généralement pas le cas
# pour un numéro admin qui n'a pas récemment écrit au bot. Un template
# business-initiated n'a pas cette contrainte.
#
# Corps du template à enregistrer sur Meta Business Manager (catégorie
# Utility) :
#   Escalade T-GYM WhatsApp
#   Le client {{1}} a besoin d'assistance.
#
#   Voir la conversation : {{2}}
#   Merci.
#
# Note : Meta exige des variables numérotées {{1}}, {{2}}... dans le corps
# du template (les noms comme {{nom_client}}/{{lien}} ne sont pas
# supportés en dehors de la fonctionnalité named-parameters, encore peu
# répandue) — {{1}} = nom_client, {{2}} = lien, dans cet ordre.
ADMIN_TEMPLATE_NAME = "escalade_conversation_client"
ADMIN_TEMPLATE_LANGUE = "fr"
ADMIN_TEMPLATE_NOMS_PARAMETRES = ["nom_client", "lien"]

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

    _notifier_admin(conversation, raison)


def _notifier_admin(conversation: ConversationWhatsApp, raison: str) -> None:
    """Prévient un conseiller humain sur WhatsApp qu'une conversation vient
    d'être escaladée, avec un lien direct (wa.me) vers l'échange avec le
    client — pour ne pas avoir à chercher le numéro dans l'admin Django.

    Passe par le template Meta approuvé ADMIN_TEMPLATE_NAME (business-
    initiated, pas de contrainte de fenêtre 24h). Tant que ce template
    n'est pas encore validé par Meta, l'envoi échoue avec
    EnvoiWhatsAppIndisponible : on retombe alors sur le texte libre, qui ne
    fonctionnera que si l'admin a lui-même écrit au bot dans les 24h.

    N'échoue jamais bruyamment : si ADMIN_WHATSAPP_NUMBER n'est pas
    configuré, ou si les deux tentatives d'envoi échouent, on logue et on
    continue (le client a déjà reçu son message d'escalade, l'essentiel
    est fait).
    """
    numero_admin = getattr(settings, "ADMIN_WHATSAPP_NUMBER", "")
    if not numero_admin:
        logger.info("ADMIN_WHATSAPP_NUMBER absent — notification admin non envoyée.")
        return

    lien_conversation = f"{settings.SITE_URL}/staff/conversations/{conversation.pk}/"
    nom_client = conversation.nom_contact or conversation.wa_id

    try:
        envoyer_template(
            numero_admin,
            ADMIN_TEMPLATE_NAME,
            ADMIN_TEMPLATE_LANGUE,
            [nom_client, lien_conversation],
            categorie="Utility",
            noms_parametres=ADMIN_TEMPLATE_NOMS_PARAMETRES,
        )
        return
    except EnvoiWhatsAppIndisponible:
        logger.warning(
            "Échec d'envoi du template admin (%s) pour la conversation %s — "
            "template pas encore approuvé sur Meta, ou paramètres incorrects. "
            "Repli sur texte libre.",
            ADMIN_TEMPLATE_NAME,
            conversation.wa_id,
        )

    message = (
        f"🔔 Escalade T-GYM WhatsApp\n"
        f"Le client {conversation.wa_id} a besoin d'assistance.\n\n"
        f"Voir la conversation : {lien_conversation}\n"
        f"Merci."
    )
    try:
        envoyer_texte_libre(numero_admin, message)
    except EnvoiWhatsAppIndisponible:
        logger.exception(
            "Échec d'envoi de la notification admin (template ET texte libre) "
            "pour la conversation %s.", conversation.wa_id
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


def _historique_conversation(conversation: ConversationWhatsApp, types_module) -> list:
    """Reconstruit les derniers échanges (jusqu'à HISTORIQUE_MAX_MESSAGES,
    entrants + sortants) sous forme de tours Gemini (`types.Content`), pour
    que le bot ait le fil de la conversation plutôt que de traiter chaque
    message entrant comme une question isolée.

    Le message qui vient d'arriver a déjà été enregistré en base par le
    webhook AVANT l'appel à cette fonction (voir `_enregistrer_message_entrant`
    dans `views.py`) : il fait donc partie de `conversation.messages` et doit
    être exclu ici, puisqu'il est envoyé séparément comme message courant à
    `chat.send_message()`.

    Les réponses du bot sont stockées en texte brut (le champ `reponse` déjà
    extrait du JSON, voir `envoyer_texte_libre`), pas en JSON — c'est
    volontaire : le JSON strict n'est une contrainte de format que sur la
    sortie du tour courant, pas quelque chose que Gemini a besoin de revoir
    dans son propre historique.
    """
    messages = list(
        conversation.messages.order_by("-date_envoi")[: HISTORIQUE_MAX_MESSAGES + 1]
    )
    messages.reverse()
    if messages:
        messages = messages[:-1]  # retire le message entrant courant (déjà enregistré)

    historique = []
    for msg in messages:
        if not msg.contenu:
            continue
        role = "user" if msg.sens == MessageWhatsApp.Sens.ENTRANT else "model"
        historique.append(
            types_module.Content(role=role, parts=[types_module.Part.from_text(text=msg.contenu)])
        )
    return historique


def _demander_a_gemini(conversation: ConversationWhatsApp, message: str) -> dict | None:
    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not api_key:
        logger.info("GEMINI_API_KEY absente — bot WhatsApp indisponible.")
        return None

    try:
        from google import genai
        from google.genai import errors, types

        client = genai.Client(api_key=api_key)
        chat = client.chats.create(
            model=GEMINI_MODEL,
            history=_historique_conversation(conversation, types),
            config=types.GenerateContentConfig(
                system_instruction=_instructions_systeme(conversation)
            ),
        )
        response = chat.send_message(message)
        texte = (response.text or "").strip()
        # Gemini peut entourer le JSON de ```json ... ``` malgré la consigne : on nettoie.
        texte = texte.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    except errors.APIError as exc:
        logger.error(
            "Échec de l'appel Gemini pour le bot WhatsApp (conversation %s) — code=%s status=%s message=%s",
            conversation.wa_id, exc.code, exc.status, exc.message,
        )
        return None
    except Exception:
        logger.exception(
            "Échec inattendu (non-API) de l'appel Gemini pour le bot WhatsApp (conversation %s).",
            conversation.wa_id,
        )
        return None

    try:
        return json.loads(texte)
    except json.JSONDecodeError:
        logger.error(
            "Réponse Gemini non-JSON pour le bot WhatsApp (conversation %s) : %r",
            conversation.wa_id, texte[:300],
        )
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
