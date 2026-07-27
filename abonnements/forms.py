from django import forms


class EnvoiMasseForm(forms.Form):
    nom_template = forms.CharField(
        label="Nom du template Meta",
        help_text="Doit correspondre exactement au nom du template approuvé dans le dashboard Meta.",
    )
    langue = forms.CharField(label="Code langue", initial="fr")
    parametres = forms.CharField(
        label="Variables du corps (séparées par des virgules)",
        required=False,
        help_text="Dans l'ordre {{1}}, {{2}}... Laisser vide si le template n'a pas de variable. "
                   "Attention : les mêmes valeurs seront envoyées à TOUS les contacts sélectionnés "
                   "(pas de personnalisation par contact pour l'instant).",
    )

    def parametres_liste(self) -> list[str]:
        brut = self.cleaned_data.get("parametres", "")
        return [p.strip() for p in brut.split(",") if p.strip()]

