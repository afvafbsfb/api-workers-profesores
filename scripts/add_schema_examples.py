"""
Script para agregar ejemplos a los schemas en openapi-auto.json
Ejecutar después de dump_openapi.py
"""
import json
import sys

def add_examples_to_spec(spec_path):
    """Agrega ejemplos a los schemas que no los tienen."""
    
    with open(spec_path, 'r', encoding='utf-8') as f:
        spec = json.load(f)
    
    schemas = spec.get('components', {}).get('schemas', {})
    
    # Ejemplos para Academia
    if 'CreateAcademia' in schemas or 'Academia' in schemas:
        # Intentar ambos nombres
        for schema_name in ['CreateAcademia', 'Academia']:
            if schema_name in schemas:
                schema = schemas[schema_name]
                if 'properties' not in schema:
                    schema['properties'] = {}
                
                # Agregar example al schema completo
                if 'example' not in schema:
                    schema['example'] = {
                        'nombre': 'Academia de Idiomas Central',
                        'direccion': 'Calle Mayor 123, Madrid',
                        'telefono': '+34 912 345 678'
                    }
                
                print(f"✓ Agregado ejemplo a {schema_name}")
    
    # Ejemplos para TarifaCreate
    if 'TarifaCreate' in schemas:
        schema = schemas['TarifaCreate']
        if 'example' not in schema:
            schema['example'] = {
                'academia_id': 1,
                'descripcion': 'Tarifa mensual básica',
                'precio_base': 50.0
            }
        print("✓ Agregado ejemplo a TarifaCreate")
    
    # Ejemplos para TarifaUpdate
    if 'TarifaUpdate' in schemas:
        schema = schemas['TarifaUpdate']
        if 'example' not in schema:
            schema['example'] = {
                'descripcion': 'Tarifa mensual básica MODIFICADA',
                'precio_base': 55.0
            }
        print("✓ Agregado ejemplo a TarifaUpdate")
    
    # Ejemplos para Tarifa (respuesta completa)
    if 'Tarifa' in schemas:
        schema = schemas['Tarifa']
        if 'example' not in schema:
            schema['example'] = {
                'id': 1,
                'academia_id': 1,
                'descripcion': 'Tarifa mensual básica',
                'precio_base': 50.0,
                'fecha_alta': '2025-10-27T10:30:00',
                'fecha_baja': None,
                'fecha_ultima_modificacion': '2025-10-27T10:30:00'
            }
        print("✓ Agregado ejemplo a Tarifa")
    
    # Guardar cambios
    with open(spec_path, 'w', encoding='utf-8') as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Ejemplos agregados a {spec_path}")


if __name__ == '__main__':
    spec_path = sys.argv[1] if len(sys.argv) > 1 else 'docs/openapi-auto.json'
    add_examples_to_spec(spec_path)
