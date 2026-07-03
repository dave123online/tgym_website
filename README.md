# T-GYM — Site Web (Phase 1 : Vitrine + Tarifs + Funnel WhatsApp)

Projet Django, même stack que Akem FS (SQLite en dev, prêt pour Postgres/Render en prod).

## Ce qui est livré dans cette Phase 1

- Vitrine : Accueil, La Méthode, Où nous trouver
- Grille tarifaire dynamique (Premium + 3 formules flexibles), éditable depuis l'admin
- Funnel WhatsApp : chaque plan génère un lien `wa.me` pré-rempli (aucun envoi automatique — c'est toujours le visiteur qui clique, comme sur Akem FS)
- Bandeau coulissant ("Top Body") piloté depuis l'admin (`Annonce`)
- Configuration du site centralisée (`SiteConfig`) : contacts, horaires, réseaux — un seul endroit à modifier, aucune valeur en dur dans le code
- Admin Django personnalisé en français

## Apps créées (rôles pour la suite)

- `core` : pages publiques, `SiteConfig`, `Annonce`, `whatsapp.py` (builder de liens)
- `abonnements` : modèle `Plan` (grille tarifaire)
- `coaching`, `actualites` : générées mais **volontairement vides** — réservées aux Phases 1.5/2 (programme "45 jours pour maigrir", actualités)

## Démarrage rapide

```bash
cd tgym_site
python3 -m venv venv && source venv/bin/activate
pip install django

python manage.py migrate
python manage.py seed_tgym        # charge les vraies données (config, tarifs, annonce démo)
python manage.py createsuperuser  # ton compte admin

python manage.py runserver
```

Puis :
- Site : http://127.0.0.1:8000/
- Admin : http://127.0.0.1:8000/admin/

## Modifier le contenu sans toucher au code

Tout se fait dans `/admin/` :
- **Configuration du site** → contacts WhatsApp, horaires, Facebook, adresse
- **Formules tarifaires** → prix, contenu inclus, mise en avant ("populaire")
- **Annonces (bandeau)** → activer/désactiver le bandeau coulissant, programmer une date de fin

## Prochaines étapes (pas encore construites)

- Phase 1.5 : page "45 jours pour maigrir" dédiée (app `coaching`)
- Phase 2 : Actualités + bandeau "Top Body News" auto-alimenté (app `actualites`)
- Phase 3 (nécessite WhatsApp Business Cloud API côté Meta) : comptes adhérents/coachs, relance automatique, diffusion d'actus en masse, chatbot Gemini

## Déploiement (à venir)

Même logique qu'Akem FS : Render + WhiteNoise pour le statique, variables d'environnement pour `SECRET_KEY`/`DEBUG`/`ALLOWED_HOSTS`, Postgres en prod. Pas encore configuré dans cette Phase 1 — on le fera à l'étape déploiement.
