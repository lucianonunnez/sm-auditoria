import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ============================================
# CONFIGURACION
# ============================================

st.set_page_config(
    page_title="Swiss Medical | Auditoria Prestacional",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# ESTILOS CSS PROFESIONALES
# ============================================

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    :root {
        --sm-red: #E31E24;
        --sm-dark-red: #B71C1C;
        --sm-light-red: #FF5252;
        --bg-primary: #0E1117;
        --bg-secondary: #1A1D24;
        --bg-tertiary: #262B36;
        --text-primary: #FAFAFA;
        --text-secondary: #B0B3B8;
        --border-color: #3A3F4B;
    }
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .stApp {
        background-color: var(--bg-primary);
    }
    
    h1, h2, h3 {
        color: var(--text-primary) !important;
        font-weight: 600 !important;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: var(--bg-tertiary);
        border: 1px solid var(--border-color);
        border-radius: 6px;
        padding: 10px 20px;
        color: var(--text-secondary);
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--sm-red) 0%, var(--sm-dark-red) 100%);
        color: white;
        border-color: var(--sm-red);
    }
    
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select {
        background-color: var(--bg-tertiary) !important;
        border: 1px solid var(--border-color) !important;
        color: var(--text-primary) !important;
        border-radius: 4px !important;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, var(--sm-red) 0%, var(--sm-dark-red) 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 0.75rem 2rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        box-shadow: 0 4px 12px rgba(227, 30, 36, 0.3) !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
    }
    
    .metric-card {
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 1.25rem;
        text-align: center;
    }
    
    .alert-box {
        padding: 1.5rem;
        border-radius: 8px;
        margin: 1rem 0;
        color: white;
    }
    
    .alert-normal { background: linear-gradient(135deg, #1B5E20 0%, #2E7D32 100%); }
    .alert-warning { background: linear-gradient(135deg, #E65100 0%, #F57C00 100%); }
    .alert-danger { background: linear-gradient(135deg, var(--sm-dark-red) 0%, var(--sm-red) 100%); }
    .alert-info { background: linear-gradient(135deg, #01579B 0%, #0277BD 100%); }
    
    [data-testid="stSidebar"] {
        background-color: var(--bg-secondary);
        border-right: 1px solid var(--border-color);
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ============================================
# FUNCIONES DE CARGA
# ============================================

@st.cache_data
def cargar_datos():
    """Carga datos del sistema"""
    try:
        df = pd.read_csv('base_global_unificada.csv.gz', compression='gzip', encoding='utf-8')
        df['MesFecha'] = pd.to_datetime(df['MesFecha'])
        df['CM'] = pd.to_numeric(df['CM'], errors='coerce')
        df['PU'] = pd.to_numeric(df['PU'], errors='coerce')
        df['Q'] = pd.to_numeric(df['Q'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return None

# ============================================
# FUNCIONES DE ANALISIS
# ============================================

def buscar_historico(base, prestador, prestacion):
    """Busca historico de una prestacion"""
    mask = base['ID'].astype(str).str.upper() == str(prestador).upper()
    
    if prestacion and 'Prestacion' in base.columns:
        prestacion_clean = str(prestacion).upper().strip()
        mask &= base['Prestacion'].astype(str).str.upper().str.contains(
            prestacion_clean[:30], na=False, regex=False
        )
    
    return base[mask].copy()

def calcular_estadisticas(hist, fecha_auditoria):
    """Calcula estadisticas del historico"""
    d = hist[hist['MesFecha'] < pd.to_datetime(fecha_auditoria)].copy()
    
    if len(d) < 2:
        return None
    
    d = d.dropna(subset=['CM'])
    
    if len(d) == 0:
        return None
    
    return {
        'promedio': float(d['CM'].mean()),
        'mediana': float(d['CM'].median()),
        'std': float(d['CM'].std()),
        'min': float(d['CM'].min()),
        'max': float(d['CM'].max()),
        'q25': float(d['CM'].quantile(0.25)),
        'q75': float(d['CM'].quantile(0.75)),
        'q90': float(d['CM'].quantile(0.90)),
        'q95': float(d['CM'].quantile(0.95)),
        'n_registros': len(d),
        'datos': d['CM'].values
    }

def clasificar_anomalia(z_score):
    """Clasifica el nivel de anomalia"""
    if abs(z_score) < 1:
        return "NORMAL", "alert-normal", "Dentro del rango esperado"
    elif abs(z_score) < 2:
        return "REVISAR", "alert-warning", "Desviacion moderada"
    else:
        if z_score > 0:
            return "ALERTA ALTA", "alert-danger", "Sobrecosto significativo"
        else:
            return "INUSUAL BAJO", "alert-info", "Costo muy bajo"

# ============================================
# FUNCIONES DE GRAFICOS
# ============================================

def crear_grafico_evolucion_cm(df_prestador):
    """Crea grafico de evolucion de CM por prestacion"""
    
    # Filtrar datos con CM valido
    df_plot = df_prestador[df_prestador['CM'].notna()].copy()
    df_plot = df_plot.sort_values('MesFecha')
    
    # Agrupar por prestacion y fecha
    df_agg = df_plot.groupby(['MesFecha', 'Prestacion'])['CM'].sum().reset_index()
    
    # Top prestaciones por volumen total
    top_prestaciones = df_plot.groupby('Prestacion')['CM'].sum().nlargest(10).index.tolist()
    df_top = df_agg[df_agg['Prestacion'].isin(top_prestaciones)]
    
    fig = go.Figure()
    
    for prestacion in top_prestaciones:
        data = df_top[df_top['Prestacion'] == prestacion]
        fig.add_trace(go.Scatter(
            x=data['MesFecha'],
            y=data['CM'],
            mode='lines+markers',
            name=prestacion[:40],
            hovertemplate='<b>%{fullData.name}</b><br>Fecha: %{x}<br>CM: $%{y:,.2f}<extra></extra>'
        ))
    
    fig.update_layout(
        title="Evolucion Temporal del Costo Medico (CM) - Top 10 Prestaciones",
        xaxis_title="Mes",
        yaxis_title="Costo Medico (CM)",
        template="plotly_dark",
        height=500,
        hovermode='x unified',
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def crear_grafico_variacion_pu(df_prestador):
    """Crea grafico de variacion de precio unitario"""
    
    df_plot = df_prestador[df_prestador['PU'].notna()].copy()
    df_plot = df_plot.sort_values('MesFecha')
    
    # Calcular variacion porcentual mensual
    df_plot['PU_pct_change'] = df_plot.groupby('Prestacion')['PU'].pct_change() * 100
    
    # Top prestaciones
    top_prestaciones = df_plot.groupby('Prestacion')['CM'].sum().nlargest(10).index.tolist()
    df_top = df_plot[df_plot['Prestacion'].isin(top_prestaciones)]
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("Precio Unitario (PU)", "Variacion Mensual (%)"),
        vertical_spacing=0.12,
        row_heights=[0.6, 0.4]
    )
    
    for prestacion in top_prestaciones:
        data = df_top[df_top['Prestacion'] == prestacion]
        
        # Grafico de PU
        fig.add_trace(
            go.Scatter(
                x=data['MesFecha'],
                y=data['PU'],
                mode='lines',
                name=prestacion[:40],
                showlegend=True,
                hovertemplate='%{y:,.2f}'
            ),
            row=1, col=1
        )
        
        # Grafico de variacion
        fig.add_trace(
            go.Bar(
                x=data['MesFecha'],
                y=data['PU_pct_change'],
                name=prestacion[:40],
                showlegend=False,
                hovertemplate='%{y:+.1f}%'
            ),
            row=2, col=1
        )
    
    fig.update_xaxes(title_text="Mes", row=2, col=1)
    fig.update_yaxes(title_text="Precio Unitario ($)", row=1, col=1)
    fig.update_yaxes(title_text="Variacion (%)", row=2, col=1)
    
    fig.update_layout(
        title="Analisis de Variacion de Precios Unitarios",
        template="plotly_dark",
        height=700,
        showlegend=True,
        hovermode='x unified',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def crear_grafico_distribucion(stats, importe_cm, titulo):
    """Crea grafico de distribucion"""
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=stats['datos'],
        name='Distribucion Historica',
        marker_color='rgba(99, 110, 250, 0.6)',
        nbinsx=30
    ))
    
    fig.add_vline(
        x=importe_cm,
        line_dash="dash",
        line_color="#E31E24",
        line_width=3,
        annotation_text=f"Consulta: ${importe_cm:,.0f}",
        annotation_position="top"
    )
    
    fig.add_vline(
        x=stats['promedio'],
        line_dash="dot",
        line_color="#4CAF50",
        line_width=2,
        annotation_text=f"Promedio: ${stats['promedio']:,.0f}",
        annotation_position="bottom"
    )
    
    fig.update_layout(
        title=titulo,
        xaxis_title="Importe (CM)",
        yaxis_title="Frecuencia",
        template="plotly_dark",
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def crear_grafico_boxplot(df_prestador):
    """Crea boxplot comparativo de prestaciones"""
    
    df_plot = df_prestador[df_prestador['CM'].notna()].copy()
    top_prestaciones = df_plot.groupby('Prestacion')['CM'].sum().nlargest(10).index.tolist()
    df_top = df_plot[df_plot['Prestacion'].isin(top_prestaciones)]
    
    fig = go.Figure()
    
    for prestacion in top_prestaciones:
        data = df_top[df_top['Prestacion'] == prestacion]['CM']
        fig.add_trace(go.Box(
            y=data,
            name=prestacion[:40],
            boxmean='sd'
        ))
    
    fig.update_layout(
        title="Distribucion de Costos por Prestacion (Boxplot)",
        yaxis_title="Costo Medico (CM)",
        template="plotly_dark",
        height=500,
        showlegend=True,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def crear_tabla_resumen(df_prestador):
    """Crea tabla resumen de prestaciones"""
    
    df_plot = df_prestador[df_prestador['CM'].notna()].copy()
    
    resumen = df_plot.groupby('Prestacion').agg({
        'CM': ['count', 'sum', 'mean', 'std', 'min', 'max'],
        'PU': 'mean',
        'Q': 'sum'
    }).round(2)
    
    resumen.columns = ['N_Registros', 'CM_Total', 'CM_Promedio', 'CM_Std', 'CM_Min', 'CM_Max', 'PU_Promedio', 'Q_Total']
    resumen = resumen.sort_values('CM_Total', ascending=False)
    
    # Calcular variacion de PU
    variacion_pu = df_plot.groupby('Prestacion').apply(
        lambda x: ((x['PU'].iloc[-1] - x['PU'].iloc[0]) / x['PU'].iloc[0] * 100) if len(x) > 1 else 0
    ).round(1)
    
    resumen['Variacion_PU_%'] = variacion_pu
    
    return resumen.head(20)

def crear_heatmap_temporal(df_prestador):
    """Crea heatmap de actividad temporal"""
    
    df_plot = df_prestador[df_prestador['CM'].notna()].copy()
    df_plot['Año'] = df_plot['MesFecha'].dt.year
    df_plot['Mes'] = df_plot['MesFecha'].dt.month
    
    # Top 10 prestaciones
    top_prestaciones = df_plot.groupby('Prestacion')['CM'].sum().nlargest(10).index.tolist()
    df_top = df_plot[df_plot['Prestacion'].isin(top_prestaciones)]
    
    # Pivot para heatmap
    pivot = df_top.pivot_table(
        values='CM',
        index='Prestacion',
        columns='MesFecha',
        aggfunc='sum',
        fill_value=0
    )
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns.strftime('%Y-%m'),
        y=[p[:40] for p in pivot.index],
        colorscale='Reds',
        hovertemplate='Prestacion: %{y}<br>Mes: %{x}<br>CM: $%{z:,.0f}<extra></extra>'
    ))
    
    fig.update_layout(
        title="Heatmap de Actividad por Prestacion y Mes",
        xaxis_title="Mes",
        yaxis_title="Prestacion",
        template="plotly_dark",
        height=600,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

# ============================================
# INTERFAZ PRINCIPAL
# ============================================

def main():
    # Header
    st.markdown("""
        <h1 style='text-align: center; color: #E31E24; margin-bottom: 0;'>
            SWISS MEDICAL
        </h1>
        <div style='text-align: center; color: #B0B3B8; padding-bottom: 1rem; border-bottom: 2px solid #E31E24; margin-bottom: 2rem;'>
            Sistema de Auditoria Prestacional y Analisis Temporal
        </div>
    """, unsafe_allow_html=True)
    
    # Cargar datos
    datos = cargar_datos()
    
    if datos is None:
        st.error("Error al cargar los datos")
        return
    
    # Sidebar
    with st.sidebar:
        st.markdown("### INFORMACION DEL SISTEMA")
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Registros", f"{len(datos):,}")
        with col2:
            st.metric("Prestadores", f"{datos['ID'].nunique()}")
        
        st.markdown(f"**Ultima actualizacion:** {datetime.now().strftime('%d/%m/%Y')}")
        st.markdown(f"**Rango temporal:** {datos['MesFecha'].min().strftime('%Y-%m')} a {datos['MesFecha'].max().strftime('%Y-%m')}")
        
        st.markdown("---")
        st.markdown("### EJEMPLOS PARA TESTEAR")
        st.markdown("""
        **Auditoria:**
        - Prestador: **P1**
        - Prestacion: **Anteojos**
        - Importe: **$900,000**
        
        **Dashboard Temporal:**
        - Prestador: **P5** (832 prestaciones)
        - Prestador: **P147** (638 prestaciones)
        - Prestador: **P32** (613 prestaciones)
        
        **Prestaciones comunes:**
        - Consulta Ginecología
        - Colposcopia
        - Electrocardiograma
        """)
    
    # Tabs principales
    tab1, tab2 = st.tabs(["AUDITORIA DE FACTURA", "DASHBOARD TEMPORAL"])
    
    # ============================================
    # TAB 1: AUDITORIA
    # ============================================
    
    with tab1:
        st.markdown("## DATOS DE LA FACTURA A AUDITAR")
        
        prestadores_unicos = sorted(datos['ID'].astype(str).unique().tolist())
        prestaciones_unicas = sorted(datos['Prestacion'].dropna().unique().tolist())
        
        col1, col2 = st.columns(2)
        
        with col1:
            prestador = st.selectbox(
                "PRESTADOR",
                options=prestadores_unicos,
                index=0,
                help="Seleccione el prestador"
            )
            
            tipo_clase = st.selectbox(
                "TIPO CLASE CM",
                options=["Ambulatorio", "Internacion", "Otros"]
            )
            
            nomenclador = st.text_input(
                "NOMENCLADOR",
                value="Intervenciones quirurgicas"
            )
        
        with col2:
            prestacion = st.selectbox(
                "PRESTACION",
                options=prestaciones_unicas,
                index=0
            )
            
            mes_liquidado = st.date_input(
                "MES LIQUIDADO",
                value=datetime.now()
            )
            
            cantidad = st.number_input(
                "CANTIDAD",
                min_value=1,
                value=1
            )
        
        st.markdown("---")
        
        importe_cm = st.number_input(
            "IMPORTE CM (EN PESOS)",
            min_value=0.0,
            value=900000.0,
            step=1000.0,
            format="%.2f"
        )
        
        if st.button("REALIZAR AUDITORIA", use_container_width=True):
            
            with st.spinner("Procesando auditoria..."):
                
                hist = buscar_historico(datos, prestador, prestacion)
                
                if hist.empty:
                    hist = datos[datos['ID'].astype(str).str.upper() == prestador.upper()]
                
                if not hist.empty:
                    stats = calcular_estadisticas(hist, mes_liquidado)
                    
                    if stats:
                        z_score = (importe_cm - stats['promedio']) / stats['std'] if stats['std'] > 0 else 0
                        dif_pct = ((importe_cm - stats['promedio']) / stats['promedio'] * 100) if stats['promedio'] > 0 else 0
                        
                        clasificacion, alerta_class, mensaje = clasificar_anomalia(z_score)
                        
                        st.markdown("---")
                        st.markdown("## RESULTADO DE LA AUDITORIA")
                        
                        st.markdown(f"""
                        <div class='alert-box {alerta_class}'>
                            <div style='font-size: 1.5rem; font-weight: 700;'>{clasificacion}</div>
                            <div style='font-size: 1rem;'>{mensaje}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Metricas
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Importe Facturado", f"${importe_cm:,.0f}")
                        with col2:
                            st.metric("Promedio Historico", f"${stats['promedio']:,.0f}")
                        with col3:
                            st.metric("Z-Score", f"{z_score:.2f}σ")
                        with col4:
                            st.metric("Diferencia", f"{dif_pct:+.1f}%")
                        
                        # Graficos
                        st.markdown("### ANALISIS GRAFICO")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            fig_dist = crear_grafico_distribucion(stats, importe_cm, "Distribucion Historica")
                            st.plotly_chart(fig_dist, use_container_width=True)
                        
                        with col2:
                            # Crear boxplot simple de esta prestacion
                            fig_box = go.Figure()
                            fig_box.add_trace(go.Box(
                                y=stats['datos'],
                                name='CM',
                                marker_color='#636EFA',
                                boxmean='sd'
                            ))
                            fig_box.add_scatter(
                                x=[0],
                                y=[importe_cm],
                                mode='markers',
                                marker=dict(size=15, color='#E31E24', symbol='star'),
                                name='Consulta'
                            )
                            fig_box.update_layout(
                                title="Boxplot con Posicion de Consulta",
                                yaxis_title="Costo Medico (CM)",
                                template="plotly_dark",
                                height=400,
                                showlegend=True,
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)'
                            )
                            st.plotly_chart(fig_box, use_container_width=True)
                        
                        # Estadisticas detalladas
                        with st.expander("VER ESTADISTICAS DETALLADAS"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"""
                                | Metrica | Valor |
                                |---------|-------|
                                | Promedio | ${stats['promedio']:,.2f} |
                                | Mediana | ${stats['mediana']:,.2f} |
                                | Desv. Std | ${stats['std']:,.2f} |
                                | N° Registros | {stats['n_registros']} |
                                """)
                            with col2:
                                st.markdown(f"""
                                | Metrica | Valor |
                                |---------|-------|
                                | Minimo | ${stats['min']:,.2f} |
                                | Maximo | ${stats['max']:,.2f} |
                                | Percentil 90 | ${stats['q90']:,.2f} |
                                | Percentil 95 | ${stats['q95']:,.2f} |
                                """)
                        
                        # Recomendaciones
                        st.markdown("### RECOMENDACIONES")
                        if clasificacion == "NORMAL":
                            st.markdown("- Aprobar la factura\n- Proceder con el pago")
                        elif clasificacion == "REVISAR":
                            st.markdown("- Solicitar justificacion\n- Verificar complejidad\n- Comparar casos similares")
                        elif clasificacion == "ALERTA ALTA":
                            st.markdown(f"- RECHAZAR o SUSPENDER\n- Auditoria obligatoria\n- Excede promedio en {abs(dif_pct):.0f}%")
                        else:
                            st.markdown("- Verificar error de carga\n- Consultar area medica")
                    
                    else:
                        st.error("Historico insuficiente")
                else:
                    st.error(f"Sin datos del prestador {prestador}")
    
    # ============================================
    # TAB 2: DASHBOARD TEMPORAL
    # ============================================
    
    with tab2:
        st.markdown("## ANALISIS TEMPORAL DEL PRESTADOR")
        
        prestador_dashboard = st.selectbox(
            "SELECCIONE PRESTADOR PARA ANALIZAR",
            options=sorted(datos['ID'].astype(str).unique().tolist()),
            key="dashboard_prestador"
        )
        
        if st.button("GENERAR DASHBOARD", use_container_width=True):
            
            with st.spinner("Generando analisis temporal..."):
                
                df_prestador = datos[datos['ID'] == prestador_dashboard].copy()
                
                if len(df_prestador) == 0:
                    st.error(f"Sin datos del prestador {prestador_dashboard}")
                else:
                    # Metricas generales
                    st.markdown("### METRICAS GENERALES DEL PRESTADOR")
                    
                    col1, col2, col3, col4, col5 = st.columns(5)
                    
                    with col1:
                        st.metric("Prestaciones Unicas", df_prestador['Prestacion'].nunique())
                    with col2:
                        st.metric("Total Registros", len(df_prestador))
                    with col3:
                        cm_total = df_prestador['CM'].sum()
                        st.metric("CM Total", f"${cm_total:,.0f}")
                    with col4:
                        cm_promedio = df_prestador['CM'].mean()
                        st.metric("CM Promedio", f"${cm_promedio:,.0f}")
                    with col5:
                        meses = df_prestador['MesFecha'].nunique()
                        st.metric("Meses Activos", meses)
                    
                    st.markdown("---")
                    
                    # Graficos temporales
                    st.markdown("### EVOLUCION TEMPORAL")
                    
                    fig_evol = crear_grafico_evolucion_cm(df_prestador)
                    st.plotly_chart(fig_evol, use_container_width=True)
                    
                    fig_pu = crear_grafico_variacion_pu(df_prestador)
                    st.plotly_chart(fig_pu, use_container_width=True)
                    
                    # Heatmap
                    st.markdown("### HEATMAP DE ACTIVIDAD")
                    fig_heat = crear_heatmap_temporal(df_prestador)
                    st.plotly_chart(fig_heat, use_container_width=True)
                    
                    # Boxplot comparativo
                    st.markdown("### DISTRIBUCION DE COSTOS POR PRESTACION")
                    fig_box = crear_grafico_boxplot(df_prestador)
                    st.plotly_chart(fig_box, use_container_width=True)
                    
                    # Tabla resumen
                    st.markdown("### TABLA RESUMEN POR PRESTACION")
                    resumen = crear_tabla_resumen(df_prestador)
                    
                    # Formatear columnas monetarias
                    st.dataframe(
                        resumen.style.format({
                            'CM_Total': '${:,.2f}',
                            'CM_Promedio': '${:,.2f}',
                            'CM_Std': '${:,.2f}',
                            'CM_Min': '${:,.2f}',
                            'CM_Max': '${:,.2f}',
                            'PU_Promedio': '${:,.2f}',
                            'Q_Total': '{:,.0f}',
                            'Variacion_PU_%': '{:+.1f}%'
                        }),
                        use_container_width=True
                    )
                    
                    # Insights automáticos
                    st.markdown("### INSIGHTS AUTOMATICOS")
                    
                    # Prestacion con mayor crecimiento
                    df_crecimiento = df_prestador.groupby('Prestacion').apply(
                        lambda x: ((x['CM'].iloc[-1] - x['CM'].iloc[0]) / x['CM'].iloc[0] * 100) if len(x) > 1 else 0
                    ).sort_values(ascending=False)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**MAYOR CRECIMIENTO DE CM:**")
                        for i, (prest, crec) in enumerate(df_crecimiento.head(5).items(), 1):
                            st.markdown(f"{i}. {prest}: **+{crec:.1f}%**")
                    
                    with col2:
                        st.markdown("**MAYOR DECRECIMIENTO DE CM:**")
                        for i, (prest, crec) in enumerate(df_crecimiento.tail(5).items(), 1):
                            st.markdown(f"{i}. {prest}: **{crec:.1f}%**")
    
    # Footer
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0; color: #B0B3B8; border-top: 1px solid #3A3F4B; margin-top: 3rem;'>
        Swiss Medical S.A. | Sistema de Auditoria Automatizada v3.0 | Powered by AI/ML
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
