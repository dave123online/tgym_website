# T-GYM — Site Web (Phase 1 + 1.5)

Projet Django, même stack que Akem FS (SQLite en dev, prêt pour Postgres/Render en prod).

## Ce qui est livré

**Phase 1 — Vitrine + Tarifs + Funnel WhatsApp**
- Vitrine : Accueil, La Méthode, Où nous trouver
- Grille tarifaire dynamique (Premium + 3 formules flexibles), éditable depuis l'admin
- Funnel WhatsApp : chaque plan génère un lien `wa.me` pré-rempli (aucun envoi automatique — c'est toujours le visiteur qui clique)
- Bandeau coulissant ("Top Body") piloté depuis l'admin (`Annonce`)
- Configuration du site centralisée (`SiteConfig`) : contacts, horaires, réseaux, localisation
- Lien Google Maps direct (avec GPS si renseigné, sinon adresse texte en fallback) — pas d'API, pas de clé
- Admin Django personnalisé en français

**Phase 1.5 — Programmes (dont "45 jours pour maigrir")**
- App `coaching` : modèle `Programme` extensible (titre, accroche, durée, objectif, inclus, tarif)
- Page liste `/programmes/` + fiche détail `/programmes/<slug>/`
- Le programme marqué "phare" (`est_phare=True`) s'affiche automatiquement sur l'Accueil et La Méthode via le context processor global — aucune donnée en dur dans les templates
- Lien WhatsApp contextualisé ("Bonjour, j'ai une question à propos de : le programme 45 jours pour maigrir")

## Apps

- `core` : pages publiques, `SiteConfig`, `Annonce`, `whatsapp.py` (builder de liens)
- `abonnements` : modèle `Plan` (grille tarifaire)
- `coaching` : modèle `Programme` (programmes phares, extensible)
- `actualites` : générée mais **volontairement vide** — réservée à la Phase 2

## Démarrage rapide

```bash
cd tgym_site
python3 -m venv venv && source venv/bin/activate
pip install django

python manage.py migrate
python manage.py seed_tgym        # charge les vraies données (config, tarifs, programme phare, annonce démo)
python manage.py createsuperuser  # ton compte admin

python manage.py runserver
```

Puis :
- Site : http://127.0.0.1:8000/
- Admin : http://127.0.0.1:8000/admin/

## Modifier le contenu sans toucher au code

Tout se fait dans `/admin/` :
- **Configuration du site** → contacts WhatsApp, horaires, Facebook, adresse, GPS
- **Formules tarifaires** → prix, contenu inclus, mise en avant ("populaire")
- **Programmes** → ajouter/modifier un programme, cocher "Programme phare" pour le mettre en avant sur l'accueil
- **Annonces (bandeau)** → activer/désactiver le bandeau coulissant, programmer une date de fin

## Prochaines étapes (pas encore construites)

- Phase 2 : Actualités + bandeau "Top Body News" auto-alimenté (app `actualites`)
- Phase 3 (nécessite WhatsApp Business Cloud API côté Meta) : comptes adhérents/coachs, relance automatique, diffusion d'actus en masse, chatbot Gemini

## Déploiement (à venir)

Même logique qu'Akem FS : Render + WhiteNoise pour le statique, variables d'environnement pour `SECRET_KEY`/`DEBUG`/`ALLOWED_HOSTS`, Postgres en prod. Pas encore configuré — on le fera à l'étape déploiement.

