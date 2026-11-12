# traiter.py : lit les pages de scans/ et écrit un JSON par page dans resultats/
import json
import os
import sys
import time

from dotenv import load_dotenv
from google import genai

from test_gemini import lire_page

DOSSIER_SCANS = "scans"
DOSSIER_RESULTATS = "resultats"
RAPPORT = "rapport.json"
EXTENSIONS = (".jpg", ".jpeg", ".png")
PAUSE_ENTRE_PAGES = 6        # secondes (reste sous 15 requêtes/minute)
ESSAIS = 3
ATTENTE_APRES_ECHEC = 65
ECHECS_CONSECUTIFS_MAX = 3   # au-delà : quota probablement épuisé, on s'arrête


def lister_pages():
    return sorted(
        f for f in os.listdir(DOSSIER_SCANS)
        if f.lower().endswith(EXTENSIONS)
    )


def valide(donnees):
    return (
        isinstance(donnees, dict)
        and isinstance(donnees.get("contenu"), list)
        and len(donnees["contenu"]) > 0
    )


def traiter_page(client, chemin):
    for essai in range(1, ESSAIS + 1):
        try:
            donnees = lire_page(client, chemin)
            if valide(donnees):
                return donnees
            print(f"[essai {essai}/{ESSAIS}] {os.path.basename(chemin)} : réponse vide ou invalide")
        except Exception as e:
            print(f"[essai {essai}/{ESSAIS}] {os.path.basename(chemin)} : {str(e)[:150]}")
        if essai < ESSAIS:
            time.sleep(ATTENTE_APRES_ECHEC)
    return None


def ecrire_resume(rapport):
    """Tableau lisible dans l'onglet Actions (uniquement sur GitHub)."""
    chemin = os.getenv("GITHUB_STEP_SUMMARY")
    if not chemin:
        return
    with open(chemin, "a", encoding="utf-8") as f:
        f.write("## Transcription du cours\n\n")
        f.write("| Statut | Pages |\n|---|---|\n")
        f.write(f"| Total scans | {rapport['total']} |\n")
        f.write(f"| Traitées maintenant | {len(rapport['traitees'])} |\n")
        f.write(f"| Déjà faites avant | {len(rapport['deja_faites'])} |\n")
        f.write(f"| En échec | {len(rapport['echecs'])} |\n")
        f.write(f"| Restantes (reprise au prochain lancement) | {len(rapport['restantes'])} |\n")
        if rapport["echecs"]:
            f.write("\nÉchecs : " + ", ".join(rapport["echecs"]) + "\n")
        if rapport["restantes"]:
            f.write("\nRestantes : " + ", ".join(rapport["restantes"]) + "\n")


def main():
    load_dotenv("secret/.env")  # en local ; sur GitHub la clé vient des Secrets
    cle = os.getenv("GEMINI_API_KEY")
    if not cle:
        sys.exit("GEMINI_API_KEY introuvable")

    client = genai.Client(api_key=cle)
    os.makedirs(DOSSIER_RESULTATS, exist_ok=True)

    pages = lister_pages()
    rapport = {
        "date": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "total": len(pages),
        "traitees": [],
        "deja_faites": [],
        "echecs": [],
        "restantes": [],
    }
    print(f"{len(pages)} page(s) trouvée(s)")

    consecutifs = 0
    for nom in pages:
        sortie = os.path.join(DOSSIER_RESULTATS, os.path.splitext(nom)[0] + ".json")

        if os.path.exists(sortie):
            rapport["deja_faites"].append(nom)
            continue

        if consecutifs >= ECHECS_CONSECUTIFS_MAX:
            rapport["restantes"].append(nom)
            continue

        donnees = traiter_page(client, os.path.join(DOSSIER_SCANS, nom))
        if donnees is None:
            rapport["echecs"].append(nom)
            consecutifs += 1
            continue

        consecutifs = 0
        with open(sortie, "w", encoding="utf-8") as f:
            json.dump(donnees, f, ensure_ascii=False, indent=2)
        rapport["traitees"].append(nom)
        print(f"[écrit] {sortie}")
        time.sleep(PAUSE_ENTRE_PAGES)

    with open(RAPPORT, "w", encoding="utf-8") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=2)
    ecrire_resume(rapport)

    if rapport["echecs"] or rapport["restantes"]:
        print("Travail incomplet : voir rapport.json")
        sys.exit(1)
    print("Toutes les pages sont traitées.")


if __name__ == "__main__":
    main()
