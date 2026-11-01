# test_gemini.py
# Utilisation : python3 test_gemini.py scans/page_001.jpg
import json
import os
import sys

from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

FICHIER_CLES = "secret/.env"
MODELES = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"]

PROMPT = """Tu transcris une page scannée d'un cahier de cours de BEP (bâtiment, terrassements), écrite à la main en français.

RÈGLES
1. Transcris fidèlement TOUT le contenu, dans l'ordre de lecture.
2. Ignore les lignes et la marge du cahier : elles ne font pas partie du contenu.
3. Corrige l'orthographe, la grammaire et la ponctuation du texte rédigé.
4. Recopie les numéros et puces (1), 2), I-, etc.) exactement comme écrits. Si un doute existe, signale-le dans "alertes".
5. Ne modifie JAMAIS un chiffre, une unité, une formule ou un résultat de calcul : recopie-les tels qu'écrits.
6. Si un calcul te semble faux, signale-le dans "alertes" sans le corriger.
7. Si un mot ou un chiffre est illisible, écris [illisible] et signale-le dans "alertes".
8. Pour chaque schéma, ne dessine rien et n'interprète rien : décris seulement ce qui est dessiné et écrit. Si un sens est incertain, signale-le dans "alertes".
9. "couleurs" : uniquement les couleurs utilisées dans le dessin lui-même (hachures, remplissages, traits colorés) avec ce qu'elles colorent. Liste vide si le dessin est à l'encre normale. Ne mentionne jamais l'encre du texte ni le papier.
10. Indique si le contenu continue sur la page suivante (énoncé coupé, solution annoncée mais absente, etc.).

Réponds uniquement en JSON, avec cette structure :
{
  "contenu": [
    {"type": "titre", "texte": "..."},
    {"type": "paragraphe", "texte": "..."},
    {"type": "calcul", "lignes": ["...", "..."]},
    {"type": "schema",
     "description": "ce qui est dessiné, en une ou deux phrases",
     "elements": [
       {"genre": "rectangle", "role": "mur extérieur", "largeur_cote": "6.30", "hauteur_cote": "5.30"},
       {"genre": "ouverture", "sorte": "porte", "mur": "bas", "avec_arc": true},
       {"genre": "ouverture", "sorte": "fenêtre", "mur": "droit"},
       {"genre": "arc", "rayon_cote": "85 cm", "coin": "bas-droit"},
       {"genre": "triangle", "base_cote": "2", "hauteur_cote": "2", "emplacement": "coin bas-droit"}
     ],
     "cotes": [{"valeur": "6.00", "mesure": "ce que la flèche ou le trait délimite visiblement", "position": "haut"}],
     "hachures": [{"zone": "...", "couleur": "...", "etiquette": "SH"}],
     "couleurs": [],
     "annotations": ["texte écrit dans ou autour du dessin, tel quel"]}
  ],
  "alertes": ["..."],
  "continue_sur_page_suivante": false
}"""

def lire_page(client, chemin):
    image = Image.open(chemin)
    derniere_erreur = None
    for modele in MODELES:
        try:
            reponse = client.models.generate_content(
                model=modele,
                contents=[image, PROMPT],
                config=types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json",
                ),
            )
            print(f"[ok] modèle utilisé : {modele}")
            return json.loads(reponse.text)
        except Exception as e:
            print(f"[échec] {modele} : {str(e)[:150]}")
            derniere_erreur = e
    raise derniere_erreur


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage : python3 test_gemini.py scans/page_001.jpg")

    load_dotenv(FICHIER_CLES)
    cle = os.getenv("GEMINI_API_KEY")
    if not cle:
        sys.exit(f"GEMINI_API_KEY introuvable dans {FICHIER_CLES}")

    client = genai.Client(api_key=cle)
    donnees = lire_page(client, sys.argv[1])

    os.makedirs("sortie", exist_ok=True)
    nom = os.path.splitext(os.path.basename(sys.argv[1]))[0]
    sortie = os.path.join("sortie", f"{nom}.json")
    with open(sortie, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=2)

    print(json.dumps(donnees, ensure_ascii=False, indent=2))
    print(f"\nSauvegardé dans {sortie}")


if __name__ == "__main__":
    main()
