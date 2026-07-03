# analyseur.py
import os
from dotenv import load_dotenv
from groq import Groq

# 1. Charger les variables secrètes depuis le fichier .env
load_dotenv()
cle_api = os.getenv("GROQ_API_KEY")

if not cle_api:
    print("❌ Erreur : La clé GROQ_API_KEY n'a pas été trouvée dans le fichier .env")
    exit()

# 2. Initialiser le client IA avec Groq
client = Groq(api_key=cle_api)

# 3. Fonction pour lire le code du fichier à tester
def lire_code_client(chemin_fichier):
    with open(chemin_fichier, "r", encoding="utf-8") as fichier:
        return fichier.read()

# 4. Le Prompt : Nos instructions d'expert FinOps pour guider l'IA
INSTRUCTIONS_PROMPT = """
Tu es un expert mondial en ingénierie de performance logicielle et en FinOps (optimisation des coûts serveurs et cloud).
Ton but est de trouver les inefficacités critiques dans le code Python et les requêtes SQL que l'utilisateur va te soumettre.

Tu dois impérativement renvoyer ta réponse sous la forme de deux sections claires :
1. ANALYSE DU PROBLÈME : Explique brièvement en français pourquoi ce code coûte cher en temps de calcul ou en requêtes inutiles.
2. CODE OPTIMISÉ : Donne le code corrigé, propre, performant et directement copiable.
"""

def optimiser_mon_code(chemin_du_fichier):
    print(f"🔍 Lecture de {chemin_du_fichier}...")
    code_original = lire_code_client(chemin_du_fichier)
    
    print("🤖 Envoi à l'IA pour analyse de performance...")
    
    # Appel de l'IA (On utilise llama3-8b-8192 qui est ultra-rapide et gratuit)
    reponse = client.chat.completions.create(
        messages=[
            {"role": "system", "content": INSTRUCTIONS_PROMPT},
            {"role": "user", "content": f"Optimise ce code :\n\n{code_original}"}
        ],
        model="llama-3.1-8b-instant",
        temperature=0.2, # Température basse pour avoir des réponses logiques et précises
    )
    
    # Affichage du résultat renvoyé par l'IA
    print("\n" + "="*40 + " RÉSULTAT DU SAAS " + "="*40 + "\n")
    print(reponse.choices[0].message.content)
    print("\n" + "="*98)

# Lancement du script sur notre fichier de test
if __name__ == "__main__":
    optimiser_mon_code("code_a_tester.py")