from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from src.shared.database import Base

class Alumno(Base):
    __tablename__ = 'Alumno'
    id = Column(Integer, primary_key=True, autoincrement=True)
    academia_id = Column(Integer, ForeignKey('Academia.id'), nullable=False)
    nombre = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    dni = Column(String(20), nullable=False)
    telefono = Column(String(20), nullable=False)
    fecha_nacimiento = Column(Date, nullable=False)
    direccion = Column(String(255), nullable=False)
    nombre_tutor = Column(String(100), nullable=True)
    relaccion_tutor_alumno = Column(String(100), nullable=True)
    telefono_tutor = Column(String(20), nullable=True)
    email_tutor = Column(String(120), nullable=True)

    inscripciones = relationship('Inscripcion', back_populates='alumno')

class Inscripcion(Base):
    __tablename__ = 'Inscripcion'
    id = Column(Integer, primary_key=True, autoincrement=True)
    alumno_id = Column(Integer, ForeignKey('Alumno.id'), nullable=False)
    curso_id = Column(Integer, ForeignKey('Curso.id'), nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=True)
    motivo_baja = Column(String(255), nullable=True)

    alumno = relationship('Alumno', back_populates='inscripciones')