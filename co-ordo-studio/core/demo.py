from __future__ import annotations
from .models import DocumentBlock

def demo_blocks():
    return [
        DocumentBlock("p-0", 0, "★ Mémoire de travail : système permettant de maintenir temporairement et manipuler des informations.", "Titre2", True),
        DocumentBlock("p-1", 1, "La boucle phonologique permet le maintien temporaire des informations verbales.", "Normal", False),
        DocumentBlock("p-2", 2, "L'administrateur central coordonne les différents sous-systèmes.", "Normal", False),
        DocumentBlock("p-3", 3, "Exemple : retenir temporairement un numéro de téléphone.", "Normal", False),
        DocumentBlock("p-4", 4, "Historique du modèle proposé en 1974.", "Normal", False),
    ]
