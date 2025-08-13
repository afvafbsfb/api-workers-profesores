# Infraestructura en AWS

## Elastic Beanstalk
- Entorno creado: `Servicio-api-workers-env`
- URL del entorno: `servicio-api-workers-env.eba-m5yrjv7b.eu-west-3.elasticbeanstalk.com`

## API Gateway
- Nombre: `Workers API (proxy only)`
- Ruta única: `/{proxy+}` con método `ANY`
- Integración HTTP con el entorno EB:
  - URI: `http://servicio-api-workers-env.eba-m5yrjv7b.eu-west-3.elasticbeanstalk.com/{proxy}`
  - ID de integración: `kxs6esd`

## Base de datos
- Aurora y RDS: instancia/cluster `api-workers-prod`
