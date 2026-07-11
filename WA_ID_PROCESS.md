# Guide complet — Obtenir les identifiants WhatsApp Business API (Meta)

Ce guide te donne les **3 identifiants** dont T-GYM a besoin + le **template approuvé** indispensable pour envoyer des relances automatiques.

---

## 🎯 Ce qu'on va obtenir

À la fin de ce guide, tu auras :

| Identifiant | Utilisé dans T-GYM | Où le trouver |
|---|---|---|
| `WHATSAPP_ACCESS_TOKEN` | `abonnements/whatsapp_api.py` | Meta Developer Portal |
| `WHATSAPP_PHONE_NUMBER_ID` | idem | Meta Developer Portal |
| `WHATSAPP_BUSINESS_ACCOUNT_ID` | idem | Meta Developer Portal |
| Template `relance_abonnement` approuvé | `WHATSAPP_TEMPLATE_RELANCE` | Meta Business Manager |

---

## ⚠️ Avertissements importants AVANT de commencer

1. **Le numéro WhatsApp utilisé sur l'API ne peut plus être utilisé dans l'app WhatsApp classique.** Tu dois choisir : soit tu gardes ton numéro actuel pour l'app manuelle, soit tu le migres vers l'API (irréversible). **Solution recommandée** : acheter un **nouveau numéro** dédié à l'API (carte SIM prépayée MTN/Moov à 500 FCFA).

2. **Le token temporaire expire en 24h.** On va directement créer un **token permanent** via un System User — sinon tu devras le régénérer tous les jours.

3. **Les templates doivent être approuvés par Meta** (délai : 5 min à 24h, généralement < 15 min). Sans template approuvé, aucun envoi automatique ne marche.

4. **En mode développement**, tu ne peux envoyer des messages qu'à **5 numéros de test maximum** (les tiens + 4 autres). Pour envoyer à tous les adhérents, il faut passer en mode Live (vérification business requise).

---

## 📋 Étape 1 — Prérequis

Avant de toucher à Meta, assure-toi d'avoir :

- [ ] Un **compte Facebook personnel** (obligatoire pour créer un Business Manager)
- [ ] Un **numéro de téléphone dédié** à l'API (pas celui que tu utilises déjà sur WhatsApp perso/business)
- [ ] Ce numéro doit pouvoir **recevoir un SMS ou un appel** (pour la vérification)
- [ ] (Optionnel mais recommandé) Un **registre de commerce** ou document officiel de T-GYM — requis pour passer en mode Live

---

## 🏢 Étape 2 — Créer le compte Meta Business

> Si tu as déjà un compte Meta Business pour T-GYM (ex: pour gérer la page Facebook), **saute cette étape** et utilise le compte existant.

1. Va sur **[business.facebook.com/overview](https://business.facebook.com/overview)**
2. Clique sur **"Créer un compte"**
3. Remplis :
   - **Nom du compte** : `T-GYM`
   - **Ton nom** : ton nom complet
   - **Email professionnel** : ton email (pas un Gmail perso si possible — proscréable mais moins bien vu)
4. Clique sur **"Soumettre"** → confirme par email
5. Tu arrives sur le **Business Manager** (tableau de bord)

---

## 🛠️ Étape 3 — Créer l'app Meta Developer

1. Va sur **[developers.facebook.com](https://developers.facebook.com)**
2. Connecte-toi avec le **même compte Facebook** que le Business Manager
3. En haut à droite, clique sur **"My Apps"** → **"Create App"**
4. Choisis le type d'app : **"Business"** (pas "Consumer", pas "Game")
5. Remplis :
   - **App name** : `T-GYM WhatsApp`
   - **App contact email** : ton email
   - **Business Account** : sélectionne `T-GYM` (le Business Manager créé à l'étape 2)
6. Clique sur **"Create App"**
7. Tu arrives sur le dashboard de l'app

---

## 💬 Étape 4 — Configurer WhatsApp dans l'app

1. Sur le dashboard de l'app, dans le menu de gauche, cherche **"Add products to your app"** (ou "Ajouter des produits")
2. Trouve **"WhatsApp"** → clique sur **"Set up"** (Configurer)
3. Tu arrives sur la page WhatsApp de l'app

### 4.1 — Ajouter un numéro de téléphone

1. Dans la section **"To start using this API, add a phone number"**, clique sur **"Add phone number"**
2. Une modale s'ouvre :
   - **Phone number** : choisis **"I have a number"** (j'ai un numéro)
   - Entre le numéro dédié (avec indicatif pays, ex: `+229 9X XX XX XX`)
   - **Display name** : `T-GYM` (ce que les clients verront)
   - **Timezone** : `Africa/Porto-Novo`
   - **Business** : sélectionne `T-GYM`
3. Clique sur **"Next"**
4. Meta te demande de **vérifier le numéro** :
   - Choisis **"SMS"** ou **"Voice call"**
   - Entre le code reçu
5. ✅ Le numéro est ajouté

### 4.2 — Récupérer les 3 identifiants

Sur la même page WhatsApp, tu vois maintenant une section **"API Setup"** avec :

| Champ | Où le trouver | À copier dans T-GYM |
|---|---|---|
| **Temporary access token** | En haut de la page | ⚠️ **NE PAS UTILISER** — on va créer un token permanent |
| **Phone number ID** | Section "API Setup" → champ "Phone number ID" | `WHATSAPP_PHONE_NUMBER_ID` |
| **WhatsApp Business Account ID** | Section "API Setup" → champ "WhatsApp Business Account ID" | `WHATSAPP_BUSINESS_ACCOUNT_ID` |

**Copie ces 2 IDs maintenant** (le token, on y revient).

---

## 🔐 Étape 5 — Créer un token permanent (System User)

> Le token temporaire expire en 24h. Il faut un token permanent.

### 5.1 — Créer un System User

1. Va sur **[business.facebook.com/settings](https://business.facebook.com/settings)**
2. Menu de gauche : **"Users"** → **"System Users"**
3. Clique sur **"Add"** (Ajouter)
4. Remplis :
   - **Name** : `tgym-whatsapp-api`
   - **Role** : **"Employee"** (pas Admin — Employee suffit et c'est plus sûr)
5. Clique sur **"Create System User"**

### 5.2 — Assigner l'app au System User

1. Sur la page du System User, section **"Assigned assets"** → onglet **"Apps"**
2. Clique sur **"Add Apps"**
3. Sélectionne `T-GYM WhatsApp` (l'app créée à l'étape 3)
4. Coche la case **"Manage app"** (gérer l'app)
5. Clique sur **"Save changes"**

### 5.3 — Générer le token permanent

1. Toujours sur la page du System User, section **"Generated token"**
2. Clique sur **"Generate new password"** (oui, Meta appelle ça "password" mais c'est bien un token)
3. Une modale s'ouvre :
   - **App** : sélectionne `T-GYM WhatsApp`
   - **Permissions** : clique sur **"Select permissions"** et coche :
     - `whatsapp_business_messaging`
     - `whatsapp_business_management`
   - Clique sur **"Generate token"**
4. **Copie immédiatement le token** — il ne sera plus affichable après fermeture de la modale
5. C'est ton `WHATSAPP_ACCESS_TOKEN`

> 💡 Astuce : colle-le dans un fichier `.env` local tout de suite, ne le laisse pas dans le presse-papier.

---

## 📝 Étape 6 — Créer le template `relance_abonnement`

> Sans template approuvé, l'envoi auto ne marchera pas. C'est l'étape la plus critique.

### 6.1 — Accéder au gestionnaire de templates

1. Va sur **[business.facebook.com](https://business.facebook.com)**
2. Menu de gauche : **"Account tools"** → **"Message templates"** (ou "Modèles de message")
3. Clique sur **"Create template"**

### 6.2 — Créer le template de relance

1. **Template name** : `relance_abonnement` (doit correspondre exactement à `WHATSAPP_TEMPLATE_RELANCE` dans T-GYM)
2. **Category** : **"Marketing"** (ou "Utility" — les deux marchent, mais "Utility" est moins cher en coût Meta)
3. **Language** : `French (fr)`
4. Clique sur **"Continue"**

### 6.3 — Composer le message

Dans l'éditeur de template :

**Body (corps du message)** :

```
Bonjour {{1}},

Ton abonnement « {{2}} » à T-GYM arrive à expiration le {{3}}.

Pour garder ta lancée et continuer à profiter de la salle, passe nous voir ou réponds à ce message pour renouveler.

À très vite,
L'équipe T-GYM 💪
```

Les `{{1}}`, `{{2}}`, `{{3}}` sont les **variables** qui seront remplacées dynamiquement par T-GYM :
- `{{1}}` → prénom de l'adhérent
- `{{2}}` → nom de la formule (ex: "Premium")
- `{{3}}` → date d'expiration (ex: "15/07/2026")

> ⚠️ **Important** : l'ordre des variables dans le template doit correspondre à l'ordre dans lequel T-GYM les envoie. Dans `abonnements/whatsapp_api.py`, c'est :
> ```python
> {"type": "text", "text": prenom},       # {{1}}
> {"type": "text", "text": plan_nom},     # {{2}}
> {"type": "text", "text": date_fin},     # {{3}}
> ```
> ✅ Ça correspond bien.

### 6.4 — Soumettre pour approbation

1. Clique sur **"Submit"** (Soumettre)
2. Meta examine le template (5 min à 24h, généralement < 15 min)
3. Tu recevras une notification quand il sera approuvé

> 💡 Si Meta rejette le template, ils donnent une raison (ex: "trop promotionnel", "contenu non clair"). Corrige et resoumets.

---

## 🚀 Étape 7 — Passer en mode Live (production)

> En mode dev, tu ne peux envoyer qu'à 5 numéros. Pour envoyer à tous les adhérents, il faut passer en Live.

1. Retourne sur **[developers.facebook.com](https://developers.facebook.com)** → ton app `T-GYM WhatsApp`
2. En haut à droite, tu vois un switch **"Development mode"** → clique dessus
3. Meta te demande de **vérifier ton business** :
   - **Legal business name** : `T-GYM`
   - **Business address** : adresse de la salle
   - **Phone number** : numéro de la salle
   - **Documents** : registre de commerce, facture d'eau/électricité, ou document officiel
4. Soumets → vérification sous 24-48h (parfois plus)
5. Une fois validé, bascule le switch en **"Live"**

> ⚠️ **Coût** : à partir de ce moment, chaque conversation est facturée par Meta (voir résumé plus bas).

---

## 🔧 Étape 8 — Renseigner les variables dans T-GYM

Crée un fichier `.env` à la racine du projet (même niveau que `manage.py`) :

```bash
# WhatsApp Business Cloud API (Meta)
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_BUSINESS_ACCOUNT_ID=987654321098765
WHATSAPP_TEMPLATE_RELANCE=relance_abonnement
WHATSAPP_TEMPLATE_LANGUE=fr

# Gemini (optionnel, pour les messages IA)
GEMINI_API_KEY=AIzaxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Puis modifie `tgym_site/settings.py` pour charger le `.env` :

```python
# En haut du fichier
import os
from pathlib import Path

# Charger le .env manuellement (simple, pas de dépendance)
env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

# Plus bas, les variables existent déjà :
WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
# ...
```

> ⚠️ **Sécurité** : ajoute `.env` dans ton `.gitignore` pour ne jamais le committer.

---

## 🧪 Étape 9 — Tester

### 9.1 — Tester l'envoi d'un message

1. Dans l'admin Django, va sur un adhérent qui a un abonnement qui expire bientôt
2. Lance la commande :
   ```bash
   python manage.py generer_relances --jours 30
   ```
3. Puis :
   ```bash
   python manage.py envoyer_relances_whatsapp
   ```
4. Le téléphone de l'adhérent devrait recevoir le message

> ⚠️ **En mode dev**, l'adhérent doit être dans la liste des **5 numéros de test** (configurables dans la page WhatsApp de l'app Meta).

### 9.2 — Vérifier les logs

Si ça ne marche pas, regarde les logs Django :
```bash
python manage.py envoyer_relances_whatsapp 2>&1 | tee envoi.log
```

Les erreurs courantes :
- `HTTP 400` → template inconnu ou non approuvé
- `HTTP 403` → token invalide ou expiré
- `HTTP 131039` → numéro de destination pas dans la liste de test (mode dev)

---

## 💰 Rappel des coûts (par conversation de 24h)

| Type | Coût | Exemple |
|---|---|---|
| **Utility** (relance, rappel) | ~0.035 USD (~22 FCFA) | Ton template `relance_abonnement` en "Utility" |
| **Marketing** (promo, actu) | ~0.08 USD (~50 FCFA) | Si tu fais un template "promo Noel" |
| **Service** (réponse à un client) | ~0.008 USD (~5 FCFA) | Si le client t'écrit en premier |

> 💡 **Conseil** : crée ton template `relance_abonnement` en catégorie **"Utility"** plutôt que "Marketing" — c'est 2× moins cher.

---

## ✅ Checklist finale

- [ ] Compte Meta Business créé
- [ ] App Meta Developer créée (type "Business")
- [ ] WhatsApp ajouté à l'app
- [ ] Numéro dédié ajouté et vérifié
- [ ] `WHATSAPP_PHONE_NUMBER_ID` copié
- [ ] `WHATSAPP_BUSINESS_ACCOUNT_ID` copié
- [ ] System User créé
- [ ] Token permanent généré avec permissions `whatsapp_business_messaging` + `whatsapp_business_management`
- [ ] `WHATSAPP_ACCESS_TOKEN` copié
- [ ] Template `relance_abonnement` créé et **approuvé** (catégorie Utility)
- [ ] Fichier `.env` créé à la racine
- [ ] `.env` ajouté au `.gitignore`
- [ ] Test d'envoi réussi en mode dev (5 numéros de test)
- [ ] Business vérifié par Meta (pour passer en Live)

---

## 🆘 En cas de blocage

Les interfaces Meta changent souvent. Si un bouton a changé de place :
- Cherche dans la doc officielle : [developers.facebook.com/docs/whatsapp/cloud-api](https://developers.facebook.com/docs/whatsapp/cloud-api)
- Ou dis-moi où tu es bloqué, je te guide en direct

---

Une fois tout ça fait, T-GYM pourra envoyer des relances automatiques à tous les adhérents dont l'abonnement expire. Tu veux qu'on passe à la suite (chatbot Gemini sur le site, ou déploiement Render) ?