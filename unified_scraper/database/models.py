from sqlalchemy import Column, Integer, String, Date, Text, Boolean, ForeignKey, TIMESTAMP, UniqueConstraint
from sqlalchemy.orm import relationship
from Database.high_court_database import Base
from sqlalchemy.sql import func
from sqlalchemy import JSON 

class HighCourt(Base):
    __tablename__ = "HighCourts"

    id = Column(Integer, primary_key=True, index=True)
    highcourt_name = Column(String(100), nullable=False)
    base_link = Column(Text)
    bench = Column(String(255), nullable=True)       
    pdf_folder = Column(String(255), nullable=True)

    judgments = relationship("MetaData", back_populates="highcourt")


class MetaData(Base):
    __tablename__ = "MetaData"

    id = Column(Integer, primary_key=True, index=True)
    high_court_id = Column(Integer, ForeignKey("HighCourts.id", ondelete="CASCADE"), nullable=False)
    case_id = Column(String(255), nullable=False)
    judgement_date = Column(Date)
    party_detail = Column(Text)
    document_link = Column(JSON, nullable=True)
    is_downloaded = Column(Boolean, default=False)
    scrapped_at = Column(TIMESTAMP, server_default=func.now())

    highcourt = relationship("HighCourt", back_populates="judgments")

 
