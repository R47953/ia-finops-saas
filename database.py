# database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# L'emplacement de notre fichier de base de données SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///./saas_finops.db"

# L'engine est le moteur qui fait tourner le SQL en tâche de fond
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Chaque fois qu'on interagit avec la BDD, on ouvre une Session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# La classe de base dont hériteront tous nos modèles (tables)
Base = declarative_base()

# Fonction pratique pour ouvrir/fermer la BDD à chaque requête API
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()