import re

# Préfixes internationaux du Bénin qu'on retire en tête de numéro, dans
# l'ordre du plus long au plus court pour ne pas laisser un "00" traîner
# après avoir retiré seulement "229" d'un "00229...".
PREFIXES_A_RETIRER = ["00229", "+229", "229"]


def normaliser_telephone(valeur: str) -> str:
    """
    Normalise un numéro de téléphone pour comparaison/stockage : retire les
    espaces, puis un éventuel préfixe international béninois en tête
    (00229, +229, 229), pour ne garder que le numéro local.

    "+229 94140535" -> "94140535"
    "00229 94 14 05 35" -> "94140535"
    "94140535" -> "94140535" (inchangé)
    """
    valeur = re.sub(r"\s+", "", valeur or "")
    for prefixe in PREFIXES_A_RETIRER:
        if valeur.startswith(prefixe):
            return valeur[len(prefixe):]
    return valeur



