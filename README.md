# Reporte de Disponibilidad y Tráfico LibreNMS

Este script genera reportes de disponibilidad y tráfico de red de dispositivos monitoreados en LibreNMS, calculando las horas online y offline de cada dispositivo en un período específico, incluyendo la fecha en que cada dispositivo fue agregado al monitoreo.

## Requisitos

- Python 3.8 o superior
- LibreNMS instalado y configurado
- Token de API de LibreNMS
- Las siguientes bibliotecas de Python:
  - pandas >= 1.5.0
  - requests >= 2.28.0
  - datetime >= 3.8.0
  - logging >= 0.5.1.2
  - os (incluido en la biblioteca estándar de Python)

## Instalación de Dependencias

Puedes instalar las dependencias necesarias usando pip:

```bash
pip install pandas>=1.5.0 requests>=2.28.0
```

## Configuración

1. Asegúrate de tener las variables de entorno configuradas o modifica las siguientes constantes en el código:
   ```python
   API_TOKEN = os.getenv('LIBRENMS_TOKEN', 'tu_token_aqui')
   BASE_URL = os.getenv('LIBRENMS_URL', 'https://tu-servidor-librenms/api/v0')
   ```

## Funcionalidades

### 1. Obtención de Dispositivos
- Obtiene la lista de todos los dispositivos monitoreados en LibreNMS
- Extrae información básica: hostname, ID, dirección IP y fecha de agregado al monitoreo

### 2. Cálculo de Disponibilidad
- Calcula las horas online y offline de cada dispositivo
- Considera el tiempo real que el dispositivo ha estado en el sistema
- Calcula el porcentaje de disponibilidad como: (horas_online / tiempo_total) * 100

### 3. Monitoreo de Tráfico de Red
- Obtiene datos de tráfico para los puertos de red
- Calcula estadísticas de tráfico para cada puerto:
  - Bytes entrantes (in)
  - Bytes salientes (out)
  - Tráfico total
  - Máximo tráfico entrante
  - Máximo tráfico saliente
  - Promedio de tráfico entrante
  - Promedio de tráfico saliente

### 4. Generación de Reportes
- Crea reportes en formato Excel
- Incluye las siguientes columnas:
  - Equipo (hostname)
  - Sysname (nombre del AP)
  - IP
  - Fecha de agregado al monitoreo
  - Horas online
  - Horas offline
  - Tiempo total
  - Porcentaje de disponibilidad
  - Fecha de inicio del período
  - Fecha de fin del período
  - Estadísticas de tráfico de red

## Uso

1. Ejecuta el script:
   ```bash
   python librenms_report.py
   ```

2. El script te pedirá:
   - Fecha de inicio (formato: YYYY-MM-DD)
   - Fecha de fin (formato: YYYY-MM-DD)

3. El reporte se generará en la carpeta `reportes` con el nombre:
   ```
   disponibilidad_YYYYMMDD_YYYYMMDD.xlsx
   ```

## Estructura del Reporte

### Columnas del Excel
- **Equipo**: Nombre del dispositivo
- **Sysname**: Nombre del punto de acceso (AP)
- **IP**: Dirección IP del dispositivo
- **Fecha de agregado**: Fecha y hora en que el dispositivo fue agregado al monitoreo
- **Horas online**: Tiempo que el dispositivo estuvo disponible
- **Horas offline**: Tiempo que el dispositivo estuvo no disponible
- **Tiempo total**: Suma de horas online y offline
- **Disponibilidad**: Porcentaje de tiempo que el dispositivo estuvo disponible
- **Fecha inicio**: Inicio del período de monitoreo
- **Fecha fin**: Fin del período de monitoreo


