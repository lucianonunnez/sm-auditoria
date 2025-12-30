import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import joblib

# Configuración de la página
st.set_page_config(
    page_title="Auditoría Swiss Medical",
    page_icon="🏥",
    layout="wide"
)

# Cargar modelo y datos (una sola vez)
@st.cache_resource
def cargar_recursos():
    """Carga el modelo, scaler y datos históricos"""
    try:
        base_global = pd.read_csv('base_global_unificada.csv.gz', compression='gzip')
        base_global['MesFecha'] = pd.to_datetime(base_global['MesFecha'])
        return base_global
    except Exception as e:
        st.error(f"Error al cargar recursos: {e}")
        return None

def buscar_historico(base, prestador, prestacion):
    """Busca histórico de una prestación"""
    mask = base['ID'].astype(str).str.upper() == str(prestador).upper()
    
    if 'Prestacion' in base.columns:
        prestacion_clean = str(prestacion).upper().strip()
        mask &= base['Prestacion'].astype(str).str.upper().str.contains(prestacion_clean[:30], na=False, regex=False)
    
    return base[mask].copy()

def construir_features(hist, fecha_auditoria):
    """Construye estadísticas del histórico"""
    d = hist[hist['MesFecha'] < pd.to_datetime(fecha_auditoria)].copy()
    
    if len(d) < 2:
        return None
    
    d['CM'] = pd.to_numeric(d['CM'], errors='coerce')
    d = d.dropna(subset=['CM'])
    
    if len(d) == 0:
        return None
    
    return {
        'CM_promedio': float(d['CM'].mean()),
        'CM_mediana': float(d['CM'].median()),
        'CM_std': float(d['CM'].std()),
        'CM_min': float(d['CM'].min()),
        'CM_max': float(d['CM'].max()),
        'CM_q25': float(d['CM'].quantile(0.25)),
        'CM_q75': float(d['CM'].quantile(0.75)),
        'n_registros': len(d)
    }

# ============================================
# INTERFAZ PRINCIPAL
# ============================================

st.title("🏥 Swiss Medical - Auditoría de Prestaciones")
st.markdown("---")

# Cargar recursos
base_global = cargar_recursos()

if base_global is None:
    st.error("⚠️ No se pudieron cargar los datos históricos")
    st.stop()

# Sidebar con información
with st.sidebar:
    st.header("ℹ️ Información")
    st.write(f"**Registros históricos:** {len(base_global):,}")
    st.write(f"**Prestadores únicos:** {base_global['ID'].nunique()}")
    st.write(f"**Última actualización:** {datetime.now().strftime('%d/%m/%Y')}")
    st.markdown("---")
    st.write("**Clasificación:**")
    st.write("🟢 Normal: Dentro del rango")
    st.write("🟡 Revisar: Desviación moderada")
    st.write("🔴 Alerta: Requiere auditoría")

# Formulario principal
st.header("📋 Datos de la Factura")

col1, col2 = st.columns(2)

with col1:
    prestador = st.text_input("Prestador *", value="P1", help="Código del prestador (ej: P1, P2)")
    tipo_clase = st.selectbox("Tipo Clase CM", ["Ambulatorio", "Internación", "Otros"], help="Tipo de prestación")
    nomenclador = st.text_input("Nomenclador", value="Intervenciones quirúrgicas", help="Clasificación del nomenclador")

with col2:
    prestacion = st.text_input("Prestación *", value="Vitrectomía", help="Nombre de la prestación a auditar")
    mes_liquidado = st.date_input("Mes Liquidado *", value=datetime.now(), help="Fecha del registro a auditar")
    cantidad = st.number_input("Cantidad *", min_value=1, value=1, help="Cantidad de prestaciones")

st.markdown("---")

importe_cm = st.number_input("💰 Importe CM (en pesos) *", min_value=0.0, value=900000.0, step=1000.0, format="%.2f", help="Monto total de la factura")

# Botón de auditoría
if st.button("🔍 REALIZAR AUDITORÍA", type="primary", use_container_width=True):
    
    with st.spinner("Procesando auditoría..."):
        
        # Buscar histórico
        hist = buscar_historico(base_global, prestador, prestacion)
        
        if hist.empty:
            st.warning(f"⚠️ No se encontró histórico específico para '{prestacion}'")
            st.info("Buscando por prestador solamente...")
            hist = base_global[base_global['ID'].astype(str).str.upper() == prestador.upper()]
        
        if hist.empty:
            st.error(f"❌ No hay datos históricos del prestador '{prestador}'")
            st.info(f"💡 Prestadores disponibles: {base_global['ID'].unique()[:10].tolist()}")
            st.stop()
        
        st.success(f"✅ Encontrados {len(hist)} registros históricos")
        
        # Construir features
        feats = construir_features(hist, mes_liquidado)
        
        if feats is None:
            st.error("⚠️ Histórico insuficiente (<2 meses) o sin datos válidos de CM")
            st.stop()
        
        # Análisis
        cm_promedio = feats['CM_promedio']
        cm_std = feats['CM_std'] if feats['CM_std'] > 0 else cm_promedio * 0.2
        
        # Z-score
        z_score = (importe_cm - cm_promedio) / cm_std if cm_std > 0 else 0
        dif_pct = ((importe_cm - cm_promedio) / cm_promedio * 100) if cm_promedio > 0 else 0
        
        # Clasificación
        if abs(z_score) < 1:
            label = "✅ NORMAL"
            accion = "Importe dentro del rango esperado"
            st.success(f"## {label}")
        elif abs(z_score) < 2:
            label = "🟡 REVISAR"
            accion = "Desviación moderada - Solicitar justificación"
            st.warning(f"## {label}")
        else:
            if z_score > 0:
                label = "🔴 ALERTA ALTA"
                accion = "SOBRECOSTO SIGNIFICATIVO - Auditoría obligatoria"
                st.error(f"## {label}")
            else:
                label = "🔵 INUSUALMENTE BAJO"
                accion = "Costo muy bajo - Verificar si es correcto"
                st.info(f"## {label}")
        
        st.write(f"**{accion}**")
        st.markdown("---")
        
        # Resultados en columnas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Importe Facturado", f"${importe_cm:,.2f}", delta=f"{dif_pct:+.1f}%")
        
        with col2:
            st.metric("Promedio Histórico", f"${cm_promedio:,.2f}")
        
        with col3:
            st.metric("Z-Score", f"{z_score:.2f}σ")
        
        # Detalles expandibles
        with st.expander("📊 Ver Análisis Detallado"):
            st.write("**Datos de la Factura:**")
            st.write(f"- Prestador: {prestador}")
            st.write(f"- Tipo: {tipo_clase}")
            st.write(f"- Nomenclador: {nomenclador}")
            st.write(f"- Prestación: {prestacion}")
            st.write(f"- Mes: {mes_liquidado.strftime('%B %Y')}")
            st.write(f"- Cantidad: {cantidad}")
            
            st.markdown("---")
            
            st.write("**Contexto Histórico:**")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"- Promedio: ${feats['CM_promedio']:,.2f}")
                st.write(f"- Mediana: ${feats['CM_mediana']:,.2f}")
                st.write(f"- Desv. Std: ${feats['CM_std']:,.2f}")
                st.write(f"- N° registros: {feats['n_registros']}")
            with col2:
                st.write(f"- Mínimo: ${feats['CM_min']:,.2f}")
                st.write(f"- Máximo: ${feats['CM_max']:,.2f}")
                st.write(f"- Percentil 25: ${feats['CM_q25']:,.2f}")
                st.write(f"- Percentil 75: ${feats['CM_q75']:,.2f}")
        
        # Histórico reciente
        with st.expander("📜 Ver Histórico Reciente"):
            hist_recent = hist[hist['MesFecha'] < pd.to_datetime(mes_liquidado)].tail(10)
            if len(hist_recent) > 0:
                display = hist_recent[['MesFecha', 'Q', 'CM']].copy()
                display['MesFecha'] = display['MesFecha'].dt.strftime('%Y-%m')
                display['CM'] = display['CM'].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "N/A")
                st.dataframe(display, use_container_width=True, hide_index=True)
        
        # Recomendaciones
        st.markdown("---")
        st.subheader("💡 Recomendaciones")
        
        if label == "✅ NORMAL":
            st.write("- ✓ Aprobar la factura")
            st.write("- ✓ Proceder con el pago")
        elif label == "🟡 REVISAR":
            st.write("- ⚠ Solicitar justificación del prestador")
            st.write("- ⚠ Verificar complejidad del caso")
            st.write("- ⚠ Comparar con casos similares")
        elif label == "🔴 ALERTA ALTA":
            st.write("- ✗ RECHAZAR o SUSPENDER el pago")
            st.write("- ✗ Solicitar auditoría médica detallada")
            st.write("- ✗ Pedir documentación respaldatoria")
            st.write(f"- ✗ El importe excede el promedio en {abs(dif_pct):.0f}%")
        else:
            st.write("- ? Verificar si hay error de carga")
            st.write("- ? Consultar con el área médica")

# Footer
st.markdown("---")
st.caption("Swiss Medical S.A. - Sistema de Auditoría Automatizada v2.0")
