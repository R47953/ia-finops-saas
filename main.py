# main.py
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq
import models
from database import engine, get_db
from sqlalchemy.orm import Session
from fastapi import Depends
from fastapi import Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.orm import Session
from datetime import date
from pydantic import BaseModel, EmailStr
from fastapi.middleware.cors import CORSMiddleware
from datetime import date
import random
from datetime import datetime, timedelta
import stripe
from fastapi.responses import RedirectResponse
from fastapi import Request
from dotenv import load_dotenv
import resend
from fastapi.middleware.cors import CORSMiddleware



# 1. Chargement de l'environnement et des clés
load_dotenv()

cle_api = os.getenv("GROQ_API_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")

if not cle_api:
    raise RuntimeError("❌ Clé GROQ_API_KEY manquante dans l'environnement")

client_ia = Groq(api_key=cle_api)

# Initialisation de Resend avec ta clé secrète
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
if not RESEND_API_KEY:
    raise RuntimeError("❌ Clé RESEND_API_KEY manquante dans l'environnement")

resend.api_key = RESEND_API_KEY

# 2. CREATION DE L'APPLICATION (DOIT ETRE FAIT AVANT LE CORS)
app = FastAPI(
    title="SaaS FinOps Optimizer API",
    description="API pour analyser et optimiser les performances du code backend.",
    version="0.1",
    docs_url="/docs",      
    redoc_url="/redoc"     
)

# 3. CONFIGURATION DU CORS (MAINTENANT QUE "APP" EXISTE)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Fonction qui va fouiller dans la BDD pour voir si la clé existe
def verifier_authentification(api_key: str = Depends(api_key_header), db: Session = Depends(get_db)):
    if not api_key:
        raise HTTPException(status_code=403, detail="Clé API manquante. En-tête X-API-Key requis.")
    
    utilisateur = db.query(models.Utilisateur).filter(models.Utilisateur.api_key == api_key).first()
    
    if not utilisateur:
        raise HTTPException(status_code=403, detail="Clé API invalide ou expirée.")
        
    # --- LOGIQUE DU PAYWALL ---
    aujourdhui = date.today()
    
    # Si la dernière analyse date d'un autre jour, on réinitialise son compteur journalier
    if utilisateur.derniere_analyse_date != aujourdhui:
        utilisateur.nb_analyses_aujourdhui = 0
        utilisateur.derniere_analyse_date = aujourdhui
        db.commit()

    # Si l'utilisateur a atteint ou dépassé son quota
    if utilisateur.nb_analyses_aujourdhui >= utilisateur.limite_quotidienne:
        raise HTTPException(
            status_code=429, 
            detail=f"Quota journalier atteint ({utilisateur.limite_quotidienne}/{utilisateur.limite_quotidienne}). Passez à l'offre Premium pour débloquer l'accès illimité !"
        )
        
    return utilisateur
models.Base.metadata.create_all(bind=engine)
# 3. Structure des données attendues (Pydantic)
# On demande au client de nous envoyer un JSON avec un champ 'code'
class DemandeOptimisation(BaseModel):
    code: str

# 4. Le Prompt système d'expert
INSTRUCTIONS_PROMPT = """
Tu es un expert mondial en ingénierie de performance logicielle et en FinOps.
Trouve les inefficacités critiques dans le code soumis.
Réponds impérativement avec deux sections claires :
1. ANALYSE DU PROBLÈME : Explique brièvement en français le problème de performance.
2. CODE OPTIMISÉ : Donne le code corrigé et performant.
"""
class UtilisateurCreate(BaseModel):
    email: str

# 5. La "Route" d'API que les clients vont appeler
# main.py (Mise à jour de la route)

@app.post("/optimiser")
async def optimiser_code_api(
    donnees: DemandeOptimisation, 
    db: Session = Depends(get_db),
    utilisateur_actuel: models.Utilisateur = Depends(verifier_authentification) # Sécurité activée !
):
    if not donnees.code.strip():
        raise HTTPException(status_code=400, detail="Le code fourni est vide.")
    
    try:
        # 1. Appel à l'IA Groq / Llama
        reponse = client_ia.chat.completions.create(
            messages=[
                {"role": "system", "content": INSTRUCTIONS_PROMPT},
                {"role": "user", "content": f"Optimise ce code :\n\n{donnees.code}"}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.2,
        )
        
        analyse_texte = reponse.choices[0].message.content

        # 2. Enregistrement dans l'historique de la BDD
        nouvelle_analyse = models.HistoriqueAnalyse(
            code_original=donnees.code,
            analyse_ia=analyse_texte,
            utilisateur_id=utilisateur_actuel.id  
        )
        db.add(nouvelle_analyse)
        
        # 3. Consommation d'une analyse (Compteur)
        utilisateur_actuel.nb_analyses_aujourdhui += 1
        db.commit()
        
        # ✉️ 4. Déclenchement de l'email automatique avec Resend
        # On utilise directement l'adresse email de l'utilisateur connecté de manière sécurisée
        envoyer_code_par_email(
            email_client=utilisateur_actuel.email,
            code_original=donnees.code,
            code_optimise=analyse_texte
        )
        
        # 5. Réponse envoyée au Frontend Vercel
        return {
            "statut": "succes",
            "utilisateur_email": utilisateur_actuel.email,
            "statut_compte": utilisateur_actuel.statut,
            "analyses_restantes": utilisateur_actuel.limite_quotidienne - utilisateur_actuel.nb_analyses_aujourdhui,
            "analyse": analyse_texte
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'analyse : {str(e)}")
# Petite route de test pour vérifier que le serveur tourne
@app.get("/")
def home():
    return {"message": "Le serveur du SaaS FinOps est en ligne ! 🚀"}


class UserCreateRequest(BaseModel):
    email: str

class VerificationRequest(BaseModel):
    email: str
    code: str
@app.post("/auth/demande")
def demander_connexion(request: UserCreateRequest, db: Session = Depends(get_db)):
    utilisateur = db.query(models.Utilisateur).filter(models.Utilisateur.email == request.email).first()
    
    if not utilisateur:
        # Création de l'utilisateur s'il est nouveau
        utilisateur = models.Utilisateur(
            email=request.email,
            statut="gratuit",
            limite_quotidienne=5,
            nb_analyses_aujourdhui=0,
            derniere_analyse_date=date.today()
        )
        db.add(utilisateur)
        db.commit()
        db.refresh(utilisateur)

    # 1. Générer un code à 6 chiffres aléatoires
    code_secret = f"{random.randint(100000, 999995)}"
    
    # 2. Définir une expiration dans 10 minutes
    expiration = datetime.utcnow() + timedelta(minutes=10)
    
    # 3. Sauvegarder dans la BDD
    utilisateur.code_verification = code_secret
    utilisateur.code_expire_a = expiration
    db.commit()

    # ✉️ Fonction pour envoyer le code par email
def envoyer_code_par_email(email_client: str, code_original: str, code_optimise: str):
    try:
        # Construction du contenu du mail en HTML propre
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
                <h2 style="color: #4F46E5;">Voici votre code optimisé par FinOps Optimizer ! 🚀</h2>
                <p>Bonjour,</p>
                <p>Vous trouverez ci-dessous le résultat de l'optimisation de votre script backend.</p>
                
                <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;"/>
                
                <h3>💻 Code Optimisé :</h3>
                <pre style="background-color: #f4f4f5; padding: 15px; border-radius: 8px; border: 1px solid #e4e4e7; overflow-x: auto; font-family: 'Courier New', Courier, monospace;">{code_optimise}</pre>
                
                <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;"/>
                
                <p style="font-size: 0.9em; color: #666;">Merci d'utiliser notre service.<br/>L'équipe SaaS FinOps Optimizer</p>
            </body>
        </html>
        """
        
        # Envoi via l'API Resend
        params = {
            "from": "FinOps Optimizer <onboarding@resend.dev>", 
            "to": [email_client],  # <-- Bien utiliser email_client (l'argument de ta fonction)
            "subject": "🚀 Votre code optimisé est prêt !",
            "html": html_content
        }
        
        resend.Emails.send(params)
        print(f"✅ Email envoyé avec succès à {email_client}")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi de l'email : {str(e)}")
        # On ne bloque pas forcément l'application si l'email échoue, mais on le log
    # 4. ✉️ SIMULATION D'ENVOI D'EMAIL (On l'affiche dans le terminal de l'API)
    print("\n" + "="*40)
    print(f"✉️ EMAIL ENVOYÉ À : {utilisateur.email}")
    print(f"👉 VOTRE CODE DE CONNEXION : {code_secret}")
    print("="*40 + "\n")

    return {"message": "Un code de vérification a été envoyé par email."}

class VerificationRequest(BaseModel):
    email: str
    code: str

@app.post("/auth/verifier")
def verifier_code(request: VerificationRequest, db: Session = Depends(get_db)):
    utilisateur = db.query(models.Utilisateur).filter(models.Utilisateur.email == request.email).first()
    
    if not utilisateur or utilisateur.code_verification != request.code:
        raise HTTPException(status_code=401, detail="Code de vérification incorrect.")
        
    # Vérifier si le code a expiré
    if datetime.utcnow() > utilisateur.code_expire_a:
        raise HTTPException(status_code=401, detail="Le code a expiré (valable 10 min).")
    
    # Si l'utilisateur n'avait pas encore de clé API, on lui en génère une maintenant
    if not utilisateur.api_key:
        import uuid
        utilisateur.api_key = f"sk_live_{uuid.uuid4().hex}"
    
    # Consommer le code (on le vide pour la sécurité)
    utilisateur.code_verification = None
    utilisateur.code_expire_a = None
    db.commit()
    
    return {
        "api_key": utilisateur.api_key,
        "statut": utilisateur.statut,
        "nb_analyses_aujourdhui": utilisateur.nb_analyses_aujourdhui,
        "limite_quotidienne": utilisateur.limite_quotidienne
    }
load_dotenv()
# Configure ta clé secrète Stripe Test
stripe.api_key = STRIPE_SECRET_KEY

class CheckoutRequest(BaseModel):
    email: str

@app.post("/stripe/create-checkout-session")
def create_checkout_session(request: CheckoutRequest, db: Session = Depends(get_db)):
    try:
        # On vérifie que l'utilisateur existe bien
        utilisateur = db.query(models.Utilisateur).filter(models.Utilisateur.email == request.email).first()
        if not utilisateur:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

        # Création de la session de paiement Stripe
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            customer_email=request.email, # Stripe pré-remplira l'email du client
            line_items=[
                {
                    # Remplace par l'ID du prix créé sur ton tableau de bord Stripe
                    'price': 'price_1TotZ1116HPWJVK01dR3NX5Q', 
                    'quantity': 1,
                },
            ],
            mode='subscription', # Mode abonnement mensuel
            # Où rediriger l'utilisateur après le paiement (on le renvoie sur ton Dashboard)
            success_url='https://dashboard.stripe.com',
            cancel_url='https://dashboard.stripe.com',
        )
        
        # On renvoie l'URL de paiement Stripe à notre Frontend
        return {"url": checkout_session.url}
        
    except Exception as e:
        print("❌ ERREUR STRIPE DETECTÉE :", str(e))
        raise HTTPException(status_code=500, detail=str(e))
    
# Colle ici le secret fourni par la commande 'stripe listen'
STRIPE_WEBHOOK_SECRET = "whsec_5944f6609688b0bec53eb72da56cea5c50fb5492b1d3c3964bdb17b27a662853"

@app.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        # 1. Vérification de la sécurité de la requête (est-ce que ça vient bien de Stripe ?)
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Payload invalide
        raise HTTPException(status_code=400, detail="Payload invalide")
    except stripe.error.SignatureVerificationError as e:
        # Signature invalide
        raise HTTPException(status_code=400, detail="Signature invalide")

    # 2. Traitement de l'événement de paiement réussi
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        
        # ✅ Extraction sécurisée compatible avec les objets Stripe
        customer_email = session.customer_email or (session.customer_details.email if session.customer_details else None)
        
        if customer_email:
            print(f"💰 Paiement Premium validé pour : {customer_email}")
            
            # Recherche de l'utilisateur en base de données
            utilisateur = db.query(models.Utilisateur).filter(models.Utilisateur.email == customer_email).first()
            if utilisateur:
                # 🚀 PASSAGE EN PREMIUM !
                utilisateur.statut = "premium"
                utilisateur.limite_quotidienne = 999999
                db.commit()
                print(f"✨ L'utilisateur {customer_email} est désormais PREMIUM en BDD !")
            else:
                print(f"⚠️ Aucun utilisateur trouvé en BDD pour l'email {customer_email}")

if __name__ == "__main__":
    import uvicorn
    # Récupère le port attribué par Render, ou utilise 8000 par défaut en local
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
