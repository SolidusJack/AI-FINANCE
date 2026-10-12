from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Transaction
from settings import Settings  

engine = create_engine(Settings.URL_DATABASE)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)
