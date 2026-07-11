# Guide — Remplir T-GYM en vidéos (et photos)

Tout se fait depuis l'admin Django (`/admin/`), aucun code à toucher.
Trois emplacements différents, trois usages différents — ce guide explique
lequel utiliser pour quoi, et comment préparer les fichiers avant upload.

---

## 1. Vue d'ensemble : où va quoi

| Emplacement | Modèle / champ | Usage sur le site |
|---|---|---|
| Fond de la page d'accueil | `SiteConfig` → `hero_video` / `hero_image` | Une seule vidéo (ou photo), plein cadre, derrière le titre |
| Mur "Dans nos murs" | `VideoSalle` (sans programme associé) + `PhotoSalle` | Mosaïque de plusieurs vidéos/photos, ambiance générale |
| Section programme phare | `VideoSalle` (avec `programme` renseigné) | Une vidéo par programme, en cadre "écran de téléphone" |

Règle simple : **si la vidéo montre un programme précis** (ex: une séance
du "45 jours pour maigrir"), tu l'associes à ce programme → elle sort
dans la section dédiée. **Sinon** (ambiance générale, salle, matériel,
coach qui bosse), tu la laisses sans programme → elle va dans le mur.

---

## 2. Étape par étape

### A. La vidéo de fond de l'accueil (optionnel, une seule)

1. `/admin/core/siteconfig/1/change/`
2. Section **"Photo / vidéo d'accueil"**
3. Upload dans `hero_video` (ou `hero_image` si tu préfères une photo)

- Si les deux sont renseignés, la vidéo prend le dessus.
- Cette vidéo est vue en tout premier par chaque visiteur → choisis ta
  meilleure prise, celle qui donne le plus envie de pousser la porte.

### B. Les vidéos du mur "Dans nos murs" (autant que tu veux)

1. `/admin/core/videosalle/add/`
2. Upload dans `fichier`
3. **Laisse `programme` vide**
4. `légende` optionnelle (ex: "Séance du matin")
5. `ordre_affichage` : les plus petits chiffres passent en premier

Répète pour chaque vidéo généraliste. Idem pour les photos via
`/admin/core/photosalle/add/`.

### C. Les vidéos d'un programme phare (une ou plusieurs par programme)

1. `/admin/core/videosalle/add/`
2. Upload dans `fichier`
3. **Renseigne `programme`** → choisis le programme concerné (ex: "45
   jours pour maigrir")
4. Si plusieurs vidéos sont liées au même programme phare, seule la
   première (par `ordre_affichage`) s'affiche sur l'accueil — les autres
   sont prêtes pour le jour où la fiche programme elle-même affichera une
   galerie (pas encore fait, mais les données seront déjà là)

---

## 3. Spécifications techniques recommandées

| Emplacement | Format conseillé | Orientation | Durée | Poids |
|---|---|---|---|---|
| Hero (fond d'accueil) | MP4 (H.264) | Paysage (16:9) | 8–15s en boucle | < 8 Mo idéalement |
| Mur "Dans nos murs" | MP4 (H.264) | Paysage OU portrait — les deux marchent | 5–12s en boucle | < 6 Mo par vidéo |
| Programme phare | MP4 (H.264) | **Portrait (9:16)** de préférence — c'est le format du cadre | 8–20s | < 8 Mo |

Points importants :
- **Pas besoin de son.** Toutes les vidéos sont lues en muet + boucle
  automatique (obligatoire techniquement pour l'autoplay navigateur, donc
  ne compte pas dessus pour transmettre un message audio).
- **Le cadrage s'adapte tout seul** (`object-fit: cover`) : une vidéo
  paysage dans le cadre portrait du programme phare sera recadrée
  (bords coupés à gauche/droite), pas déformée. Mais le rendu est
  meilleur si tu filmes déjà en portrait pour cet emplacement.
- **Poids = vitesse de chargement.** Une vidéo de 40 Mo va ramer sur la
  connexion d'un visiteur au Bénin. Vise systématiquement sous 8 Mo.

### Comprimer une vidéo avant upload (si tu as `ffmpeg`)

```bash
# Redimensionne en largeur 1080px, compresse, enlève le son
ffmpeg -i original.mp4 -vf "scale=1080:-2" -an -c:v libx264 -crf 28 -preset veryfast web.mp4
```

Pour une vidéo portrait (programme phare), remplace juste la largeur par
la hauteur si ta source est déjà verticale : `scale=-2:1080`.

---

## 4. Aperçu (poster) — recommandé mais pas obligatoire

Chaque `VideoSalle` a un champ `apercu` (image). C'est l'image affichée
le temps que la vidéo charge — évite l'écran noir/blanc le temps du
chargement, surtout sur connexion lente. Pas indispensable (la section
fonctionne sans), mais ça améliore nettement la première impression.
Simple screenshot d'une bonne frame de la vidéo suffit.

---

## 5. Ce qui se passe si une section est vide

Toutes les sections média (mur, programme phare) se masquent
automatiquement s'il n'y a rien à montrer — pas de cadre vide ni
d'erreur. Tu peux donc remplir le site progressivement, section par
section, sans jamais rien casser entre deux ajouts.

---

## 6. Conseil de tri avant de tout uploader d'un coup

Avec "un petit paquet" de vidéos à trier :
1. Sépare-les en deux tas : **liées à un programme précis** vs
   **généralistes**.
2. Dans le tas généraliste, garde de la variété (matériel, ambiance,
   coach, extérieur/enseigne...) — le mur est plus vivant avec des plans
   différents qu'avec 8 fois le même angle.
3. Upload 3-4 vidéos généralistes pour commencer, regarde le rendu sur
   le site, ajuste l'ordre si besoin, puis complète.
