import requests
import pandas as pd
from datetime import datetime, timezone
import sys

LIBRENMS_URL = "https://monitorcoru.netlayer.cl/api/v0"
TOKEN = "fde5b824669326c729a1f08e1b9e25a5"

HEADERS = {
    "X-Auth-Token": TOKEN,
    "Content-Type": "application/json"
}


# -------------------------------------------------
# UTIL
# -------------------------------------------------

def fecha_a_epoch(fecha_str, fin_dia=False):
    dt = datetime.strptime(fecha_str, "%d-%m-%Y")

    if fin_dia:
        dt = dt.replace(hour=23, minute=59, second=59)
    else:
        dt = dt.replace(hour=0, minute=0, second=0)

    dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


# -------------------------------------------------
# DISPONIBILIDAD REAL POR RANGO
# -------------------------------------------------

def calcular_disponibilidad_rango(device_id, epoch_inicio, epoch_fin):

    url = f"{LIBRENMS_URL}/devices/{device_id}/outages"
    r = requests.get(url, headers=HEADERS)
    data = r.json()

    if data.get("status") != "ok":
        print(f"[{device_id}] ERROR obteniendo outages")
        return 0.0, 0

    outages = sorted(data.get("outages", []), key=lambda x: x["going_down"])

    rango_total = epoch_fin - epoch_inicio
    downtime = 0

    # ---- determinar estado inicial ----
    estado_down_al_inicio = False
    outage_activo_inicio = None

    for o in outages:
        if o["going_down"] <= epoch_inicio:
            if o["up_again"] is None or o["up_again"] > epoch_inicio:
                estado_down_al_inicio = True
                outage_activo_inicio = o

    # ---- si estaba DOWN al inicio ----
    if estado_down_al_inicio:
        fin_outage = outage_activo_inicio["up_again"] if outage_activo_inicio["up_again"] else epoch_fin
        fin_inter = min(fin_outage, epoch_fin)

        if fin_inter > epoch_inicio:
            downtime += (fin_inter - epoch_inicio)

    # ---- intersecciones normales ----
    for o in outages:

        outage_inicio = o["going_down"]
        outage_fin = o["up_again"] if o["up_again"] else epoch_fin

        if outage_fin <= epoch_inicio:
            continue

        if estado_down_al_inicio and o == outage_activo_inicio:
            continue

        inicio_inter = max(outage_inicio, epoch_inicio)
        fin_inter = min(outage_fin, epoch_fin)

        if fin_inter > inicio_inter:
            downtime += (fin_inter - inicio_inter)

    uptime = max(rango_total - downtime, 0)
    porcentaje = (uptime / rango_total) * 100 if rango_total > 0 else 0

    return round(porcentaje, 4), downtime


# -------------------------------------------------
# OBTENER DEVICES
# -------------------------------------------------

def obtener_dispositivos():
    url = f"{LIBRENMS_URL}/devices"
    r = requests.get(url, headers=HEADERS)
    data = r.json()

    if data.get("status") != "ok":
        print("Error obteniendo devices")
        sys.exit(1)

    return data.get("devices", [])


# -------------------------------------------------
# MAIN
# -------------------------------------------------

if __name__ == "__main__":

    if len(sys.argv) != 3:
        print("Uso: python disponibilidad.py DD-MM-YYYY DD-MM-YYYY")
        sys.exit(1)

    fecha_inicio = sys.argv[1]
    fecha_fin = sys.argv[2]

    epoch_inicio = fecha_a_epoch(fecha_inicio, False)
    epoch_fin = fecha_a_epoch(fecha_fin, True)

    print("--------------------------------------------------")
    print("RANGO UTC INICIO:", datetime.fromtimestamp(epoch_inicio, timezone.utc))
    print("RANGO UTC FIN   :", datetime.fromtimestamp(epoch_fin, timezone.utc))
    print("SEGUNDOS TOTALES:", epoch_fin - epoch_inicio)
    print("--------------------------------------------------")

    dispositivos = obtener_dispositivos()

    filas = []

    for d in dispositivos:

        device_id = d["device_id"]
        hostname = d["hostname"]
        ip = d.get("ip", "")
        sysname = d.get("sysName", hostname)
        fecha_insert = d.get("inserted", "")

        porcentaje, downtime = calcular_disponibilidad_rango(
            device_id,
            epoch_inicio,
            epoch_fin
        )

        print(f"[{device_id}] {hostname}")
        print(f"    Downtime (seg): {downtime}")
        print(f"    Disponibilidad: {porcentaje}%")
        print("--------------------------------------------------")

        filas.append({
            "device_id": device_id,
            "hostname": hostname,
            "sysname": sysname,
            "ip": ip,
            "fecha_incorporacion": fecha_insert,
            "porcentaje_disponibilidad_rango": porcentaje,
            "downtime_segundos": downtime
        })

    df = pd.DataFrame(filas)

    nombre_archivo = f"disponibilidad_{fecha_inicio}_a_{fecha_fin}.xlsx"
    df.to_excel(nombre_archivo, index=False)

    print("Excel generado:", nombre_archivo)