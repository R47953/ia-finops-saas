# code_a_tester.py
import sqlite3

def recuperer_utilisateurs_et_commandes():
    conn = sqlite3.connect('boutique.db')
    cursor = conn.cursor()
    
    # On récupère tous les utilisateurs
    cursor.execute("SELECT id, nom FROM utilisateurs")
    utilisateurs = cursor.fetchall()
    
    resultat = []
    for user in utilisateurs:
        user_id = user[0]
        # ERREUR CRITIQUE : Une requête SQL exécutée À L'INTÉRIEUR d'une boucle. 
        # Si on a 10 000 utilisateurs, le script va faire 10 000 requêtes !
        cursor.execute(f"SELECT produit, prix FROM commandes WHERE utilisateur_id = {user_id}")
        commandes = cursor.fetchall()
        resultat.append({
            "nom": user[1],
            "commandes": commandes
        })
        
    conn.close()
    return resultat