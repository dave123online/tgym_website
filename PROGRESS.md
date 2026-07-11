# T-GYM — Suivi d'avancement

Dernière mise à jour : 08/07/2026

Légende : ✅ fait & testé · 🔄 en cours · ⏳ pas commencé · 🔒 bloqué (dépendance externe)

---

## Phase 1 — Vitrine + Tarifs + Funnel WhatsApp
✅ **Terminée et testée**
- SiteConfig (singleton), Annonce (bandeau), Plan (grille tarifaire)
- Liens WhatsApp pré-remplis (wa.me, clic visiteur uniquement)
- Lien Google Maps direct (sans API)
- Pages Accueil / La Méthode / Tarifs / Où nous trouver
- Admin Django en français, seed_tgym

## Phase 1.5 — Programmes
✅ **Terminée et testée**
- Modèle Programme extensible, page liste + détail
- Programme "phare" auto-affiché (context processor global)
- "45 jours pour maigrir" chargé via seed_tgym

## Phase 2 — Actualités
✅ **Terminée et testée**
- Modèle Actualite (catégorie, image optionnelle, is_featured, est_publiee)
- Page liste `/actualites/` + détail `/actualites/<slug>/`
- Bandeau "Top Body News" auto-alimenté par l'actu is_featured
  (fallback quand aucune Annonce n'est active)
- Lien nav "Actualités"

## Phase 3 — Comptes, abonnements, relance auto, chatbot

### Étape 1 — Comptes & rôles
✅ **Terminée et testée** (08/07/2026)
- App `comptes` : modèle `Profil` (OneToOne sur `auth.User`) avec rôle
  `staff` / `coach` / `adherent`
- Pas de swap `AUTH_USER_MODEL` (trop risqué sur la base déjà migrée) —
  le `User` Django standard reste la source d'auth, `Profil` ajoute la
  couche "rôle métier" par-dessus
- Signal : tout nouveau `User` reçoit un `Profil` automatiquement
  (staff/superuser → rôle staff, sinon adhérent par défaut)
- Migration de backfill : les comptes déjà existants (ex: `shade`) ont
  reçu un `Profil` rétroactivement — vérifié en shell
- Admin : rôle éditable inline sur la fiche User + liste Profil dédiée
- Vues : `/connexion/`, `/deconnexion/`, `/mon-espace/` (point d'entrée
  unique qui affichera le bon contenu selon le rôle)
- `comptes/decorators.py` : `role_required(*roles)` prêt à l'emploi pour
  les futurs dashboards coach/adhérent
- Testé : toutes les pages existantes toujours en HTTP 200, `/connexion/`
  200, `/mon-espace/` redirige bien vers connexion si non authentifié,
  formulaire de login fonctionnel (CSRF + erreurs affichées)

### Étape 2 — Modèle Abonnement (adhérent ↔ plan ↔ expiration)
✅ **Terminée et testée** (08/07/2026)
- `Abonnement` : lien `User` ↔ `Plan` ↔ `date_debut`/`date_fin`
- `duree_jours` sur `Plan` → calcul automatique de `date_fin` à la sauvegarde
  (écrase toute saisie manuelle si la formule a une durée définie)
- `est_en_cours()` pour retrouver l'abonnement actif d'un adhérent
- Admin avec inlines (Profil + Abonnements sur la fiche User)
- Historique des contrôles de résultat : pas encore fait, reporté (lié au
  rôle coach, hors scope immédiat)
- Affichage dans `/mon-espace/` : fait le 08/07/2026 (abonnement en cours
  avec badge selon délai avant expiration + historique en tableau)

### Étape 3 — Détection des expirations + génération de message IA
✅ **Terminée et testée** (08/07/2026)
- Modèle `RelanceMessage` (`abonnements/models.py`) : message généré,
  `date_expiration_ciblee` (snapshot pour éviter les doublons), statut
  (`a_envoyer` / `envoye` / `ignore`), `genere_par_ia`, traçabilité de
  l'envoi manuel (`envoye_le`, `envoye_par`)
- `abonnements/ia_relance.py` : génération via Gemini, isolée dans une
  seule fonction (`generer_message_relance`) — même principe que
  `core/whatsapp.py`, point unique de changement si le provider IA change
- Ne lève jamais d'exception : si `GEMINI_API_KEY` est absente ou l'appel
  échoue, bascule silencieusement sur un message de secours (gabarit fixe)
  pour ne jamais bloquer la tâche planifiée
- Commande `python manage.py generer_relances [--jours N]` (défaut 3
  jours) : détecte les abonnements `actif=True` dont `date_fin` tombe
  dans la fenêtre, génère un message par abonnement concerné
- Idempotente : ne régénère pas de message pour la même échéance si un
  `RelanceMessage` existe déjà pour ce couple (abonnement, date_fin)
- Admin `RelanceMessage` : actions "Marquer comme envoyé" / "Ignorer"
  pour le suivi manuel — le staff copie le texte vers WhatsApp lui-même
  en attendant l'Étape 4
- `GEMINI_API_KEY` ajoutée aux settings (`os.environ`, vide par défaut →
  fallback automatique) + `google-generativeai` dans `requirements.txt`
- Testé en conditions réelles (copie jetable) : abonnement expirant dans
  2 jours détecté avec `--jours 3` par défaut, message de secours généré
  correctement (pas de clé Gemini en environnement de test), deuxième
  exécution de la commande → 0 doublon créé
- ⏳ Reste à décider : mécanisme de planification (Render Cron Job,
  Celery beat, ou autre) — pas encore choisi, à trancher en phase
  Déploiement ou avant si besoin

### Étape 4 — Couche d'envoi WhatsApp Business Cloud API (Meta)
✅ **Terminée et testée** (08/07/2026)
- Variables d'environnement ajoutées (vides par défaut) : `WHATSAPP_ACCESS_TOKEN`,
  `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_BUSINESS_ACCOUNT_ID`,
  `WHATSAPP_TEMPLATE_RELANCE` (défaut `relance_abonnement`), `WHATSAPP_TEMPLATE_LANGUE`
  (défaut `fr`)
- Fonction d'envoi isolée : `abonnements/whatsapp_api.py::envoyer_template_relance`
  — tout le reste du code passe par elle, jamais l'API Meta directement
  (placée dans `abonnements/` plutôt que `comptes/` suggéré en placeholder,
  plus cohérent avec `ia_relance.py` et `RelanceMessage`)
- ⚠️ **Décision d'architecture** : l'API Cloud de Meta exige un template
  pré-approuvé pour tout message business-initiated hors fenêtre de 24h —
  impossible d'y envoyer le texte libre généré par Gemini. Le texte IA
  reste donc réservé à la copie manuelle par le staff ; l'envoi automatique
  utilise un template Meta séparé avec 3 variables structurées (prénom,
  formule, date d'expiration). **Le template `relance_abonnement` reste à
  créer et faire approuver côté Meta Business Manager** — sans lui, l'envoi
  automatique échouera même une fois les tokens fournis.
- Tant que les credentials sont absents : `envoyer_template_relance` lève
  `EnvoiWhatsAppIndisponible`, logguée et absorbée par l'appelant — le
  message reste au statut `a_envoyer` (fallback manuel toujours actif)
- Nouvelle commande `python manage.py envoyer_relances_whatsapp` : tente
  l'envoi pour tous les `RelanceMessage` en attente ; en cas de succès,
  statut → `envoye`, `envoye_automatiquement=True`, `envoye_le` renseigné
- Nouveau champ `RelanceMessage.envoye_automatiquement` pour distinguer
  envoi auto (Étape 4) vs envoi manuel par le staff (Étape 3), visible et
  filtrable dans l'admin
- `numero_international()` exposé publiquement dans `core/whatsapp.py`
  (au lieu de rester privé) — point unique de normalisation des numéros,
  réutilisé par les liens wa.me ET l'appel API
- `requests` ajouté à `requirements.txt`
- Testé avec `requests.post` mocké (3 scénarios) : pas de credentials →
  laissé en attente sans erreur ; succès HTTP 200 → statut/traçabilité mis
  à jour, payload vérifié (numéro international, template, 3 variables
  dans l'ordre) ; échec HTTP 400 (ex: template inconnu) → laissé en
  attente, log clair, aucun crash
- 🔒 Rappel : nécessite compte Meta Business + numéro dédié validé +
  template pré-approuvé (hors fenêtre de 24h) + opt-in client

### Étape 5 — Chatbot Gemini (site)
✅ **Terminée et testée** (08/07/2026)
- `core/chatbot.py` (nouveau) : appel Gemini isolé (même principe que
  `ia_relance.py`). Le contexte injecté dans le prompt système est
  reconstruit à chaque appel depuis la base (`SiteConfig`, `Plan` actifs,
  `Programme` phare) — le chatbot ne peut donc pas répondre avec un tarif
  ou un horaire obsolète, et ne doit rien inventer
- Consignes système : pas de conseil médical/nutritionnel personnalisé
  (redirige vers un coach), pas d'invention de prix/horaires, redirection
  vers WhatsApp pour toute action nécessitant un humain, réponses courtes
  (2-4 phrases, format widget de chat)
- `core/views.py::chatbot_message` (nouveau, POST uniquement) : **aucun
  stockage en base** — tout vit en session Django (limite les données
  personnelles conservées sans nécessité). L'historique envoyé à Gemini
  vient toujours de la session serveur, jamais du client → impossible
  d'injecter de faux tours de conversation dans le prompt
- Historique de session tronqué à 6 échanges (`MAX_TOURS_HISTORIQUE`),
  pour garder le coût par appel bas
- Limite anti-coût : 20 messages/jour/session (`LIMITE_MESSAGES_PAR_JOUR`),
  au-delà réponse de repli invitant à passer par WhatsApp (pas une vraie
  protection anti-abus, juste un garde-fou de coût)
- Widget flottant dans `templates/base.html` (bouton 🤖 en bas à gauche,
  pour ne pas chevaucher le bouton WhatsApp 💬 en bas à droite), JS
  vanilla (pas de dépendance front supplémentaire), style ajouté dans
  `theme.css`
- Réutilise `GEMINI_API_KEY` déjà configurée à l'Étape 3 — même comportement
  de repli si absente (message invitant à contacter WhatsApp, jamais de
  crash du widget)
- Testé : GET refusé (405), message vide rejeté (400), fallback sans clé
  API vérifié, succès Gemini mocké avec vérification que le contexte
  contient bien les vraies données seedées (`Premium`, `45 jours pour
  maigrir`), limite de 20 messages/jour déclenchée au 21e message

## Déploiement
⏳ **Pas commencé**
- Render + WhiteNoise (statique) + Postgres (Neon ou autre), variables
  d'environnement `SECRET_KEY` / `DEBUG` / `ALLOWED_HOSTS` — même logique
  qu'Akem FS

---

## Petits points en attente (non bloquants)
- Identifiants de test locaux (`admin` existant côté staff) à changer
  avant toute mise en ligne — **à faire par David lui-même**, pas encore fait
- 🔲 Lien structuré `Programme ↔ Plan` (FK ou M2M) : optionnel, à faire
  si besoin un jour de remplacer le texte libre `prix_note` par une vraie
  relation — pas urgent, `coaching` et `abonnements` restent deux apps
  distinctes (décidé le 08/07/2026, voir ci-dessous)

## Accueil enrichi — 09/07/2026 (v2 : direction vidéo-first)
✅ **Fait et testé**

Deuxième passe suite au constat de David : plus de vidéos que de photos
disponibles côté salle. Direction créative changée en conséquence — voir
`frontend-design` : signature = **motif "câble"** (`.cable-divider`,
CSS pur, pas d'image), clin d'œil au fait que T-GYM est littéralement
sous des lignes haute tension à Abomey-Calavi. Utilisé uniquement comme
séparateur entre sections, jamais en décoration isolée. Typo : `Anton`
(titres, registre affiche sportive condensée) + `Inter` (corps de texte)
via Google Fonts, chargées côté navigateur du visiteur (pas d'impact sur
l'environnement de dev).

Trois traitements vidéo volontairement différents (pas de répétition du
même bloc "vidéo en fond" partout) :
- **Hero** — vidéo/photo plein cadre + overlay dégradé (déjà en place,
  conservé)
- **Mur "Dans nos murs"** (nouveau) — mosaïque asymétrique
  (`.video-wall`, grille 6 colonnes, tailles de tuiles variées) mélangeant
  vidéos généralistes ET photos de la galerie dans la même grille, vidéos
  en premier (David a plus de vidéos que de photos). Lecture en
  boucle/muette, aucun son requis. Masquée si aucun média.
- **Programme phare** (nouveau) — vidéo unique en **cadre portrait**
  (`.programme-phare__ecran`, ratio 9:16, coins arrondis façon écran de
  téléphone) à côté de la fiche programme, sur fond clair — rupture de
  rythme volontaire par rapport aux deux sections précédentes. Bascule
  automatiquement sur une photo de la galerie si aucune vidéo n'est
  encore liée au programme, section jamais cassée en attendant du contenu.

Modèle `VideoSalle` (app `core`) : fichier vidéo, aperçu (poster)
optionnel, légende, lien optionnel vers un `Programme` (si renseigné →
vidéo "produit phare" au lieu de généraliste). Même philosophie que
`PhotoSalle` : rien en dur, tout piloté depuis l'admin, sections
masquées tant qu'aucun média n'est en ligne.

Testé : suite complète toujours à 104/104 verts après migration
(`core.0003_videosalle`) ; structure de page vérifiée avec vidéos/photos
de démo générées localement (4 tuiles dans le mur, cadre portrait avec
sa propre vidéo, 6 séparateurs câble générés, zéro erreur serveur) —
démo supprimée avant livraison.

**Action à faire par David** : trier ses vidéos en deux tas au moment de
l'upload — celles à associer au champ `programme` d'un `Programme`
(produit phare) vs celles à laisser sans `programme` (mur généraliste).
Formats vertical et horizontal fonctionnent tous les deux dans le mur ;
le cadre portrait du programme phare est pensé pour du vertical mais
recadre en `object-fit: cover` si la vidéo est horizontale.

## Accueil enrichi — 09/07/2026
✅ **Fait et testé**
- Page passée de 3 sections à 7 : méthode (existant) → **galerie
  "L'ambiance T-GYM"** (nouveau) → programme phare (existant) →
  **localisation/horaires en mini-cartes** (nouveau) → **aperçu des 3
  dernières actualités** (nouveau, réutilise `Actualite` déjà existant,
  jusque-là jamais montré sur l'accueil) → plan populaire (existant) →
  **CTA final WhatsApp** (nouveau)
- `SiteConfig` : ajout `hero_image` / `hero_video` (les deux optionnels,
  vidéo prioritaire sur image si les deux sont renseignées) — le hero
  passe d'un fond noir plat à une vraie photo/vidéo de la salle en fond,
  avec overlay dégradé pour garder le texte lisible
- Nouveau modèle `PhotoSalle` (app `core`) : galerie admin-pilotée
  (image, légende optionnelle, actif, ordre d'affichage) — section
  masquée automatiquement tant qu'aucune photo n'est en ligne, pas de
  placeholder cassé avant que le staff n'ajoute du contenu
- Aucune image de stock utilisée : tout est pensé pour être rempli avec
  de VRAIES photos/vidéos de T-GYM par le staff depuis l'admin (upload
  simple, pas de retouche requise côté code)
- Renommé l'eyebrow de la section actus ("Top Body News" → "Vie de la
  salle") pour ne pas entrer en collision avec le nom réservé du bandeau
  du même nom (bug détecté par la suite de tests existante, corrigé
  avant livraison)
- Testé : suite complète toujours à 104/104 verts, structure de page
  vérifiée (7 sections dans l'ordre), galerie testée avec des images de
  démo générées localement (supprimées avant livraison — aucune vraie
  photo T-GYM n'existe encore côté staff)
- **Action à faire par David** : uploader de vraies photos/vidéos de la
  salle dans l'admin (`SiteConfig` pour le hero, `Photos de la salle`
  pour la galerie) — le site est prêt à les recevoir mais reste sans
  section galerie tant que c'est vide

## Décisions prises
- **08/07/2026 — `coaching` vs `abonnements`** : apps gardées séparées.
  `coaching.Programme` = contenu éditorial public (pas de donnée sensible),
  `abonnements` = facturation + données liées à un `User` (et bientôt
  relances/API WhatsApp) — périmètres différents, pas de raison de fusionner.
  Rien n'empêche d'ajouter une vraie FK `Programme → Plan` plus tard si
  besoin d'un lien structuré (au lieu du texte libre `prix_note` actuel).
- **08/07/2026 — Coordonnées GPS T-GYM** : pas encore disponibles, on garde
  le fallback adresse texte pour le lien Google Maps (déjà en place, aucun
  changement de code nécessaire). À renseigner dans l'admin (`SiteConfig`)
  quand elles seront disponibles.
- **08/07/2026 — `/mon-espace/` (adhérent)** : branché sur les vraies
  données (voir Étape 2 ci-dessus) — plus un placeholder.

## Sécurité — audit du 09/07/2026
🔄 **To-do, pas encore corrigé** (voir tgym_rapport_securite.txt pour le
détail complet des mécanismes et preuves empiriques)

Bloquant avant tout déploiement public :
- 🔲 Changer le mot de passe du superuser `admin` (déjà su, jamais fait)
- 🔲 Définir `SECRET_KEY` (neuve, jamais celle commitée), `DEBUG=False` et
  `ALLOWED_HOSTS` explicitement dans l'environnement de prod (Render) —
  vérifié que sans ça, DEBUG=True s'active par défaut et expose les pages
  techniques Django (stack traces, settings, requêtes SQL)

Élevé/moyen, à traiter rapidement après le déploiement initial :
- 🔲 `comptes/backends.py::IdentifiantOuTelephoneBackend` — canal de timing
  mesuré (~430ms d'écart, ~0.88s compte existant vs ~0.45s inexistant) qui
  permet d'énumérer les identifiants/téléphones à distance. Cause : le
  backend perso s'ajoute à `ModelBackend` au lieu de le remplacer, donc les
  deux hashent le mot de passe pour un compte existant (2x le coût) contre
  un seul hash factice pour un compte inexistant. Corriger en appelant un
  hash factice systématique sur le chemin "introuvable", et évaluer si
  `ModelBackend` doit rester dans `AUTHENTICATION_BACKENDS` vu que le
  backend perso fait déjà la recherche par username.
- 🔲 `core/views.py::chatbot_message` — limite de 20 msg/jour stockée en
  session, donc contournable en ne réutilisant pas le cookie (vérifié :
  25 messages envoyés avec sessions fraîches, 0 blocage). Ajouter un
  throttling par IP indépendant de la session (django-ratelimit ou
  équivalent) avant mise en ligne publique du chatbot.
- 🔲 Durcissement cookies/HTTPS pour la prod : `SESSION_COOKIE_SECURE`,
  `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`,
  `CSRF_TRUSTED_ORIGINS` — aucun n'est actuellement défini, même
  conditionnellement. À ajouter dans un bloc `if not DEBUG:` à l'étape
  Déploiement.

Faible, backlog :
- ✅ **Anti-brute-force sur `/connexion/` et `/admin/login/`** — fait le
  09/07/2026, voir section "Audit sécurité" plus bas.
- 🔲 Écart entre les tests décrits dans ce fichier (scénarios précis,
  "mocké", "405 sur GET"...) et la réalité : tous les `tests.py` étaient
  vides avant le 09/07/2026 (`Found 0 test(s)`). Corrigé — voir section
  "Tests de régression" ci-dessous.
- 🔲 (mineur, backlog) `google-generativeai` est officiellement déprécié
  côté Google (`FutureWarning` vu en lançant les tests) au profit de
  `google-genai`. Migration à prévoir un jour dans `ia_relance.py` et
  `chatbot.py` — pas urgent, le package actuel fonctionne toujours.

Vérifié SANS problème trouvé lors de cet audit (pour référence, ne pas
re-vérifier inutilement) : pas de XSS stocké (aucun `|safe` en template,
chatbot utilise `textContent`), pas d'injection SQL (tout passe par
l'ORM), pas d'IDOR sur `/mon-espace/` (toujours filtré sur `request.user`),
`creer_compte_adherent` correctement protégée par rôle, pas d'upload
public d'image, CSRF correct sur le chatbot, credentials WhatsApp/Gemini
jamais codées en dur.

## Tests de régression
✅ **Créés le 09/07/2026** — 96 tests au total (`python manage.py test`),
un `tests.py` par app couvrant le comportement actuel (modèles, vues
publiques, formulaires, décorateur de rôle, backend d'auth, générateurs
de liens WhatsApp, fallback IA sans clé API, commandes de gestion,
mocks Gemini/API WhatsApp Business). Objectif : pouvoir lancer
`python manage.py test` en un coup avant chaque changement et détecter
toute régression sur ce qui marche déjà. Ne couvrent PAS encore les
corrections de sécurité ci-dessus (pas encore faites) — à compléter au
fur et à mesure qu'elles seront traitées.


- 🐛 **08/07/2026** — `AUTHENTICATION_BACKENDS` (backend `comptes.backends.
  IdentifiantOuTelephoneBackend`, connexion par téléphone) avait été ajouté
  dans un `./settings.py` orphelin à la racine, jamais lu par Django
  (`manage.py` pointe vers `tgym_site.settings`). Le vrai fichier
  `tgym_site/settings.py` ne l'avait donc jamais chargé — la connexion par
  téléphone tombait silencieusement sur le `ModelBackend` par défaut.
  Corrigé : bloc déplacé dans `tgym_site/settings.py`, fichier orphelin
  supprimé.
- 🐛 **08/07/2026** — `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` étaient encore
  codés en dur dans `settings.py` malgré la mention "même logique qu'Akem
  FS" dans la section Déploiement de ce fichier — en réalité rien n'était
  branché sur l'environnement. Corrigé : les trois lisent maintenant
  `os.environ` (avec repli dev sûr pour `SECRET_KEY`/`DEBUG` uniquement —
  aucun repli pour `ALLOWED_HOSTS`, qui doit être explicitement fourni en
  prod). `python-dotenv` ajouté + `load_dotenv()` appelé en tête de
  `settings.py` pour que `.env` soit réellement chargé en local (sans ça,
  un `.env.example` rempli n'aurait servi à rien). Voir `.env.example`
  à la racine pour la liste complète des variables reconnues.

---

## Audit sécurité — 09/07/2026

Audit externe (`tgym_rapport_securite.txt`) reçu et vérifié empiriquement
avant correction (codebase reconstruit localement, migrations générées,
suite de tests + tests dynamiques dédiés). Tous les findings ont été
confirmés dans le code réel **sauf le finding #7**, qui était faux (voir
plus bas) — corrigé dans l'ordre de priorité du rapport.

### Corrigé

1. ✅ **CRITIQUE — SECRET_KEY / DEBUG / ALLOWED_HOSTS**
   `tgym_site/settings.py` lit maintenant un interrupteur **explicite**
   `IS_PRODUCTION` (`os.environ`, `False` par défaut) plutôt que de
   déduire "on est en prod" depuis `ALLOWED_HOSTS` — plus fiable, aucune
   ambiguïté possible. En local, `IS_PRODUCTION` n'est jamais posé :
   `DEBUG` peut rester `True`, `SECRET_KEY`/`ALLOWED_HOSTS` peuvent rester
   vides, rien ne bloque. Dès que `IS_PRODUCTION=True` (à poser sur
   Render) : `SECRET_KEY` manquante ou `DEBUG` pas explicitement à
   `False` → `ImproperlyConfigured` immédiat au démarrage, plutôt que de
   tourner silencieusement avec la clé par défaut documentée dans ce
   dépôt. Le durcissement cookies/HTTPS (`SESSION_COOKIE_SECURE` etc.)
   est lui aussi piloté par `IS_PRODUCTION`, pas par `DEBUG` seul.
   Testé : 5 scénarios (local pur / `IS_PRODUCTION=True` sans clé /
   `IS_PRODUCTION=True` sans `DEBUG=False` / config prod complète /
   `ALLOWED_HOSTS` seul sans `IS_PRODUCTION` — ce dernier ne bloque plus,
   contrairement à l'ancienne heuristique). Suite complète : 100 tests
   toujours verts après ce changement.
2. ✅ **CRITIQUE — mot de passe admin par défaut → devenu non-bloquant pour
   le déploiement**
   Précision du 09/07/2026 : Render tournera sur **Postgres**, une base
   neuve — la migration initiale n'y créera aucun superuser, `admin` avec
   son mot de passe par défaut n'existe donc que dans le `db.sqlite3`
   local. Le compte admin de prod sera créé via `python manage.py
   createsuperuser` directement sur l'instance Render, avec un mot de
   passe fort choisi à ce moment-là — pas de bascule d'un mot de passe
   existant à changer. `admin/tgym2026` reste une gêne purement locale
   (pas d'action requise avant déploiement) ; ⏳ **reste recommandé** de le
   changer en local aussi (`python manage.py changepassword admin`) pour
   ne pas développer avec un mot de passe connu, mais ce n'est plus un
   point bloquant.
3. ✅ **ÉLEVÉ — canal de timing sur l'authentification**
   `comptes/backends.py` : `ModelBackend` retiré de
   `AUTHENTICATION_BACKENDS` (il faisait doublon avec
   `IdentifiantOuTelephoneBackend`, qui couvre déjà la recherche par
   username). Un seul hash par tentative désormais, réel si l'utilisateur
   existe, factice (`User().set_password(...)`) sinon — le temps de
   réponse ne varie plus selon l'existence du compte. Testé : suite
   fonctionnelle de connexion (username/téléphone/mauvais mot de passe)
   toujours verte + nouveau test qui vérifie le déclenchement du hash
   factice sur un identifiant inconnu.
4. ✅ **MOYEN — garde-fou chatbot contournable**
   `core/views.py` : throttle par IP ajouté (`django.core.cache`,
   20 messages/IP/jour), indépendant du cookie de session — gère
   `X-Forwarded-For` pour un déploiement derrière Render. Le compteur en
   session existant est conservé pour l'UX ("tu as atteint ta limite")
   mais n'est plus la seule protection. ⚠️ Cache par défaut = mémoire du
   process (`LocMemCache`) : suffisant pour un seul worker, mais **à
   passer sur un cache partagé (Redis/Memcached) si le déploiement tourne
   plusieurs workers/dynos**, sinon la limite redevient contournable en
   frappant des workers différents — à trancher à l'étape Déploiement.
   Testé : script simulant un client sans cookies (nouvelle session à
   chaque requête) → bloqué au 21e message ; deux IP différentes via
   `X-Forwarded-For` → compteurs bien indépendants.
5. ✅ **MOYEN — durcissement cookies/HTTPS**
   Bloc `if not DEBUG:` ajouté dans `settings.py` :
   `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`,
   `SECURE_HSTS_SECONDS` (+ subdomains/preload), `SECURE_PROXY_SSL_HEADER`
   (nécessaire derrière le proxy TLS de Render), `CSRF_TRUSTED_ORIGINS`
   généré depuis `ALLOWED_HOSTS`. Jamais actif en local (`DEBUG=True`).
   Testé : valeurs correctement activées en simulant une config prod.

### Backlog (non bloquant, noté par le rapport comme "peut attendre")

- ✅ Anti-brute-force sur `/connexion/` et `/admin/login/` — fait le
  09/07/2026 (voir ci-dessous, plus dans le backlog).

### 6. Anti-brute-force — fait le 09/07/2026

`comptes/middleware.py::AntiBruteForceMiddleware`, sans dépendance externe
(pas de `django-axes`) — même approche cache Django que le throttle IP du
chatbot. Verrouille une IP après **10 tentatives échouées en 15 minutes**
sur `/connexion/` OU `/admin/login/` (compteur partagé entre les deux —
frapper l'un ou l'autre compte pareil), réponse `429` tant que verrouillé.
Un login réussi réinitialise le compteur (pas de blocage après une simple
faute de frappe suivie du bon mot de passe). Volontairement par IP seule
(pas IP+identifiant) : cohérent avec le reste du projet, un attaquant ne
peut pas contourner en changeant juste de nom d'utilisateur.
⚠️ Même limite que le throttle chatbot : cache par défaut = mémoire du
process (`LocMemCache`), à passer sur un cache partagé si plusieurs
workers en prod (même chantier que le point 4 ci-dessus, à trancher à
l'étape Déploiement).
Testé : 4 nouveaux tests (verrouillage après le seuil, verrouillage
partagé connexion/admin, réinitialisation après succès, verrouillage
indépendant du nom d'utilisateur tenté) + suite complète : **104 tests,
tous verts**.

### ⚠️ Correction du rapport lui-même — finding #7 inexact

Le rapport affirme que les 4 `tests.py` du projet sont des stubs vides
(`# Create your tests here.`) et que `python manage.py test` renvoie
"Found 0 test(s)". **Faux** dans le codebase réel : les 4 fichiers
totalisent 757 lignes et 96 tests déjà écrits (dont les scénarios
sécurité que le rapport dit absents : GEMINI mocké, limite de 20
messages/jour, refus 405 sur GET, tests fonctionnels du backend
d'authentification). `python manage.py test` → **100 tests, tous verts**
après les 6 nouveaux tests ajoutés pour les correctifs de cette session
(2 sur le throttle IP, 2 sur le backend d'auth). Le rapport semble avoir
été généré sur une version différente/antérieure du code que celle
fournie dans `codebase.txt` — signalé pour que David en tienne compte
pour la suite (les autres findings, eux, ont tous été confirmés
empiriquement sur le code réel).



