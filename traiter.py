# traiter.py : lit toutes les pages de scans/ et écrit un JSON par page dans resultats/
import json
import os
import sys
import time

from dotenv import load_dotenv
from google import genai

from test_gemini import lire_page

DOSSIER_SCANS = "scans"
DOSSIER_RESULTATS = "resultats"
EXTENSIONS = (".jpg", ".jpeg", ".png")
PAUSE_ENTRE_PAGES = 6   # secondes (reste sous 15 requêtes/minute)
ESSAIS = 3
ATTENTE_APRES_ECHEC = 65


def lister_pages():
    return sorted(
        f for f in os.listdir(DOSSIER_SCANS)
        if f.lower().endswith(EXTENSIONS)
    )


def traiter_page(client, chemin):
    for essai in range(1, ESSAIS + 1):
        try:
            return lire_page(client, chemin)
        except Exception as e:
            print(f"[essai {essai}/{ESSAIS}] {os.path.basename(chemin)} : {str(e)[:150]}")
            if essai < ESSAIS:
                time.sleep(ATTENTE_APRES_ECHEC)
    return None


def main():
    load_dotenv("secret/.env")  # en local ; sur GitHub la clé vient des Secrets
    cle = os.getenv("GEMINI_API_KEY")
    if not cle:
        sys.exit("GEMINI_API_KEY introuvable")

    client = genai.Client(api_key=cle)
    os.makedirs(DOSSIER_RESULTATS, exist_ok=True)

    echecs = []
    pages = lister_pages()
    print(f"{len(pages)} page(s) trouvée(s)")

    for nom in pages:
        sortie = os.path.join(DOSSIER_RESULTATS, os.path.splitext(nom)[0] + ".json")
        if os.path.exists(sortie):
            print(f"[déjà fait] {nom}")
            continue

        donnees = traiter_page(client, os.path.join(DOSSIER_SCANS, nom))
        if donnees is None:
            echecs.append(nom)
            continue

        with open(sortie, "w", encoding="utf-8") as f:
            json.dump(donnees, f, ensure_ascii=False, indent=2)
        print(f"[écrit] {sortie}")
        time.sleep(PAUSE_ENTRE_PAGES)

    if echecs:
        print(f"Pages en échec : {', '.join(echecs)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
