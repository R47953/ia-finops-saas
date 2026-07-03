# models.py
from datetime import date, datetime  # Ajout de datetime pour les analyses
import uuid
# Ajout de Text et DateTime dans l'import SQLAlchemy
from sqlalchemy import Column, Integer, String, ForeignKey, Date, Text, DateTime 
from sqlalchemy.orm import relationship
from database import Base

class Utilisateur(Base):
    __tablename__ = "utilisateurs"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    api_key = Column(String, unique=True, default=lambda: f"sk_live_{uuid.uuid4().hex}")
    statut = Column(String, default="gratuit")  # "gratuit" ou "premium"
    
    # --- NOUVEAUX CHAMPS POUR LE PAYWALL ---
    limite_quotidienne = Column(Integer, default=5)  # 5 requêtes max par jour pour les gratuits
    nb_analyses_aujourdhui = Column(Integer, default=0)
    derniere_analyse_date = Column(Date, default=date.today)
    code_verification = Column(String, nullable=True)  # Stocke le code temporaire (ex: "582910")
    code_expire_a = Column(DateTime, nullable=True)     # Date/heure d'expiration du code
    analyses = relationship("HistoriqueAnalyse", back_populates="proprietaire")


class HistoriqueAnalyse(Base):
    __tablename__ = "historique_analyses"

    id = Column(Integer, primary_key=True, index=True)
    code_original = Column(Text, nullable=False)
    analyse_ia = Column(Text, nullable=False)
    # datetime.utcnow récupère l'heure précise de l'analyse
    date_analyse = Column(DateTime, default=datetime.utcnow)
    
    # Clé étrangère pour lier l'analyse à un utilisateur spécifique
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"))

    proprietaire = relationship("Utilisateur", back_populates="analyses")