# Adaptación del sistema a Streamlit para despliegue web
import random
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Sistema de Análisis de Vuelos", layout="wide")
st.title("🌍 Sistema de Análisis de Vuelos Internacionales")

# --- CLASES ---
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

class Graficos:
    def __init__(self, df):
        self.df = df

    def mostrar_todos(self):
        col1, col2 = st.columns(2)
        with col1:
            self.barras_estado()
            self.pie_fab()
            self.hist_revision()
        with col2:
            self.scatter_prog_real()
            self.barras_dest()
            self.heatmap_horas()
            self.barras_apiladas()

    def barras_estado(self):
        fig, ax = plt.subplots()
        counts = self.df['Est. Vuelo'].value_counts()
        sns.barplot(x=counts.index, y=counts.values, ax=ax)
        ax.set_title("Vuelos por Estado"); ax.set_ylabel("# Vuelos")
        st.pyplot(fig)

    def pie_fab(self):
        fig, ax = plt.subplots()
        self.df['Fabricante'].value_counts().plot.pie(autopct="%1.1f%%", ax=ax, startangle=90)
        ax.set_ylabel("")
        ax.set_title("% Vuelos por Fabricante")
        st.pyplot(fig)

    def scatter_prog_real(self):
        df_d = self.df[self.df['Est. Vuelo']=='Demorado']
        if df_d.empty:
            st.info("No hay vuelos demorados para graficar scatter.")
            return
        fig, ax = plt.subplots()
        tp = pd.to_datetime(df_d['H. Prog'], format="%H:%M")
        tr = pd.to_datetime(df_d['Nueva H.'], format="%H:%M")
        ax.scatter(tp.dt.hour + tp.dt.minute/60, tr.dt.hour + tr.dt.minute/60)
        ax.plot([0,24],[0,24],'k--'); ax.set_xlim(0,24); ax.set_ylim(0,24)
        ax.set_title("Prog vs Real (Demorados)")
        st.pyplot(fig)

    def hist_revision(self):
        fig, ax = plt.subplots()
        ax.hist(self.df['Rev (h)'], bins=[0,1,2,3], edgecolor='black')
        ax.set_title("Distribución Revisiones")
        st.pyplot(fig)

    def barras_dest(self):
        fig, ax = plt.subplots()
        self.df['Destino'].value_counts().sort_values().plot.barh(ax=ax)
        ax.set_title("Vuelos por Destino")
        st.pyplot(fig)

    def heatmap_horas(self):
        fig, ax = plt.subplots()
        horas = pd.to_datetime(self.df['H. Prog'], format="%H:%M").dt.hour
        mat = horas.value_counts().reindex(range(24), fill_value=0).to_frame('Cantidad')
        sns.heatmap(mat.T, annot=True, fmt="d", cbar=False, ax=ax)
        ax.set_title("Vuelos por Hora")
        st.pyplot(fig)

    def barras_apiladas(self):
        fig, ax = plt.subplots()
        ct = pd.crosstab(self.df['Fabricante'], self.df['Est. Vuelo'])
        ct.plot.bar(stacked=True, ax=ax)
        ax.set_title("Estado por Fabricante")
        st.pyplot(fig)

# --- APLICACIÓN ---
gestor = GestorV()
opcion = st.sidebar.radio("Opciones", ["Generar Vuelos", "Cargar Excel"])

if opcion == "Generar Vuelos":
    gestor.generar()
elif opcion == "Cargar Excel":
    archivo = st.sidebar.file_uploader("Sube tu archivo .xlsx", type=["xlsx"])
    if archivo:
        gestor.cargar_excel(archivo)

if gestor.vuelos:
    df = gestor.obtener_df()
    st.subheader("📋 Tabla de Vuelos")
    st.dataframe(df, use_container_width=True)
    st.markdown("---")
    st.subheader("📊 Análisis Visual")
    g = Graficos(df)
    g.mostrar_todos()
else:
    st.warning("No hay datos para mostrar. Genera o carga vuelos.")
