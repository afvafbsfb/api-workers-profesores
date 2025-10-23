from sqlalchemy import Column, Integer, String, ForeignKey, Date, Enum, Boolean, Float, DateTime, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.shared.database import Base

class Academia(Base):
    __tablename__ = 'Academia'
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), unique=True, nullable=False)
    fecha_alta = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    fecha_baja = Column(DateTime, nullable=True)
    fecha_ultima_modificacion = Column(DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    # Not enforcing a SQLAlchemy ForeignKey here to avoid circular create-order issues.
    # We keep the column to record the user id who last modified the academia.
    usuario_id_ultima_modificacion = Column(Integer, nullable=True)
    cursos = relationship('Curso', back_populates='academia')
    aulas = relationship('Aula', back_populates='academia')
    tarifas = relationship('Tarifa', back_populates='academia')

class Aula(Base):
    __tablename__ = 'Aula'
    id = Column(Integer, primary_key=True, autoincrement=True)
    academia_id = Column(Integer, ForeignKey('Academia.id'), nullable=False)
    nombre = Column(String(100), nullable=False)
    capacidad_maxima = Column(Integer, nullable=False)

    academia = relationship('Academia', back_populates='aulas')

class Curso(Base):
    __tablename__ = 'Curso'
    id = Column(Integer, primary_key=True, autoincrement=True)
    academia_id = Column(Integer, ForeignKey('Academia.id'), nullable=False)
    nombre = Column(String(100), nullable=False)
    anio_academico = Column(String(20), nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    acepta_nuevos_alumnos = Column(Boolean, nullable=False)
    capacidad_maxima = Column(Integer, nullable=False)
    # Relación con Tarifa: obligatoria según create_database.sql
    tarifa_id = Column(Integer, ForeignKey('Tarifa.id'), nullable=False)
    tipo_alumno = Column(Enum('Infantil', 'Juvenil', 'Adultos'), nullable=False)
    estado = Column(Enum('Activo', 'Inactivo', 'Finalizado'), nullable=False)
    academia = relationship('Academia', back_populates='cursos')
    tarifa = relationship('Tarifa', back_populates='cursos')

class HorarioCurso(Base):
    __tablename__ = 'HorarioCurso'
    id = Column(Integer, primary_key=True, autoincrement=True)
    curso_id = Column(Integer, ForeignKey('Curso.id'), nullable=False)
    aula_id = Column(Integer, ForeignKey('Aula.id'), nullable=False)
    dia_semana = Column(String(20), nullable=False)
    hora_inicio = Column(Time, nullable=False)
    hora_fin = Column(Time, nullable=False)
    
    # Relationships
    sesiones = relationship('Sesion', back_populates='horario_curso')

class Tarifa(Base):
    __tablename__ = 'Tarifa'
    id = Column(Integer, primary_key=True, autoincrement=True)
    academia_id = Column(Integer, ForeignKey('Academia.id'), nullable=False)
    descripcion = Column(String(255))
    precio_base = Column(Float, nullable=False)
    fecha_alta = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    fecha_baja = Column(DateTime, nullable=True)
    fecha_ultima_modificacion = Column(DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    academia = relationship('Academia', back_populates='tarifas')
    cursos = relationship('Curso', back_populates='tarifa')