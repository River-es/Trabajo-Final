# Adaptación del sistema a Streamlit para despliegue web con opciones detalladas
import random
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from matplotlib.backends.backend_pdf import PdfPages
import os
import tempfile

st.set_page_config(page_title="Sistema de Análisis de Vuelos", layout="wide")
st.title("🌍 Sistema de Análisis de Vuelos Internacionales")

class Vuelo:
    def __init__(self, aer, dst, hora_prog, rev):
        self.aer = aer
        self.dst = dst.title()
        self.hora_prog = self._fmt_hora(hora_prog)
        self.rev = rev
        self.fab = 'Boeing' if self.dst in GestorV.EUROPA else 'Airbus'
        self.est_v, self.est_av = self._calc_estado()
        self.hora_real = self._calc_nueva()

    def _fmt_hora(self, hora_str):
        return datetime.strptime(hora_str, "%H:%M").strftime("%H:%M")

    def _calc_estado(self):
        if self.rev == 0:
            return 'A tiempo', 'Operativo'
        elif self.rev in (1, 2):
            return 'Demorado', 'Operativo'
        else:
            return 'Cancelado', 'No operativo'

    def _calc_nueva(self):
        if self.rev > 2:
            return ""
        t = datetime.strptime(self.hora_prog, "%H:%M") + timedelta(hours=self.rev)
        return t.strftime("%H:%M")

    def to_dict(self):
        return {
            'Aerolínea': self.aer,
            'Destino': self.dst,
            'H. Prog': self.hora_prog,
            'Rev (h)': self.rev,
            'Fabricante': self.fab,
            'Est. Vuelo': self.est_v,
            'Est. Avion': self.est_av,
            'Nueva H.': self.hora_real
        }

class GestorV:
    AEROLIST = ['Copa Airlines','Latam Airlines','Avianca','Argentina Airlines','Aeromexico','Delta','United Airlines','American Airlines','Air Canada','Air France','KLM','Iberia Airlines','Sky Airlines']
    DESTS = ['España','Francia','Países Bajos','Turquía','Uruguay','Ecuador','Colombia','Chile','Brasil','Bolivia','Argentina','El Salvador','Panamá','Cuba','México','Estados Unidos','Canadá','Costa Rica']
    EUROPA = {'España','Francia','Países Bajos','Turquía'}

    def __init__(self):
        self.vuelos = []

    def generar(self):
        self.vuelos.clear()
        hora = datetime.strptime("00:00", "%H:%M")
        usadas = set()
        while True:
            hora += timedelta(minutes=random.randint(2,8))
            if hora > datetime.strptime("23:59","%H:%M"):
                break
            h_prog = hora.strftime("%H:%M")
            rev = self._seleccion_rev()
            h_real = (hora + timedelta(hours=rev)).strftime("%H:%M") if rev <=2 else ""
            if h_prog not in usadas and (not h_real or h_real not in usadas):
                vuelo = Vuelo(random.choice(self.AEROLIST), random.choice(self.DESTS), h_prog, rev)
                self.vuelos.append(vuelo)
                usadas.add(vuelo.hora_prog)
                if vuelo.hora_real:
                    usadas.add(vuelo.hora_real)

    @staticmethod
    def _seleccion_rev():
        r = random.random()
        if r < 0.7:
            return 0
        elif r < 0.9:
            return random.choice([1,2])
        return 3

    def cargar_excel(self, archivo):
        self.vuelos.clear()
        df = pd.read_excel(archivo)
        for _, r in df.iterrows():
            self.vuelos.append(Vuelo(r['Aerolínea'], r['Destino'], r['H. Prog'], int(r['Rev (h)'])))

    def obtener_df(self):
        return pd.DataFrame([v.to_dict() for v in self.vuelos])

# --- Controlador de datos persistentes en sesión ---
if 'gestor' not in st.session_state:
    st.session_state['gestor'] = GestorV()

if 'df' not in st.session_state:
    st.session_state['df'] = pd.DataFrame()

opcion = st.sidebar.radio("Opciones", [
    "Generar vuelos", "Cargar Excel",
    "Gráfico de barras", "Gráfico de dispersión", "Gráfico de pastel", "Gráfico de barras horizontales",
    "Histograma", "Mapa de calor", "Gráfico de columnas apiladas",
    "Medidas de tendencia central", "Dashboard", "Descargar análisis en PDF"
])

if opcion == "Generar vuelos":
    if st.button("Generar"):
        st.session_state['gestor'].generar()
        st.session_state['df'] = st.session_state['gestor'].obtener_df()

elif opcion == "Cargar Excel":
    archivo = st.file_uploader("Selecciona el archivo Excel", type=[".xlsx"])
    if archivo:
        st.session_state['gestor'].cargar_excel(archivo)
        st.session_state['df'] = st.session_state['gestor'].obtener_df()

elif not st.session_state['df'].empty:
    g = Graficos(st.session_state['df'])
    if opcion == "Gráfico de barras":
        g.barras_estado()
    elif opcion == "Gráfico de dispersión":
        g.scatter_prog_real()
    elif opcion == "Gráfico de pastel":
        g.pie_fab()
    elif opcion == "Gráfico de barras horizontales":
        top = st.radio("Top destinos", [5, 10, 15], horizontal=True)
        g.barras_dest(top)
    elif opcion == "Histograma":
        g.hist_revision()
    elif opcion == "Mapa de calor":
        g.heatmap_horas()
    elif opcion == "Gráfico de columnas apiladas":
        g.barras_apiladas()
    elif opcion == "Medidas de tendencia central":
        g.medidas_tendencia()
    elif opcion == "Dashboard":
        st.markdown("## 📊 Análisis visual")
        col1, col2 = st.columns(2)
        with col1:
            g.barras_estado()
            g.hist_revision()
            g.barras_apiladas()
        with col2:
            g.pie_fab()
            g.scatter_prog_real()
            g.heatmap_horas()
        g.barras_dest(10)
    elif opcion == "Descargar análisis en PDF":
        nombre = st.text_input("Nombre del PDF (sin extensión):")
        if nombre:
            carpeta_descargas = os.path.join(os.path.expanduser('~'), 'Downloads')
            path = os.path.join(carpeta_descargas, f"{nombre}.pdf")
            g.guardar_pdf(path)
            st.success("El PDF se descargó satisfactoriamente.")
else:
    st.warning("No hay datos cargados o generados. Por favor, selecciona una opción válida.")
