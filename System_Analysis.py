import random
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

# --- MODELO ---
class Vuelo:
    """Representa un vuelo con atributos y cálculos."""
    def __init__(self, aer, dst, hora_prog, rev):
        self.aer = aer
        self.dst = dst.title()
        self.hora_prog = datetime.strptime(hora_prog, "%H:%M").strftime("%H:%M")
        self.rev = rev
        self.fab = 'Boeing' if self.dst in GestorV.EUROPA else 'Airbus'
        self.est_v = 'A tiempo' if rev == 0 else ('Demorado' if rev <= 2 else 'Cancelado')
        self.est_av = 'Operativo' if rev <= 2 else 'No operativo'
        self.hora_real = (
            (datetime.strptime(self.hora_prog, "%H:%M") + timedelta(hours=rev)).strftime("%H:%M")
            if rev <= 2 else ""
        )

    def to_dict(self):
        return {
            'Aerolínea': self.aer,
            'Destino': self.dst,
            'H. Prog': self.hora_prog,
            'Rev (h)': self.rev,
            'Fabricante': self.fab,
            'Est. Vuelo': self.est_v,
            'Est. Avión': self.est_av,
            'Nueva H.': self.hora_real
        }

# --- GESTOR ---
class GestorV:
    AEROLIST = [
        'Copa Airlines', 'Latam Airlines', 'Avianca', 'Argentina Airlines',
        'Aeromexico', 'Delta', 'United Airlines', 'American Airlines',
        'Air Canada', 'Air France', 'KLM', 'Iberia Airlines', 'Sky Airlines'
    ]
    DESTS = [
        'España', 'Francia', 'Países Bajos', 'Turquía', 'Uruguay', 'Ecuador',
        'Colombia', 'Chile', 'Brasil', 'Bolivia', 'Argentina', 'El Salvador',
        'Panamá', 'Cuba', 'México', 'Estados Unidos', 'Canadá', 'Costa Rica'
    ]
    EUROPA = {
        'Albania', 'Alemania', 'Andorra', 'Armenia', 'Austria', 'Azerbaiyán',
        'Bélgica', 'Bielorrusia', 'Bosnia y Herzegovina', 'Bulgaria', 'Chipre',
        'Croacia', 'Dinamarca', 'Eslovaquia', 'Eslovenia', 'España', 'Estonia',
        'Finlandia', 'Francia', 'Georgia', 'Grecia', 'Hungría', 'Irlanda',
        'Islandia', 'Italia', 'Kazajistán', 'Kosovo', 'Letonia', 'Liechtenstein',
        'Lituania', 'Luxemburgo', 'Malta', 'Moldavia', 'Mónaco', 'Montenegro',
        'Noruega', 'Países Bajos', 'Polonia', 'Portugal', 'Reino Unido',
        'República Checa', 'Macedonia del Norte', 'Rumanía', 'Rusia', 'San Marino',
        'Serbia', 'Suecia', 'Suiza', 'Turquía', 'Ucrania', 'Ciudad del Vaticano'
    }
    def __init__(self):
        self.vuelos = []
    def generar(self):
        """Genera vuelos con intervalos de 2 a 8 minutos para un día."""
        self.vuelos.clear()
        hora = datetime(1900,1,1,0,0)
        fin = datetime(1900,1,1,23,59)
        usadas = set()
        while True:
            hora += timedelta(minutes=random.randint(2,8))
            if hora > fin:
                break
            h_prog = hora.strftime("%H:%M")
            rev = self._sel_rev()
            h_real = ((hora+timedelta(hours=rev)).strftime("%H:%M") if rev<=2 else "")
            if h_prog not in usadas and (not h_real or h_real not in usadas):
                v = Vuelo(random.choice(self.AEROLIST), random.choice(self.DESTS), h_prog, rev)
                self.vuelos.append(v)
                usadas.add(v.hora_prog)
                if v.hora_real:
                    usadas.add(v.hora_real)
    @staticmethod
    def _sel_rev():
        r = random.random()
        if r < 0.7: return 0
        if r < 0.9: return random.choice([1,2])
        return 3
    def to_df(self):
        """Convierte los vuelos a DataFrame."""
        return pd.DataFrame([v.to_dict() for v in self.vuelos])

# --- GRÁFICOS & TENDENCIA ---
class Graphs:
    def __init__(self, df):
        self.df = df
    def scatter(self):
        fig,ax=plt.subplots(figsize=(6,4))
        d=self.df[self.df['Est. Vuelo']=='Demorado']
        x=pd.to_datetime(d['H. Prog'],"%H:%M").dt.hour + pd.to_datetime(d['H. Prog'],"%H:%M").dt.minute/60
        y=pd.to_datetime(d['Nueva H.'],"%H:%M").dt.hour + pd.to_datetime(d['Nueva H.'],"%H:%M").dt.minute/60
        ax.scatter(x,y,alpha=0.7)
        ax.plot([0,24],[0,24],'k--');ax.set(xlim=(0,24),ylim=(0,24),xlabel='Hora Prog (h)',ylabel='Hora Real (h)',title='Prog vs Real')
        return fig
    def stacked(self):
        fig,ax=plt.subplots(figsize=(6,4))
        pd.crosstab(self.df['Fabricante'],self.df['Est. Vuelo']).plot.bar(stacked=True,ax=ax)
        ax.set(xlabel='',ylabel='N° vuelos',title='Estado x Fabricante')
        return fig
    def tendencia(self):
        r=self.df['Rev (h)'][self.df['Rev (h)']>0]
        m=int(r.mean()*10)/10
        med=int(r.median()*10)/10
        mo=int(r.mode().iloc[0]*10)/10 if not r.mode().empty else 0
        mx=int(r.max()*10)/10
        mn=int(r.min()*10)/10
        return pd.DataFrame({'Métrica':['Media','Mediana','Moda','Máx','Mín'],
                             'Valor':[f"{m:.1f}h",f"{med:.1f}h",f"{mo:.1f}h",f"{mx:.1f}h",f"{mn:.1f}h"]})

# --- STREAMLIT ---
st.set_page_config(page_title="Sistema Vuelos",layout="wide")
st.title("🌍 Sistema de Análisis de Vuelos Internacionales")
with st.sidebar:
    st.header("Datos")
    if st.button("Generar vuelos"):
        gestor=GestorV();gestor.generar();df=gestor.to_df()
    else:
        fn=st.text_input("Excel (sin .xlsx)")
        if st.button("Cargar Excel"):
            if fn.strip(): df=pd.read_excel(f"{fn}.xlsx")
            else:st.error("Nombre requerido");st.stop()
st.subheader("Tabla de vuelos")
st.dataframe(df,use_container_width=True)
st.subheader("Gráficos")
c1,c2,c3=st.columns(3)
with c1: st.bar_chart(df['Est. Vuelo'].value_counts(),use_container_width=True)
with c2:plt.figure();st.pyplot(Graphs(df).scatter())
with c3:plt.figure();st.pyplot(Graphs(df).stacked())
st.subheader("Tendencia central")
st.table(Graphs(df).tendencia())

# Sugerencias
st.sidebar.markdown("---")
st.sidebar.write("Filtros y mapas interactivos")
