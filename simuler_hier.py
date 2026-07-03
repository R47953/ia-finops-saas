from datetime import date, timedelta
from database import SessionLocal
import models

def simuler_date_passee():
    # 1. Ouvrir une session avec la base de données
    db = SessionLocal()
    
    try:
        # 2. Chercher ton utilisateur de test (ajuste l'email si besoin)
        email_cible = "test@finops.com"
        utilisateur = db.query(models.Utilisateur).filter(models.Utilisateur.email == email_cible).first()
        
        if utilisateur:
            # Calculer la date d'hier (30 juin 2026)
            hier = date.today() - timedelta(days=1)
            
            # 3. Modifier les valeurs pour simuler un quota bloqué hier
            utilisateur.derniere_analyse_date = hier
            utilisateur.nb_analyses_aujourdhui = 5
            
            # 4. Sauvegarder les modifications en base
            db.commit()
            
            print(f"✅ Simulation réussie pour {email_cible} !")
            print(f"   -> Date enregistrée : {utilisateur.derniere_analyse_date} (Hier)")
            print(f"   -> Compteur actuel  : {utilisateur.nb_analyses_aujourdhui}/5 (Bloqué)")
            print("\n🚀 Lance maintenant une requête depuis VS Code : l'API devrait réinitialiser le compteur à 0 automatiquement !")
        else:
            print(f"❌ Erreur : Aucun utilisateur trouvé avec l'email '{email_cible}'")
            
    except Exception as e:
        print(f"❌ Une erreur est survenue : {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    simuler_date_passee()