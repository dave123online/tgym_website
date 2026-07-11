# Guide — Remplir T-GYM en vidéos (et photos)

Tout se fait depuis l'admin Django (`/admin/`), aucun code à toucher.

---

## 1. Vue d'ensemble : où va quoi

| Type de vidéo | Champ `programme` | Champ `type_video` | Apparaît sur |
|---|---|---|---|
| Généraliste (ambiance, matériel, salle) | vide | *(peu importe, remis à "Généraliste" automatiquement)* | Mur vidéo de l'accueil **et** de `/tarifs/` |
| Activité "45 jours pour maigrir" | 45 jours pour maigrir | Activité | Section programme phare de l'accueil (1ère en cadre portrait, les suivantes en rangée) |
| Témoignage "45 jours pour maigrir" | 45 jours pour maigrir | Témoignage | Carrousel témoignages, section programme phare de l'accueil |

Fond de page d'accueil : à part, un seul champ dédié (voir point 2A).

---

## 2. Étape par étape

### A. La vidéo de fond de l'accueil (optionnel, une seule)
1. `/admin/core/siteconfig/1/change/` → section **"Photo / vidéo d'accueil"**
2. Upload dans `hero_video` (ou `hero_image` pour une photo)
3. Si les deux sont renseignés, la vidéo prend le dessus.

### B. Vidéos généralistes (mur, accueil + tarifs)
1. `/admin/core/videosalle/add/`
2. Upload dans `fichier`
3. **Laisse `programme` vide** (le type se remet tout seul sur "Généraliste")
4. `légende` optionnelle, `ordre_affichage` pour l'ordre (plus petit = en premier)

### C. Vidéos "activité" du programme phare
1. `/admin/core/videosalle/add/`
2. Upload dans `fichier`
3. `programme` → choisis le programme (ex: "45 jours pour maigrir")
4. `type_video` → **Activité**
5. La 1ère (par `ordre_affichage`) s'affiche en grand cadre portrait, les suivantes en rangée de vignettes en dessous

### D. Vidéos "témoignage" du programme phare
1. Même écran, mêmes étapes B/C, mais `type_video` → **Témoignage**
2. Idéalement 4 à 7 vidéos : le carrousel les affiche toutes en vignettes, une lecture active à la fois, enchaînement automatique en boucle avec le son (bouton "Activer le son" au premier clic — c'est une contrainte navigateur, pas un bug)
3. **Coupe uniquement les passages intéressants** avant l'upload (voir §5) — le carrousel n'a pas de fonction de découpage, il lit le fichier tel quel du début à la fin

---

## 3. Spécifications techniques recommandées

| Emplacement | Format | Orientation | Durée | Poids |
|---|---|---|---|---|
| Hero (fond d'accueil) | MP4 (H.264) | Paysage (16:9) | 8–15s boucle | < 8 Mo |
| Mur généraliste (accueil + tarifs) | MP4 (H.264) | Paysage ou portrait | 5–12s boucle | < 6 Mo/vidéo |
| Activité (programme phare) | MP4 (H.264) | **Portrait (9:16)** de préférence | 8–20s | < 8 Mo |
| Témoignage (carrousel) | MP4 (H.264) | **Portrait (9:16)** de préférence | 15–45s (le passage coupé) | < 10 Mo |

- **Généraliste, activité** : pas besoin de son (lues en muet/boucle).
- **Témoignage** : le son compte, coupe le passage pour que le début
  tombe directement sur la phrase intéressante (pas de "euh, alors..."
  avant).
- Le cadrage s'adapte automatiquement (`object-fit: cover`) : une vidéo
  paysage dans un cadre portrait sera recadrée (bords coupés), pas
  déformée — mais le rendu est meilleur si tu filmes déjà dans le bon
  format.
- Poids = vitesse de chargement, vise systématiquement sous 8-10 Mo par
  fichier (connexion Bénin).

### Comprimer une vidéo avant upload (si tu as `ffmpeg`)

```bash
# Paysage, largeur 1080px
ffmpeg -i original.mp4 -vf "scale=1080:-2" -an -c:v libx264 -crf 28 -preset veryfast web.mp4

# Portrait, hauteur 1080px
ffmpeg -i original.mp4 -vf "scale=-2:1080" -c:v libx264 -crf 26 -preset veryfast -c:a aac -b:a 96k portrait.mp4
```

Retire `-an` pour les témoignages (garde le son), garde-le pour
généraliste/activité (pas besoin de son, fichier plus léger).

### Découper un passage précis (témoignages)

```bash
# Extrait de 0:32 à 1:05 par exemple
ffmpeg -i temoignage_brut.mp4 -ss 00:00:32 -to 00:01:05 -c copy temoignage_extrait.mp4
```

---

## 4. Aperçu (poster)

Chaque vidéo a un champ `apercu` (image), affiché le temps du
chargement — évite l'écran noir/blanc. Recommandé mais pas obligatoire,
un simple screenshot d'une bonne frame suffit. Particulièrement utile
sur les vignettes témoignages (identifie visuellement qui parle avant
de cliquer).

---

## 5. Ce qui se passe si une section est vide

Toutes les sections média se masquent automatiquement s'il n'y a rien à
afficher — pas de cadre vide ni d'erreur. Remplissage progressif possible,
section par section, sans jamais rien casser.

---

## 6. Conseil de tri et quantités

- **Généraliste** : 6 à 8 vidéos, varie les plans (matériel, ambiance,
  coach, enseigne...) — plus que ça pèse sur le chargement en lecture
  simultanée.
- **Activité** : 3 à 5 (1 portrait principale + le reste en rangée).
- **Témoignage** : 4 à 7. Coupe large au départ (garde 1-2 min par
  personne), puis resserre sur la phrase/le passage qui vend vraiment le
  programme — mieux vaut 20 secondes percutantes que 2 minutes diluées.
- Upload 3-4 vidéos par catégorie pour commencer, regarde le rendu sur
  le site, ajuste l'ordre (`ordre_affichage`), puis complète.