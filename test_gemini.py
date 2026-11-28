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
2. Ignore les lignes et la marge du cahier : elles ne font pas partie du contenu. Ignore aussi les dates en marge et les numéros de page.
3. Corrige uniquement l'orthographe, la grammaire et la ponctuation du texte rédigé (mots). Ne corrige jamais ce qui est un symbole, une abréviation ou une notation technique.
4. Recopie les numéros et puces (1), 2), I-, a), etc.) EXACTEMENT comme écrits, sans les harmoniser. Si un doute existe, signale-le dans "alertes".
5. Ne modifie JAMAIS un chiffre, une unité, une formule ou un résultat de calcul : recopie-les tels qu'écrits, y compris le séparateur décimal (virgule ou point) tel qu'il apparaît.
6. N'AJOUTE JAMAIS de parenthèses, crochets, signes ou espaces qui ne sont pas dans le cahier. Si la formule n'a pas de parenthèses, tu n'en écris pas.
7. Recopie les notations techniques lettre par lettre, avec leurs indices et exposants (SD, SH, ST, LdT, LdH, LdV, Larc, B1, b2, m, n, etc.). Ne remplace jamais une lettre par une autre qui te semble plus logique. Si deux lectures sont possibles, écris celle que tu vois et signale le doute dans "alertes".
8. N'effectue AUCUN calcul. Ne vérifie pas l'arithmétique. N'écris jamais d'alerte du type "le résultat devrait être...". Les alertes servent UNIQUEMENT à signaler une lecture incertaine (écriture ambiguë, scan flou, passage illisible, numérotation douteuse).
9. Si un mot ou un chiffre est illisible, écris [illisible] à sa place et signale-le dans "alertes". N'invente jamais un contenu pour combler un trou.
10. Pour chaque schéma, ne dessine rien et n'interprète rien : décris seulement ce qui est dessiné et écrit. Dans "cotes" et "elements", ne mets QUE les valeurs réellement écrites sur le dessin, jamais une valeur déduite ou calculée. Si tu ne sais pas à quoi une cote se rapporte, mets "mesure": "incertain" et signale-le dans "alertes".
11. "couleurs" : uniquement les couleurs utilisées dans le dessin lui-même (hachures, remplissages, traits colorés) avec ce qu'elles colorent. Liste vide si le dessin est à l'encre normale. Ne mentionne jamais l'encre du texte ni le papier.
12. Si la page est floue ou en grande partie illisible, ne devine pas : transcris ce qui est lisible et signale-le dans "alertes".
13. Indique si le contenu continue sur la page suivante (énoncé coupé, solution annoncée mais absente, etc.).

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
