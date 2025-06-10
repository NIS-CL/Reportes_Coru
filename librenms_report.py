import pandas as pd
from datetime import datetime, timedelta
import logging
import os
import requests
from dateutil.relativedelta import relativedelta
import argparse
import sys
import json

# Configuración
API_TOKEN = os.getenv('LIBRENMS_TOKEN', 'd461ef4ed7c4dae512e54825e6e42681')
BASE_URL = os.getenv('LIBRENMS_URL', 'https://monitorcoru.netlayer.cl/api/v0')
HEADERS = {
    'X-Auth-Token': API_TOKEN,
    'Accept': 'application/json'
}

# Configuración de log para errores
logging.basicConfig(
    filename='errores_librenms.log',
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_devices():
    """Obtiene la lista de dispositivos desde LibreNMS"""
    try:
        url = f"{BASE_URL}/devices"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        devices = data['devices']
        
        # Obtener los dispositivos con su información
        dispositivos = []
        for dev in devices:
            # Obtener el sysname y limpiarlo
            sysname = dev.get('sysname', '')
            if isinstance(sysname, str):
                # Eliminar el prefijo 'sysName:' si existe
                sysname = sysname.replace('sysName:', '').strip()
                # Si está vacío después de limpiar, intentar obtener el nombre del dispositivo
                if not sysname:
                    # Intentar obtener el nombre del dispositivo de diferentes campos
                    sysname = dev.get('display', '') or dev.get('description', '') or dev.get('hostname', 'N/A')
                    # Si aún está vacío, usar el hostname
                    if not sysname:
                        sysname = dev.get('hostname', 'N/A')
            else:
                sysname = dev.get('hostname', 'N/A')
            
            dispositivos.append((
                dev['hostname'],
                dev['device_id'],
                dev.get('ip', 'N/A'),
                dev.get('inserted', 'N/A'),
                sysname
            ))
        
        return dispositivos
    except Exception as e:
        logging.error(f"Error al obtener dispositivos: {str(e)}")
        return []

def get_device_availability(device_id, start_date, end_date):
    """Obtiene la disponibilidad de un dispositivo para un período específico"""
    try:
        url = f"{BASE_URL}/devices/{device_id}/availability"
        params = {
            'from': start_date.strftime('%Y-%m-%d'),
            'to': end_date.strftime('%Y-%m-%d')
        }
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get('availability', [])
    except Exception as e:
        logging.error(f"Error al obtener disponibilidad para dispositivo {device_id}: {str(e)}")
        return []

def calcular_disponibilidad_total(availability_data, start_date, end_date):
    """Calcula la disponibilidad total para todo el período"""
    if not availability_data:
        return {
            'porcentaje_total': 0,
            'horas_online_total': 0,
            'horas_offline_total': 0,
            'tiempo_total': 0
        }

    # Calcular el número total de horas en el período
    dias_totales = (end_date - start_date).days + 1
    horas_totales = dias_totales * 24

    # Acumular los porcentajes de disponibilidad
    suma_disponibilidad = 0
    muestras = 0

    for entry in availability_data:
        try:
            disponibilidad = float(entry.get('availability_perc', 0))
            suma_disponibilidad += disponibilidad
            muestras += 1
        except (ValueError, KeyError) as e:
            logging.warning(f"Error al procesar entrada de disponibilidad: {e}")
            continue

    # Calcular el promedio de disponibilidad
    if muestras > 0:
        porcentaje_total = suma_disponibilidad / muestras
    else:
        porcentaje_total = 0

    # Calcular horas totales online y offline
    horas_online_total = (porcentaje_total / 100) * horas_totales
    horas_offline_total = horas_totales - horas_online_total

    return {
        'porcentaje_total': round(porcentaje_total, 2),
        'horas_online_total': round(horas_online_total, 2),
        'horas_offline_total': round(horas_offline_total, 2),
        'tiempo_total': horas_totales
    }

def calcular_disponibilidad_por_dia(availability_data, start_date, end_date):
    """Calcula la disponibilidad por día basada en el porcentaje de disponibilidad"""
    # Crear un diccionario para almacenar los datos por día
    disponibilidad_por_dia = {}
    
    # Inicializar todos los días en el rango con valores en cero
    current_date = start_date
    while current_date <= end_date:
        disponibilidad_por_dia[current_date.strftime('%Y-%m-%d')] = {
            'horas_online': 0,
            'horas_offline': 0,
            'tiempo_total': 24,  # Asumimos 24 horas por día
            'porcentaje_disponibilidad': 0,
            'muestras': 0
        }
        current_date += timedelta(days=1)

    # Si no hay datos de disponibilidad, todos los días estarán offline
    if not availability_data:
        print("No se encontraron datos de disponibilidad")
        return disponibilidad_por_dia

    print("\nProcesando datos de disponibilidad:")
    # Procesar cada entrada de disponibilidad
    for entry in availability_data:
        try:
            # Obtener timestamp y convertir a fecha
            timestamp = int(entry.get('timestamp', 0))
            fecha = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
            
            # Obtener porcentaje de disponibilidad
            disponibilidad = float(entry.get('availability_perc', 0))
            
            # Actualizar los datos para ese día
            if fecha in disponibilidad_por_dia:
                # Acumular el porcentaje de disponibilidad
                disponibilidad_por_dia[fecha]['porcentaje_disponibilidad'] += disponibilidad
                disponibilidad_por_dia[fecha]['muestras'] += 1
                
                # Calcular horas online y offline basado en el porcentaje
                horas_online = (disponibilidad / 100) * 24  # 24 horas por día
                horas_offline = 24 - horas_online
                
                disponibilidad_por_dia[fecha]['horas_online'] = horas_online
                disponibilidad_por_dia[fecha]['horas_offline'] = horas_offline
                
                # Imprimir información de depuración para cada día
                print(f"\nCálculo para {fecha}:")
                print(f"Timestamp: {timestamp}")
                print(f"Disponibilidad: {disponibilidad}%")
                print(f"Horas online: {horas_online:.2f}")
                print(f"Horas offline: {horas_offline:.2f}")

        except (ValueError, KeyError) as e:
            logging.warning(f"Error al procesar entrada de disponibilidad: {e}")
            print(f"Error procesando entrada: {e}")
            print(f"Datos de la entrada: {entry}")
            continue

    # Calcular promedios finales para cada día
    for fecha in disponibilidad_por_dia:
        if disponibilidad_por_dia[fecha]['muestras'] > 0:
            # Calcular el promedio de disponibilidad
            disponibilidad_promedio = disponibilidad_por_dia[fecha]['porcentaje_disponibilidad'] / disponibilidad_por_dia[fecha]['muestras']
            
            # Recalcular horas basadas en el promedio
            horas_online = (disponibilidad_promedio / 100) * 24
            horas_offline = 24 - horas_online
            
            disponibilidad_por_dia[fecha]['horas_online'] = round(horas_online, 2)
            disponibilidad_por_dia[fecha]['horas_offline'] = round(horas_offline, 2)
            disponibilidad_por_dia[fecha]['porcentaje_disponibilidad'] = round(disponibilidad_promedio, 2)

    return disponibilidad_por_dia

def construir_reporte(start_date, end_date):
    """Construye el reporte de disponibilidad detallado por día"""
    equipos = get_devices()
    registros = []
    disponibilidad_total = {}

    for hostname, device_id, ip, fecha_agregado, sysname in equipos:
        availability = get_device_availability(device_id, start_date, end_date)
        
        # Calcular disponibilidad total
        stats_total = calcular_disponibilidad_total(availability, start_date, end_date)
        disponibilidad_total[hostname] = stats_total
        
        # Calcular disponibilidad por día
        disponibilidad_por_dia = calcular_disponibilidad_por_dia(availability, start_date, end_date)
        
        # Crear un registro por cada día
        for fecha, stats in disponibilidad_por_dia.items():
            registros.append({
                'equipo': hostname,
                'sysname': sysname,
                'ip': ip,
                'fecha_incorporacion': fecha_agregado,
                'fecha': fecha,
                'horas_online': stats['horas_online'],
                'horas_offline': stats['horas_offline'],
                'tiempo_total': stats['tiempo_total'],
                'porcentaje_disponibilidad': stats['porcentaje_disponibilidad']
            })

    # Convertir a DataFrame
    df = pd.DataFrame(registros)
    if df.empty:
        print("❌ No se encontraron datos válidos para procesar.")
        return pd.DataFrame(), disponibilidad_total
    
    # Ordenar por equipo y fecha
    df = df.sort_values(['equipo', 'fecha'])
    return df, disponibilidad_total

def generar_reporte(start_date, end_date):
    """Genera y guarda el reporte de disponibilidad total"""
    df_final, disponibilidad_total = construir_reporte(start_date, end_date)
    if not df_final.empty:
        # Crear directorio de reportes si no existe
        os.makedirs('reportes', exist_ok=True)
        
        # Generar nombre del archivo
        filename = f"reportes/disponibilidad_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"
        
        # Crear un DataFrame para la disponibilidad total
        df_total = pd.DataFrame([
            {
                'equipo': equipo,
                'sysname': df_final[df_final['equipo'] == equipo]['sysname'].iloc[0],
                'ip': df_final[df_final['equipo'] == equipo]['ip'].iloc[0],
                'fecha_incorporacion': df_final[df_final['equipo'] == equipo]['fecha_incorporacion'].iloc[0],
                'porcentaje_disponibilidad': stats['porcentaje_total'],
                'horas_online': stats['horas_online_total'],
                'horas_offline': stats['horas_offline_total'],
                'tiempo_total': stats['tiempo_total']
            }
            for equipo, stats in disponibilidad_total.items()
        ])
        
        # Ordenar por porcentaje de disponibilidad de mayor a menor
        df_total = df_total.sort_values('porcentaje_disponibilidad', ascending=False)
        
        # Guardar el DataFrame en el archivo Excel
        df_total.to_excel(filename, sheet_name='Disponibilidad Total', index=False)
        
        print(f"✅ Reporte generado: {filename}")
        
        # Imprimir resumen
        print("\nResumen del reporte:")
        print(f"Período total: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
        print(f"Total de equipos: {len(disponibilidad_total)}")
        
        # Calcular y mostrar estadísticas generales
        disponibilidad_promedio = df_total['porcentaje_disponibilidad'].mean()
        mejor_disponibilidad = df_total.iloc[0]
        peor_disponibilidad = df_total.iloc[-1]
        
        print(f"\nDisponibilidad promedio general: {disponibilidad_promedio:.2f}%")
        print(f"\nEquipo con mejor disponibilidad: {mejor_disponibilidad['equipo']} ({mejor_disponibilidad['sysname']}) - {mejor_disponibilidad['porcentaje_disponibilidad']:.2f}%")
        print(f"Equipo con peor disponibilidad: {peor_disponibilidad['equipo']} ({peor_disponibilidad['sysname']}) - {peor_disponibilidad['porcentaje_disponibilidad']:.2f}%")
        
    else:
        print("⚠️ No se generó el reporte porque no hubo datos válidos.")

def obtener_fecha(mensaje):
    """Función para obtener una fecha válida del usuario"""
    while True:
        try:
            fecha_str = input(mensaje)
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d')
            return fecha
        except ValueError:
            print("❌ Formato de fecha inválido. Use YYYY-MM-DD (ejemplo: 2024-01-01)")

def menu_principal():
    """Función para mostrar el menú principal y obtener las fechas"""
    print("\n=== Generador de Reportes LibreNMS ===")
    print("Por favor, ingrese las fechas en formato YYYY-MM-DD")
    
    # Obtener fecha de inicio
    fecha_inicio = obtener_fecha("\n📅 Ingrese la fecha de inicio (YYYY-MM-DD): ")
    
    # Obtener fecha de fin
    fecha_fin = obtener_fecha("📅 Ingrese la fecha de fin (YYYY-MM-DD): ")
    
    # Validar que la fecha de inicio sea anterior a la fecha de fin
    if fecha_inicio > fecha_fin:
        print("\n❌ Error: La fecha de inicio debe ser anterior a la fecha de fin")
        return None, None
    
    return fecha_inicio, fecha_fin

if __name__ == '__main__':
    while True:
        fecha_inicio, fecha_fin = menu_principal()
        
        if fecha_inicio and fecha_fin:
            print("\n🔄 Generando reporte...")
            generar_reporte(fecha_inicio, fecha_fin)
        
        # Preguntar si desea generar otro reporte
        continuar = input("\n¿Desea generar otro reporte? (s/n): ").lower()
        if continuar != 's':
            print("\n👋 ¡Gracias por usar el generador de reportes!")
            break

