from database import SessionLocal
import models

def forcer_quota():
    db = SessionLocal()
    try:
        # Remplace par l'email que tu as utilisé
        email_cible = "test@finops.com" 
        
        utilisateur = db.query(models.Utilisateur).filter(models.Utilisateur.email == email_cible).first()
        
        if utilisateur:
            utilisateur.nb_analyses_aujourdhui = 5
            db.commit()
            print(f"✅ Succès : Le compteur de {email_cible} est maintenant à {utilisateur.nb_analyses_aujourdhui}")
        else:
            print(f"❌ Erreur : Aucun utilisateur trouvé avec l'email {email_cible}")
    finally:
        db.close()

if __name__ == "__main__":
    forcer_quota()