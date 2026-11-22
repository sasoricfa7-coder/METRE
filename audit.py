# audit.py : bilan de qualité des JSON de resultats/ (ne modifie rien)
import glob
import json
import os
from collections import Counter

modeles = Counter()
sans_modele = []
vides = []
avec_alertes = []
illisibles = []
suites = []
schemas = 0
calculs = 0

for chemin in sorted(glob.glob("resultats/*.json")):
    nom = os.path.splitext(os.path.basename(chemin))[0]
    with open(chemin, encoding="utf-8") as f:
        d = json.load(f)

    modele = d.get("_modele")
    if modele:
        modeles[modele] += 1
    else:
        sans_modele.append(nom)

    contenu = d.get("contenu", [])
    if len(contenu) < 2:
        vides.append(nom)

    if d.get("alertes"):
        avec_alertes.append((nom, d["alertes"]))
    if "[illisible]" in json.dumps(d, ensure_ascii=False):
        illisibles.append(nom)
    if d.get("continue_sur_page_suivante"):
        suites.append(nom)

    schemas += sum(1 for b in contenu if b.get("type") == "schema")
    calculs += sum(1 for b in contenu if b.get("type") == "calcul")

print(f"Pages lues : {len(glob.glob('resultats/*.json'))}")
print(f"Schémas détectés : {schemas} | Blocs de calcul : {calculs}")
print("\nModèle utilisé :")
for m, n in modeles.most_common():
    print(f"  {m} : {n} page(s)")
print(f"  (non indiqué, anciennes versions) : {', '.join(sans_modele) or 'aucune'}")
print(f"\nPages presque vides (à revérifier en priorité) : {', '.join(vides) or 'aucune'}")
print(f"Pages avec [illisible] : {', '.join(illisibles) or 'aucune'}")
print(f"Pages qui continuent sur la suivante : {len(suites)}")
print(f"\nPages avec alertes : {len(avec_alertes)}")
for nom, al in avec_alertes:
    for a in al:
        print(f"  {nom} : {a}")
