# traiter.py : lit les pages de scans/ et écrit un JSON par page dans resultats/
import json
import os
import sys
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

from test_gemini import PROMPT

DOSSIER_SCANS = "scans"
DOSSIER_RESULTATS = "resultats"
RAPPORT = "rapport.json"
EXTENSIONS = (".jpg", ".jpeg", ".png")

# Chaque modèle a son propre quota gratuit : on les utilise l'un après l'autre
MODELES = [
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
]

PAUSE_ENTRE_PAGES = 6
ATTENTE_QUOTA_MINUTE = 65
ATTENTE_SURCHARGE = 20
ECHECS_CONSECUTIFS_MAX = 3


class QuotaEpuise(Exception):
    pass


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


def classer(erreur):
    t = str(erreur)
    if "404" in t or "NOT_FOUND" in t:
        return "absent"
    if "429" in t or "RESOURCE_EXHAUSTED" in t:
        return "quota_jour" if "PerDay" in t else "quota_minute"
    if "503" in t or "500" in t or "UNAVAILABLE" in t:
        return "surcharge"
    return "autre"


def lire_page(client, chemin, morts):
    """Essaie les modèles dans l'ordre. 'morts' = modèles inutilisables pour ce run."""
    image = Image.open(chemin)
    nom = os.path.basename(chemin)

    for modele in MODELES:
        if modele in morts:
            continue
        for tentative in (1, 2):
            try:
                reponse = client.models.generate_content(
                    model=modele,
                    contents=[image, PROMPT],
                    config=types.GenerateContentConfig(
                        temperature=0,
                        response_mime_type="application/json",
                    ),
                )
                donnees = json.loads(reponse.text)
                if not valide(donnees):
                    raise ValueError("réponse vide ou invalide")
                donnees["_modele"] = modele
                print(f"[ok] {nom} lu par {modele}")
                return donnees
            except Exception as e:
                genre = classer(e)
                print(f"[{genre}] {nom} / {modele} : {str(e)[:120]}")
                if genre in ("absent", "quota_jour"):
                    morts.add(modele)
                    break
                if tentative == 1 and genre in ("quota_minute", "surcharge"):
                    time.sleep(ATTENTE_QUOTA_MINUTE if genre == "quota_minute" else ATTENTE_SURCHARGE)
                    continue
                if genre == "quota_minute":
                    morts.add(modele)   # toujours bloqué après attente : on le laisse de côté
                break

    if all(m in morts for m in MODELES):
        raise QuotaEpuise()
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
        f.write(f"| Restantes (reprise automatique) | {len(rapport['restantes'])} |\n")
        if rapport["quota_epuise"]:
            f.write("\nQuota gratuit épuisé : le travail reprendra au prochain lancement.\n")
        if rapport["echecs"]:
            f.write("\nÉchecs : " + ", ".join(rapport["echecs"]) + "\n")


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
        "quota_epuise": False,
    }
    print(f"{len(pages)} page(s) trouvée(s)")

    morts = set()
    consecutifs = 0
    arret = False

    for nom in pages:
        sortie = os.path.join(DOSSIER_RESULTATS, os.path.splitext(nom)[0] + ".json")

        if os.path.exists(sortie):
            rapport["deja_faites"].append(nom)
            continue

        if arret or consecutifs >= ECHECS_CONSECUTIFS_MAX:
            rapport["restantes"].append(nom)
            continue

        try:
            donnees = lire_page(client, os.path.join(DOSSIER_SCANS, nom), morts)
        except QuotaEpuise:
            rapport["quota_epuise"] = True
            rapport["restantes"].append(nom)
            arret = True
            continue

        if donnees is None:
            rapport["echecs"].append(nom)
            consecutifs += 1
            continue

        consecutifs = 0
        with open(sortie, "w", encoding="utf-8") as f:
            json.dump(donnees, f, ensure_ascii=False, indent=2)
        rapport["traitees"].append(nom)
        time.sleep(PAUSE_ENTRE_PAGES)

    with open(RAPPORT, "w", encoding="utf-8") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=2)
    ecrire_resume(rapport)

    if rapport["restantes"]:
        print(f"{len(rapport['restantes'])} page(s) restante(s), reprise au prochain lancement.")
    if rapport["echecs"]:
        print("Pages en échec : voir rapport.json")
        sys.exit(1)   # rouge seulement pour une vraie erreur, pas pour un simple quota
    print("Terminé.")


if __name__ == "__main__":
    main()
