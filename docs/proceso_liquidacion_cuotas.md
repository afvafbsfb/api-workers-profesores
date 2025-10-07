# Proceso de Liquidación de Cuotas

## Descripción General
El proceso de liquidación de cuotas se ejecuta entre los días 1 y 5 de cada mes. Su objetivo es generar extractos mensuales para las inscripciones abiertas y gestionar los movimientos asociados a dichas cuotas.

## Tablas Involucradas
1. **Extractos**:
   - Registra las cuotas mensuales generadas para cada inscripción.
   - Campos clave:
     - `id_extracto`, `inscripcion_id`, `curso_id`, `alumno_id`, `numero_extracto`, `estado_liquidacion_extracto`.
     - `saldo_ingreso_cuenta_anterior`: Refleja el resultado global del cliente hasta el momento de la liquidación actual. Si no hay liquidación anterior, el valor es `0`. Si hay saldo a favor, es positivo; si hay deuda, es negativo.

2. **Movimientos_Extracto**:
   - Registra los movimientos relacionados con los extractos, como pagos o anulaciones.
   - Campos clave:
     - `id`, `inscripcion_id`, `curso_id`, `alumno_id`, `numero_extracto`, `tipo_movimiento`, `fecha_movimiento`, `importe`, `estado_liquidacion_movimiento`, `metodo_pago`.
     - `indicador_movimiento_anulado`: Indica si un movimiento ha sido anulado (`S` para Sí, `N` para No). Los movimientos liquidados no se pueden anular directamente; en su lugar, se crea un nuevo movimiento de tipo "anulación de ingreso".

## Flujo del Proceso
1. **Gestión de Movimientos**:
   - Siempre que se produce un ingreso es necesario saber qué alumno lo hace y sobre qué curso lo hace.
   - Si un alumno quiere realizar un pago, se verifica si tiene cuotas pendientes de pago. Si no tiene cuotas pendientes, se abona el importe de la cuota correspondiente. Si tiene deudas, se informa del importe total de la deuda y de la última cuota.
   - Si no hay extracto abierto, se crea uno nuevo y se añade el movimiento. La fecha del extracto será la del día y solo se rellenan los campos de PK, FK y el estado del extracto como "pendiente".

2. **Generación de Extractos**:
   - Si no existe un extracto pendiente del mes anterior, se abre un extracto nuevo del mes anterior y se liquida.

3. **Liquidación de Extractos**:
   - Es un proceso mensual que se realiza entre el día 1 y el 5 de mes y siempre se liquida el periodo del mes anterior.
   - Se calcula el período a liquidar (primer y último día del mes anterior).
   - Se recorren todas las inscripciones abiertas/activas.
   - Por cada inscripción abierta se comprueba lo siguiente:
     1. Si ya tiene un extracto pendiente de liquidar:
        - Se comprueba la fecha de alta del extracto. Si es del mes anterior, se liquida; de lo contrario, se salta para liquidarlo el mes siguiente.

        MUY IMPORTANTE: 
     2. Si no tiene un extracto pendiente de liquidar:
        - Se crea un nuevo extracto y se liquida y el extracto queda marcado como liquidado. Si el importe del cargo del extracto liqudado es mayor a 0, se abre un nuevo extracto en situación de pendiente con el campo `saldo_ingreso_cuenta_anterior` negativo por el importe del cargo del extracto liquidado. Si el importe es menor a 0, se abre con saldo positivo. Si el importe es 0, no se abre un nuevo extracto pendiente.

   - El importe resultante de la liquidación incluye:
     - `importe_cuota_mensual_sin_descuentos`: Lo que le corresponde pagar al cliente sin descuentos.
     - `importe_cuota_mensual_con_descuentos`: Lo que le corresponde pagar al cliente con descuentos aplicados.
     - `importe_exceso_ingresos`: Indica si el cliente ha pagado de más, quedando saldo a favor para cuotas futuras.
     - `total_importe_a_cobrar`: Indica el total a pagar, que incluye la nueva cuota calculada, la deuda anterior y los ingresos del mes.
   - Se marcan como liquidados tanto el extracto como todos los movimientos asociados.

   - Si el resultado de la liquidación no es cero, se abre un nuevo extracto pendiente.
   - El extracto liquidado siempre se marca como liquidado.

## Liquidación Anticipada en Caso de Finalización del Curso

Si un curso finaliza en una fecha distinta al último día del mes, se debe realizar una **liquidación anticipada** de cuotas. Esta liquidación será la última liquidación mensual para ese curso. A continuación, se detallan las reglas específicas:

1. **Fecha de Liquidación**:
   - La liquidación anticipada se realiza el día siguiente a la fecha de finalización del curso.
   - El período a liquidar será desde el primer día del mes hasta la fecha de finalización del curso.

2. **Generación de Nuevos Extractos**:
   - Después de la liquidación anticipada:
     - Si el alumno tiene deudas pendientes, se generará un nuevo extracto pendiente con el saldo correspondiente.
     - Si el alumno no tiene deudas y ha pagado todo, no se generarán nuevos extractos, ya que no hay nuevas cuotas.

3. **Movimientos Posteriores a la Finalización del Curso**:
   - A partir de la fecha de finalización del curso, cualquier movimiento de ingreso realizado por un alumno debe ser evaluado:
     - Si el ingreso cubre el total de la deuda pendiente, se debe realizar una liquidación inmediata de ese extracto.
     - Esto asegura que los extractos se vayan cerrando progresivamente y no queden pendientes innecesariamente.

4. **Cierre de Extractos**:
   - Una vez que todos los extractos pendientes han sido liquidados y no hay nuevas cuotas, no se generarán más extractos para ese curso.

Esta regla garantiza que los cursos que finalizan en fechas intermedias del mes sean gestionados correctamente, evitando retrasos en las liquidaciones y asegurando que los extractos pendientes se cierren de manera oportuna.

## Restricción Importante

Un alumno no puede tener dos extractos en estado pendiente para la misma inscripción. Esto se debe a las siguientes razones:

1. **Consolidación de Deudas**:
   - La deuda pendiente siempre se arrastra y se consolida en el último extracto pendiente. Esto asegura que toda la información financiera del cliente esté centralizada en un único registro.

2. **Flujo de Generación de Extractos**:
   - Si existe un extracto pendiente, cualquier nuevo movimiento (ingreso o anulación) se asocia al extracto existente.
   - Solo se crea un nuevo extracto pendiente si el extracto anterior ha sido liquidado y el resultado de la liquidación no es cero.

3. **Evitar Inconsistencias**:
   - Permitir múltiples extractos pendientes para la misma inscripción podría generar inconsistencias en el cálculo de deudas y saldos, complicando la gestión financiera.

Esta restricción está diseñada para garantizar la integridad de los datos y simplificar el proceso de liquidación y gestión de movimientos.

## Estados
- **Estado de Liquidación del Extracto**:
  - `1`: Pendiente de liquidación.
  - `2`: Liquidado.

- **Situación del Movimiento**:
  - `1`: Pendiente de liquidar.
  - `2`: Liquidado.

## Consultas SQL
### Generar Extractos
```sql
INSERT INTO Extractos (inscripcion_id, curso_id, alumno_id, numero_extracto, estado_liquidacion_extracto, fecha_ini_periodo, fecha_fin_periodo, importe_cuota, total_descuentos, importe_cobrar)
VALUES (?, ?, ?, ?, '1', ?, ?, ?, ?, ?);
```

### Asociar Movimiento a Extracto
```sql
INSERT INTO Movimientos_Extracto (inscripcion_id, curso_id, alumno_id, numero_extracto, tipo_movimiento, fecha_movimiento, importe, estado_liquidacion_movimiento, metodo_pago, indicador_movimiento_anulado)
VALUES (?, ?, ?, ?, ?, ?, ?, '1', ?, 'N');
```

### Liquidar Extracto
```sql
UPDATE Extractos
SET estado_liquidacion_extracto = '2'
WHERE id_extracto = ?;

UPDATE Movimientos_Extracto
SET estado_liquidacion_movimiento = '2'
WHERE numero_extracto = ?;
```