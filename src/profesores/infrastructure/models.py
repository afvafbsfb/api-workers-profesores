from sqlalchemy import Column, Integer, String, Date, ForeignKey, DateTime, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.shared.database import Base
from src.academias.infrastructure.models import Curso, Aula
from src.usuarios.infrastructure.models import Usuario

# Nota: el esquema SQL (`create_database.sql`) no define una tabla `Profesor`.
# En la base de datos un "profesor" es simplemente un `Usuario` con el rol
# 'Profesor_academia' (o puede ser también 'Admin_academia' que actúa como
# administrador de la academia). Por esa razón no mantenemos una tabla
# separada `Profesor` mapeada por SQLAlchemy para evitar inconsistencias.

class CursoProfesores(Base):
    __tablename__ = 'Curso_Profesores'
    id = Column(Integer, primary_key=True, autoincrement=True)
    curso_id = Column(Integer, ForeignKey('Curso.id'), nullable=False)
    usuario_id = Column(Integer, ForeignKey('Usuario.id'), nullable=False)
    fecha_alta = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    fecha_baja = Column(DateTime, nullable=True)
    fecha_ult_modificacion = Column(DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    motivo_baja = Column(String(255), nullable=True)

    usuario = relationship('Usuario')
    # Relación inversa: las sesiones asociadas a este mapeo curso<->usuario
    sesiones = relationship('Sesion', back_populates='curso_profesor')

class Sesion(Base):
    __tablename__ = 'Sesion'
    id = Column(Integer, primary_key=True, autoincrement=True)
    horario_curso_id = Column(Integer, ForeignKey('HorarioCurso.id'), nullable=False)
    aula_id = Column(Integer, ForeignKey('Aula.id'), nullable=False)
    curso_profesor_id = Column(Integer, ForeignKey('Curso_Profesores.id'), nullable=False)
    timestamp_alta = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    hora_inicio = Column(Time, nullable=False)
    hora_fin = Column(Time, nullable=False)
    timestamp_baja = Column(DateTime, nullable=True)
    motivo_baja = Column(String(255), nullable=True)
    notas_sesion = Column(String, nullable=True)
    notas_materia = Column(String, nullable=True)

    horario_curso = relationship('HorarioCurso', back_populates='sesiones')
    curso_profesor = relationship('CursoProfesores', back_populates='sesiones')
    aula = relationship('Aula', back_populates='sesiones')

# No asignamos Curso.sesiones directamente porque las sesiones están ligadas a Curso_Profesores
Aula.sesiones = relationship('Sesion', back_populates='aula')