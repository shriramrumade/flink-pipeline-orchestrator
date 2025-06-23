from sqlalchemy import create_engine, Column, Integer, String, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://flink:flink@postgres:5432/metadata"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Pipeline(Base):
    __tablename__ = "pipelines"
    id = Column(Integer, primary_key=True, index=True)
    pipeline_id = Column(String, unique=True, nullable=False)
    source_type = Column(String)
    source_path = Column(Text)
    source_format = Column(String)
    sink_type = Column(String)
    sink_index = Column(String)
    transformations = Column(JSON)
    schedule = Column(String)
