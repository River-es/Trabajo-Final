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

class Graficos:
    def __init__(self, df):
        self.df = df

    def barras_estado(self):
        fig, ax = plt.subplots()
        counts = self.df['Est. Vuelo'].value_counts()
        sns.barplot(x=counts.index, y=counts.values, ax=ax)
        for i, v in enumerate(counts.values):
            ax.text(i, v + 0.5, str(v), ha='center')
        ax.set_title("Vuelos por Estado"); ax.set_ylabel("# Vuelos"); ax.set_xlabel("Estado")
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
        ax.set_title("Prog vs Real (Demorados)"); ax.set_xlabel("Hora Programada"); ax.set_ylabel("Hora Real")
        st.pyplot(fig)

    def hist_revision(self):
        fig, ax = plt.subplots()
        n, bins, patches = ax.hist(self.df['Rev (h)'], bins=[0,1,2,3], edgecolor='black')
        for i in range(len(n)):
            ax.text((bins[i]+bins[i+1])/2, n[i]+0.2, str(int(n[i])), ha='center')
        ax.set_title("Distribución Revisiones"); ax.set_xlabel("Horas de revisión"); ax.set_ylabel("# Vuelos")
        st.pyplot(fig)

    def barras_dest(self, top=15):
        fig, ax = plt.subplots()
        data = self.df['Destino'].value_counts().head(top).sort_values()
        data.plot.barh(ax=ax)
        for i, v in enumerate(data.values):
            ax.text(v + 0.5, i, str(v), va='center')
        ax.set_title(f"Top {top} Vuelos por Destino"); ax.set_xlabel("# Vuelos")
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
        for c in ax.containers:
            ax.bar_label(c, label_type='center')
        ax.set_title("Estado por Fabricante"); ax.set_ylabel("# Vuelos")
        st.pyplot(fig)

    def mostrar_todos(self):
        st.markdown("### 📊 Análisis visual")
        col1, col2 = st.columns(2)
        with col1:
            self.barras_estado()
        with col2:
            self.pie_fab()
        with col1:
            self.scatter_prog_real()
        with col2:
            self.hist_revision()
        with col1:
            self.barras_dest(15)
        with col2:
            self.heatmap_horas()
        self.barras_apiladas()

    def guardar_pdf(self, nombre):
        carpeta_descargas = os.path.join(os.path.expanduser('~'), 'Downloads')
        path = os.path.join(carpeta_descargas, f"{nombre}.pdf")
        with PdfPages(path) as pdf:
            fig, ax = plt.subplots(figsize=(12, len(self.df)*0.25+1))
            ax.axis('off')
            tbl = ax.table(cellText=self.df.values, colLabels=self.df.columns, loc='center')
            tbl.auto_set_font_size(False); tbl.set_fontsize(6); tbl.scale(1,1.2)
            pdf.savefig(fig); plt.close(fig)
            for func in [self.barras_estado, self.pie_fab, self.scatter_prog_real, self.hist_revision, lambda: self.barras_dest(15), self.heatmap_horas, self.barras_apiladas]:
                fig, ax = plt.subplots()
                func()
                pdf.savefig(fig); plt.close(fig)
        st.success("El PDF se descargó satisfactoriamente.")

# --- APLICACIÓN PRINCIPAL ---
if 'gestor' not in st.session_state:
    st.session_state.gestor = GestorV()
    st.session_state.vuelos_generados = False

op_datos = st.sidebar.radio("Opciones", ["Generar vuelos", "Cargar Excel"])

if op_datos == "Generar vuelos":
    if st.sidebar.button("Generar"):
        st.session_state.gestor.generar()
        st.session_state.vuelos_generados = True
elif op_datos == "Cargar Excel":
    archivo = st.sidebar.file_uploader("Excel (sin .xlsx)", type=["xlsx"])
    if archivo:
        st.session_state.gestor.cargar_excel(archivo)
        st.session_state.vuelos_generados = True

if st.session_state.vuelos_generados:
    df = st.session_state.gestor.obtener_df()
    st.subheader("📋 Tabla de vuelos")
    st.dataframe(df, use_container_width=True)
    st.markdown("---")
    g = Graficos(df)

    opciones = [
        "Gráfico de barras", "Gráfico de dispersión", "Gráfico de pastel", "Gráfico de barras horizontales",
        "Histograma", "Mapa de calor", "Gráfico de columnas apiladas", "Medidas de tendencia central",
        "Dashboard", "Descargar análisis en PDF"
    ]
    op_graf = st.sidebar.radio("", opciones)

    if op_graf == "Gráfico de barras":
        g.barras_estado()
    elif op_graf == "Gráfico de dispersión":
        g.scatter_prog_real()
    elif op_graf == "Gráfico de pastel":
        g.pie_fab()
    elif op_graf == "Gráfico de barras horizontales":
        top = st.sidebar.selectbox("Top destinos", [15,10,5])
        g.barras_dest(top=top)
    elif op_graf == "Histograma":
        g.hist_revision()
    elif op_graf == "Mapa de calor":
        g.heatmap_horas()
    elif op_graf == "Gráfico de columnas apiladas":
        g.barras_apiladas()
    elif op_graf == "Medidas de tendencia central":
        g.medidas_tendencia()
    elif op_graf == "Dashboard":
        g.mostrar_todos()
    elif op_graf == "Descargar análisis en PDF":
        nombre = st.text_input("Nombre del archivo PDF")
        if nombre:
            g.guardar_pdf(nombre)
else:
    st.warning("No hay datos disponibles. Genera o carga vuelos.")
