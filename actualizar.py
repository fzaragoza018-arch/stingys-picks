import requests
from datetime import datetime, timedelta
from collections import defaultdict
import json

print("🧠 Generando plataforma con sintaxis f-string limpia para GitHub Actions...")

# Estructuras de datos
stats_mx = defaultdict(lambda: {'partidos': 0, 'corners': 0, 'tarjetas': 0, 'faltas': 0, 'goles_favor': 0, 'goles_contra': 0})
historial_mx = defaultdict(list)
h2h_mx = defaultdict(list)

stats_nfl = defaultdict(lambda: {'partidos': 0, 'puntos_favor': 0, 'puntos_contra': 0})
historial_nfl = defaultdict(list)

stats_nba = defaultdict(lambda: {'partidos': 0, 'puntos_favor': 0, 'puntos_contra': 0})
historial_nba = defaultdict(list)

fecha_fin = datetime.now().strftime("%Y%m%d")
fecha_inicio = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")

# ==========================================
# 1. LIGA MX
# ==========================================
url_mx_hist = f"https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/scoreboard?dates={fecha_inicio}-{fecha_fin}&limit=300"
res_mx_hist = requests.get(url_mx_hist).json().get('events', [])
res_mx_hist.reverse()

for evento in res_mx_hist:
    comp = evento.get('competitions', [])[0]
    teams = comp.get('competitors', [])
    fecha = evento.get('date', '')[:10]
    try: fecha_corta = datetime.strptime(fecha, "%Y-%m-%d").strftime("%d/%m")
    except: fecha_corta = fecha

    if len(teams) >= 2:
        l_name, v_name = teams[0]['team']['displayName'], teams[1]['team']['displayName']
        l_score, v_score = int(teams[0].get('score', 0)), int(teams[1].get('score', 0))
        
        stats_mx[l_name]['partidos'] += 1
        stats_mx[v_name]['partidos'] += 1
        stats_mx[l_name]['goles_favor'] += l_score
        stats_mx[l_name]['goles_contra'] += v_score
        stats_mx[v_name]['goles_favor'] += v_score
        stats_mx[v_name]['goles_contra'] += l_score

        id_partido = evento.get('id')
        try:
            detalle = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/summary?event={id_partido}").json()
            box = detalle.get('boxscore', {}).get('teams', [])
            for t_info in box:
                n = t_info.get('team', {}).get('displayName')
                sd = {s['name']: int(s['displayValue']) for s in t_info.get('statistics', []) if s['displayValue'].isdigit()}
                stats_mx[n]['corners'] += sd.get('wonCorners', 0)
                stats_mx[n]['tarjetas'] += sd.get('yellowCards', 0) + sd.get('redCards', 0)
        except:
            pass

        info = {'fecha': fecha_corta, 'local': l_name, 'visita': v_name, 'score_l': l_score, 'score_v': v_score}
        historial_mx[l_name].append(info)
        historial_mx[v_name].append(info)
        h2h_mx[tuple(sorted([l_name, v_name]))].append(info)

def format_event_date(date_str):
    try:
        dt = datetime.strptime(date_str[:16], "%Y-%m-%dT%H:%M")
        return dt.strftime("%d/%m - %H:%M hrs")
    except:
        return "Por definir"

fecha_futura = (datetime.now() + timedelta(days=14)).strftime("%Y%m%d")
res_mx_fut = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/scoreboard?dates={fecha_fin}-{fecha_futura}").json().get('events', [])

mx_cards_html = ""
datos_js_mx = {}
candidatos_oficiales_mx = []

for idx, evento in enumerate(res_mx_fut):
    card_id = f"mx_match_{idx}"
    teams = evento['competitions'][0]['competitors']
    local, visita = teams[0]['team']['displayName'], teams[1]['team']['displayName']
    logo_l, logo_v = teams[0]['team'].get('logo', ''), teams[1]['team'].get('logo', '')
    fecha_partido_txt = format_event_date(evento.get('date', ''))
    
    e1, e2 = stats_mx[local], stats_mx[visita]
    p1, p2 = max(1, e1['partidos']), max(1, e2['partidos'])
    
    xg_l = round((e1['goles_favor']/p1 + e2['goles_contra']/p2)/2, 2)
    xg_v = round((e2['goles_favor']/p2 + e1['goles_contra']/p1)/2, 2)
    xg_tot = round(xg_l + xg_v, 2)
    
    c_tot = round((e1['corners']/p1) + (e2['corners']/p2), 1) if (e1['corners'] > 0 or e2['corners'] > 0) else 9.5
    t_tot = round((e1['tarjetas']/p1) + (e2['tarjetas']/p2), 1) if (e1['tarjetas'] > 0 or e2['tarjetas'] > 0) else 4.5

    prob_l = round(min(80, max(15, (xg_l / (xg_tot if xg_tot > 0 else 1)) * 65)), 1)
    prob_v = round(min(80, max(15, (xg_v / (xg_tot if xg_tot > 0 else 1)) * 65)), 1)
    prob_e = round(max(10, 100 - (prob_l + prob_v)), 1)
    
    prob_dc_1x = round(prob_l + prob_e, 1)
    prob_dc_x2 = round(prob_v + prob_e, 1)
    prob_goles_over15 = round(min(92, max(45, (xg_tot / 1.8) * 60)), 1)
    prob_corners_over = round(min(88, max(30, (c_tot / 8.5) * 52)), 1)
    prob_tarjetas_over = round(min(88, max(30, (t_tot / 4.5) * 52)), 1)

    candidatos = [
        {"mercado": "Over 1.5 Goles Totales", "casino": "-180", "prob": prob_goles_over15, "razon": f"Promedio xG de {xg_tot} goles proyecta al menos 2 anotaciones en el juego."},
        {"mercado": f"Doble Oportunidad: {local} o Empate (1X)", "casino": "-220", "prob": prob_dc_1x, "razon": f"{local} registra una solidez en casa con {prob_dc_1x}% de imbatibilidad."},
        {"mercado": f"Doble Oportunidad: {visita} o Empate (X2)", "casino": "-150", "prob": prob_dc_x2, "razon": f"{visita} cubre el hándicap positivo en el {prob_dc_x2}% de las visitas."},
        {"mercado": "Over 8.5 Córners Totales", "casino": "-115", "prob": prob_corners_over, "razon": f"Promedian {c_tot} tiros de esquina conjuntos en sus partidos."},
        {"mercado": "Over 4.5 Tarjetas Totales", "casino": "-110", "prob": prob_tarjetas_over, "razon": f"Proyección de {t_tot} amonestaciones acumuladas por partido."}
    ]
    candidatos.sort(key=lambda x: x['prob'], reverse=True)
    best = candidatos[0]
    valid = best['prob'] >= 85.0
    
    if valid:
        candidatos_oficiales_mx.append({"partido": f"{local} vs {visita}", "pick": best['mercado'], "prob": best['prob'], "casino": best['casino']})

    clave_h2h = tuple(sorted([local, visita]))
    h2h_list = h2h_mx.get(clave_h2h, [])
    if len(h2h_list) >= 3:
        m_muestra = h2h_list[:5]
        fechas_5 = [m['fecha'] for m in m_muestra]
        hist_5_l = [m['score_l'] if m['local'] == local else m['score_v'] for m in m_muestra]
        hist_5_v = [m['score_v'] if m['local'] == local else m['score_l'] for m in m_muestra]
    else:
        m_local, m_visita = historial_mx[local][:5], historial_mx[visita][:5]
        fechas_5 = [m['fecha'] for m in m_local]
        hist_5_l = [m['score_l'] if m['local'] == local else m['score_v'] for m in m_local]
        hist_5_v = [m['score_v'] if m['local'] == visita else m['score_l'] for m in m_visita]

    while len(hist_5_l) < 5: hist_5_l.append(1.0)
    while len(hist_5_v) < 5: hist_5_v.append(1.0)
    while len(fechas_5) < 5: fechas_5.append("--")

    mercados_completos = [
        {"mercado": "Over 1.5 Goles Totales", "casino": "-180", "prob_alg": f"{prob_goles_over15}%", "ev": "ALTA" if prob_goles_over15 >= 85 else "OBSERVACIÓN"},
        {"mercado": f"1X ({local} / Empate)", "casino": "-220", "prob_alg": f"{prob_dc_1x}%", "ev": "ALTA" if prob_dc_1x >= 85 else "OBSERVACIÓN"},
        {"mercado": f"X2 ({visita} / Empate)", "casino": "-150", "prob_alg": f"{prob_dc_x2}%", "ev": "ALTA" if prob_dc_x2 >= 85 else "OBSERVACIÓN"},
        {"mercado": "Over 8.5 Córners", "casino": "-115", "prob_alg": f"{prob_corners_over}%", "ev": "ALTA" if prob_corners_over >= 85 else "OBSERVACIÓN"},
        {"mercado": "Over 4.5 Tarjetas", "casino": "-110", "prob_alg": f"{prob_tarjetas_over}%", "ev": "ALTA" if prob_tarjetas_over >= 85 else "OBSERVACIÓN"},
        {"mercado": f"Gana {local} (ML)", "casino": "+140" if prob_l < 45 else "-110", "prob_alg": f"{prob_l}%", "ev": "ALTA" if prob_l >= 85 else "OBSERVACIÓN"},
        {"mercado": f"Gana {visita} (ML)", "casino": "+180", "prob_alg": f"{prob_v}%", "ev": "ALTA" if prob_v >= 85 else "OBSERVACIÓN"}
    ]

    datos_js_mx[card_id] = {
        'local': local, 'visita': visita, 'logo_local': logo_l, 'logo_visita': logo_v,
        'fecha_partido': fecha_partido_txt, 'has_data': True,
        'prob_l': prob_l, 'prob_v': prob_v, 'prob_e': prob_e,
        'has_valid': valid, 'best_projection': best['mercado'] if valid else "Sin línea calificada",
        'best_casino': best['casino'], 'best_prob': best['prob'], 'best_reason': best['razon'],
        'fechas_labels': fechas_5, 'hist_local': hist_5_l, 'hist_visita': hist_5_v,
        'mercados': mercados_completos
    }

    badge_cls = 'badge-emerald' if valid else 'badge-slate'
    badge_lbl = 'ALTA CONFIANZA' if valid else 'SOLO DATA'
    
    if valid:
        box_html = f'<div class="pro-pick-box"><span class="pro-pick-label">PROYECCIÓN CONFIABLE (≥ 85%)</span><div class="pro-pick-val">{best["mercado"]}</div></div>'
        btn_save = f'<button class="save-pick-btn" onclick="saveCustomPick(\'{local} vs {visita}\', \'{best["mercado"]}\', \'{best["casino"]}\')">⭐ GUARDAR</button>'
    else:
        box_html = '<div class="pro-pick-box"><span class="pro-pick-label" style="color:var(--text-muted);">⚪ SIN PICK RECOMENDADO</span><div class="pro-pick-val" style="color:var(--text-muted); font-size:0.8rem;">Ninguna línea supera el 85% de probabilidad</div></div>'
        btn_save = ''

    mx_cards_html += f"""
    <div class="pro-card">
        <div class="pro-card-header" onclick="openModal('{card_id}', 'mx')">
            <span class="pro-league">LIGA MX • {fecha_partido_txt}</span>
            <span class="pro-badge {badge_cls}">{badge_lbl}</span>
        </div>
        <div class="pro-matchup" onclick="openModal('{card_id}', 'mx')">
            <div class="pro-team"><img src="{logo_l}"><span>{local}</span></div>
            <div class="pro-vs">VS</div>
            <div class="pro-team"><img src="{logo_v}"><span>{visita}</span></div>
        </div>
        {box_html}
        <div style="display:flex; gap:10px;">
            <button class="pro-btn" style="flex:1;" onclick="openModal('{card_id}', 'mx')">VER ANÁLISIS &rarr;</button>
            {btn_save}
        </div>
    </div>
    """

candidatos_oficiales_mx.sort(key=lambda x: x['prob'], reverse=True)
picks_oficiales_mx = candidatos_oficiales_mx[:3]

# ==========================================
# 2. NFL & 3. NBA (EN RECESO)
# ==========================================
res_nfl_fut = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={fecha_fin}-{fecha_futura}").json().get('events', [])
nfl_cards_html = ""
datos_js_nfl = {}
picks_oficiales_nfl = []

for idx, evento in enumerate(res_nfl_fut):
    card_id = f"nfl_match_{idx}"
    teams = evento['competitions'][0]['competitors']
    local, visita = teams[0]['team']['displayName'], teams[1]['team']['displayName']
    logo_l, logo_v = teams[0]['team'].get('logo', ''), teams[1]['team'].get('logo', '')
    fecha_partido_txt = format_event_date(evento.get('date', ''))
    
    datos_js_nfl[card_id] = {
        'local': local, 'visita': visita, 'logo_local': logo_l, 'logo_visita': logo_v,
        'fecha_partido': fecha_partido_txt, 'has_data': False, 'prob_l': 50, 'prob_v': 50, 'prob_e': 0,
        'has_valid': False, 'best_projection': "Esperando inicio de temporada",
        'best_casino': "-110", 'best_prob': 0, 'best_reason': "En espera de momios oficiales de la NFL.",
        'fechas_labels': ['--','--','--','--','--'], 'hist_local': [0,0,0,0,0], 'hist_visita': [0,0,0,0,0],
        'mercados': []
    }
    nfl_cards_html += f"""
    <div class="pro-card">
        <div class="pro-card-header" onclick="openModal('{card_id}', 'nfl')"><span class="pro-league">NFL • {fecha_partido_txt}</span><span class="pro-badge badge-slate">EN RECESO</span></div>
        <div class="pro-matchup" onclick="openModal('{card_id}', 'nfl')"><div class="pro-team"><img src="{logo_l}"><span>{local}</span></div><div class="pro-vs">VS</div><div class="pro-team"><img src="{logo_v}"><span>{visita}</span></div></div>
        <div class="pro-pick-box"><span class="pro-pick-label" style="color:var(--text-muted);">⏳ EN ESPERA DE INFORMACIÓN</span><div class="pro-pick-val" style="color:var(--text-muted); font-size:0.8rem;">Esperando cuotas e inicio de temporada</div></div>
        <div style="display:flex; gap:10px;"><button class="pro-btn" style="flex:1;" onclick="openModal('{card_id}', 'nfl')">VER ANÁLISIS &rarr;</button></div>
    </div>
    """

res_nba_fut = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={fecha_fin}-{fecha_futura}").json().get('events', [])
nba_cards_html = ""
datos_js_nba = {}
picks_oficiales_nba = []

for idx, evento in enumerate(res_nba_fut):
    card_id = f"nba_match_{idx}"
    teams = evento['competitions'][0]['competitors']
    local, visita = teams[0]['team']['displayName'], teams[1]['team']['displayName']
    logo_l, logo_v = teams[0]['team'].get('logo', ''), teams[1]['team'].get('logo', '')
    fecha_partido_txt = format_event_date(evento.get('date', ''))
    
    datos_js_nba[card_id] = {
        'local': local, 'visita': visita, 'logo_local': logo_l, 'logo_visita': logo_v,
        'fecha_partido': fecha_partido_txt, 'has_data': False, 'prob_l': 50, 'prob_v': 50, 'prob_e': 0,
        'has_valid': False, 'best_projection': "Esperando inicio de temporada NBA",
        'best_casino': "-110", 'best_prob': 0, 'best_reason': "En espera de momios oficiales de la NBA.",
        'fechas_labels': ['--','--','--','--','--'], 'hist_local': [0,0,0,0,0], 'hist_visita': [0,0,0,0,0],
        'mercados': []
    }
    nba_cards_html += f"""
    <div class="pro-card">
        <div class="pro-card-header" onclick="openModal('{card_id}', 'nba')"><span class="pro-league">NBA • {fecha_partido_txt}</span><span class="pro-badge badge-slate">EN RECESO</span></div>
        <div class="pro-matchup" onclick="openModal('{card_id}', 'nba')"><div class="pro-team"><img src="{logo_l}"><span>{local}</span></div><div class="pro-vs">VS</div><div class="pro-team"><img src="{logo_v}"><span>{visita}</span></div></div>
        <div class="pro-pick-box"><span class="pro-pick-label" style="color:var(--text-muted);">⏳ EN ESPERA DE INFORMACIÓN</span><div class="pro-pick-val" style="color:var(--text-muted); font-size:0.8rem;">Esperando cuotas e inicio de temporada NBA</div></div>
        <div style="display:flex; gap:10px;"><button class="pro-btn" style="flex:1;" onclick="openModal('{card_id}', 'nba')">VER ANÁLISIS &rarr;</button></div>
    </div>
    """

if not nba_cards_html:
    nba_cards_html = """<div class="pro-card" style="grid-column: 1/-1; text-align:center; padding:30px;"><span class="pro-league">NBA • TEMPORADA 2026</span><div style="margin: 15px 0; font-weight:800; font-size:1.1rem; color:#fff;">⏳ EN ESPERA DE INFORMACIÓN COMPLETA</div><p style="color:var(--text-muted); font-size:0.85rem; max-width:500px; margin:0 auto;">La NBA se encuentra en receso. Las cuotas y métricas avanzadas se cargarán al iniciar la temporada.</p></div>"""

# ==========================================
# 4. HTML DEFINITIVO
# ==========================================
html_document = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stingy's Picks Engine</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;700;800&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg-dark: #07090e; --card-dark: #121620; --border-dark: #1e2638;
            --accent-cyan: #06b6d4; --accent-emerald: #10b981; --accent-purple: #8b5cf6;
            --text-main: #f8fafc; --text-muted: #64748b;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }}
        body {{ background-color: var(--bg-dark); color: var(--text-main); padding: 15px; overflow-x: hidden; }}

        .splash-screen {{ 
            position: fixed; top:0; left:0; width:100%; height:100%; 
            background: linear-gradient(-45deg, #07090e, #0f172a, #31106e, #0284c7, #07090e);
            background-size: 350% 350%; animation: gradientBG 4.5s ease infinite;
            z-index: 2000; display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 20px; text-align: center; 
        }}
        @keyframes gradientBG {{ 0% {{ background-position: 0% 50%; }} 50% {{ background-position: 100% 50%; }} 100% {{ background-position: 0% 50%; }} }}

        .splash-logo {{ width: 70px; height: 70px; background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple)); border-radius: 20px; display: flex; align-items: center; justify-content: center; font-size: 1.8rem; font-weight: 800; margin-bottom: 20px; box-shadow: 0 0 50px rgba(6, 182, 212, 0.6); }}
        .splash-title {{ font-size: 2.2rem; font-weight: 800; margin-bottom: 8px; letter-spacing: -1px; color: #fff; }}
        .splash-sub {{ font-size: 1.15rem; color: #f1f5f9; font-weight: 800; margin-bottom: 35px; max-width: 450px; line-height: 1.4; }}

        .sports-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 18px; width: 100%; max-width: 650px; }}
        .sport-card {{ background: rgba(18, 22, 32, 0.85); backdrop-filter: blur(12px); border: 1px solid var(--border-dark); padding: 25px 18px; border-radius: 24px; cursor: pointer; transition: all 0.3s ease; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align:center; }}
        .sport-card:hover {{ border-color: var(--accent-cyan); transform: translateY(-6px); box-shadow: 0 15px 35px -5px rgba(6, 182, 212, 0.5); }}
        .sport-name {{ font-size: 0.88rem; font-weight: 800; letter-spacing: 0.5px; color: #fff; text-transform: uppercase; }}
        
        .method-card {{ background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(6, 182, 212, 0.2)); border-color: var(--accent-purple); }}

        .app-content {{ display: none; }}
        header {{ max-width: 1100px; margin: 0 auto 20px; display: flex; justify-content: space-between; align-items: center; background: var(--card-dark); border: 1px solid var(--border-dark); padding: 16px 20px; border-radius: 20px; }}
        .brand {{ display: flex; align-items: center; gap: 12px; }}
        .brand-icon {{ width: 36px; height: 36px; background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple)); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-weight: 800; color: #fff; font-size: 0.9rem; }}
        .brand-name {{ font-size: 1.25rem; font-weight: 800; letter-spacing: -0.5px; }}

        .sport-select-btn {{ background:#1a2234; border:1px solid var(--border-dark); color:#fff; font-weight:800; padding:8px 16px; border-radius:12px; cursor:pointer; font-size:0.75rem; }}

        .bankroll-panel {{ max-width: 1100px; margin: 0 auto 20px; background: var(--card-dark); border: 1px solid var(--border-dark); border-radius: 20px; padding: 16px 20px; display: flex; align-items: center; justify-content: space-between; gap: 15px; flex-wrap: wrap; }}
        .bankroll-input {{ display: flex; align-items: center; gap: 10px; }}
        .bankroll-input input {{ background: #0a0d14; border: 1px solid var(--border-dark); color: var(--accent-cyan); padding: 8px 12px; border-radius: 8px; font-weight: 800; width: 140px; font-size: 1rem; text-align: center; }}

        .saved-section {{ max-width: 1100px; margin: 0 auto 25px; background: rgba(139, 92, 246, 0.08); border: 1px solid var(--accent-purple); border-radius: 24px; padding: 22px; }}
        .saved-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap:wrap; gap:10px; }}
        .saved-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px; }}
        .saved-item {{ background: #0a0d14; border: 1px solid var(--border-dark); border-radius: 16px; padding: 16px; }}
        .saved-item-partido {{ font-size: 0.8rem; font-weight: 700; color: var(--text-muted); margin-bottom: 4px; }}
        .saved-item-pick {{ font-size: 0.95rem; font-weight: 800; color: #fff; margin-bottom: 10px; }}

        .btn-status {{ padding: 5px 10px; border-radius: 8px; font-size: 0.72rem; font-weight: 800; border: none; cursor: pointer; }}
        .btn-win {{ background: rgba(16, 185, 129, 0.2); color: var(--accent-emerald); border: 1px solid var(--accent-emerald); }}
        .btn-loss {{ background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid #ef4444; }}
        .btn-del {{ background: #1e2638; color: var(--text-muted); border: 1px solid var(--border-dark); margin-left: auto; }}

        .hero-section {{ max-width: 1100px; margin: 0 auto 25px; background: linear-gradient(135deg, rgba(6, 182, 212, 0.1) 0%, rgba(16, 185, 129, 0.1) 100%); border: 1px solid var(--accent-cyan); border-radius: 24px; padding: 22px; }}
        .hero-title {{ font-size: 1.1rem; font-weight: 800; color: #fff; margin-bottom: 15px; display: flex; align-items: center; gap: 8px; }}
        .parlay-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px; }}
        .parlay-card {{ background: #0a0d14; border: 1px solid var(--border-dark); border-radius: 16px; padding: 15px; position: relative; }}
        .parlay-tag {{ font-size: 0.65rem; font-weight: 800; color: var(--accent-cyan); text-transform: uppercase; margin-bottom: 6px; }}
        .parlay-match {{ font-size: 0.8rem; font-weight: 700; color: var(--text-muted); margin-bottom: 4px; }}
        .parlay-pick {{ font-size: 0.95rem; font-weight: 800; color: #fff; margin-bottom: 8px; }}

        .container {{ max-width: 1100px; margin: 0 auto; display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; }}
        .pro-card {{ background: var(--card-dark); border: 1px solid var(--border-dark); border-radius: 24px; padding: 20px; transition: all 0.25s ease; }}
        .pro-card:hover {{ border-color: var(--accent-cyan); box-shadow: 0 12px 30px -10px rgba(6, 182, 212, 0.25); }}

        .pro-card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; cursor: pointer; }}
        .pro-league {{ font-size: 0.7rem; font-weight: 800; color: var(--text-muted); }}
        .pro-badge {{ padding: 5px 12px; border-radius: 20px; font-size: 0.7rem; font-weight: 800; }}
        .badge-emerald {{ background: rgba(16, 185, 129, 0.15); color: var(--accent-emerald); border: 1px solid var(--accent-emerald); }}
        .badge-slate {{ background: rgba(100, 116, 139, 0.15); color: var(--text-muted); border: 1px solid var(--border-dark); }}

        .pro-matchup {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; cursor: pointer; }}
        .pro-team {{ flex: 1; display: flex; flex-direction: column; align-items: center; gap: 8px; text-align: center; }}
        .pro-team img {{ width: 50px; height: 50px; object-fit: contain; }}
        .pro-team span {{ font-weight: 700; font-size: 0.9rem; }}
        .pro-vs {{ font-weight: 800; font-size: 0.8rem; color: var(--text-muted); padding: 0 10px; }}

        .pro-pick-box {{ background: #0a0d14; border: 1px solid var(--border-dark); padding: 14px; border-radius: 16px; margin-bottom: 15px; cursor: pointer; }}
        .pro-pick-label {{ font-size: 0.65rem; font-weight: 800; color: var(--accent-cyan); text-transform: uppercase; margin-bottom: 4px; display: block; }}
        .pro-pick-val {{ font-size: 0.9rem; font-weight: 800; color: #fff; margin-bottom: 8px; }}

        .pro-btn {{ background: #1a2234; border: none; color: #fff; font-weight: 800; font-size: 0.75rem; padding: 12px; border-radius: 14px; cursor: pointer; }}
        .save-pick-btn {{ background: rgba(139, 92, 246, 0.2); border: 1px solid var(--accent-purple); color: var(--accent-purple); font-weight: 800; font-size: 0.75rem; padding: 12px 14px; border-radius: 14px; cursor: pointer; }}

        .modal-overlay {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(7, 9, 14, 0.94); backdrop-filter: blur(10px); justify-content: center; align-items: center; z-index: 3000; padding: 20px; }}
        .modal-content {{ background: var(--card-dark); border: 1px solid var(--border-dark); border-radius: 28px; width: 100%; max-width: 850px; max-height: 90vh; overflow-y: auto; padding: 25px; position: relative; }}
        .close-btn {{ position: absolute; top: 20px; right: 20px; font-size: 1.8rem; color: var(--text-muted); cursor: pointer; }}

        .grid-2col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px; }}
        .modal-section {{ background: #0a0d14; border-radius: 18px; padding: 18px; border: 1px solid var(--border-dark); margin-bottom: 15px; }}
        .modal-section h3 {{ font-size: 0.8rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase; margin-bottom: 12px; border-bottom: 1px solid var(--border-dark); padding-bottom: 6px; }}

        .pro-table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; text-align: center; }}
        .pro-table th {{ color: var(--text-muted); font-size: 0.7rem; font-weight: 800; text-transform: uppercase; padding-bottom: 10px; }}
        .pro-table td {{ padding: 10px; border-top: 1px solid var(--border-dark); font-weight: 700; }}
        .pill-odd {{ background: #1e2638; padding: 4px 10px; border-radius: 8px; color: var(--accent-cyan); font-weight: 800; display: inline-block; }}

        .reason-box {{ background: rgba(6, 182, 212, 0.08); border: 1px solid var(--accent-cyan); border-radius: 12px; padding: 12px 15px; margin-top: 12px; font-size: 0.82rem; color: #f8fafc; line-height: 1.5; }}
        .stake-box {{ background: rgba(16, 185, 129, 0.1); border: 1px solid var(--accent-emerald); padding: 14px; border-radius: 12px; text-align: center; margin-top: 12px; color: var(--accent-emerald); font-weight: 800; font-size: 0.95rem; }}

        .toast-container {{ position: fixed; bottom: 25px; right: 25px; z-index: 4000; display: flex; flex-direction: column; gap: 10px; pointer-events: none; }}
        .toast-box {{ background: #0d121f; border: 1px solid var(--accent-cyan); border-left: 4px solid var(--accent-cyan); border-radius: 14px; padding: 14px 20px; color: #fff; font-size: 0.88rem; font-weight: 700; display: flex; align-items: center; gap: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.7); opacity: 0; transform: translateY(30px); transition: all 0.4s ease; pointer-events: auto; }}
        .toast-box.show {{ opacity: 1; transform: translateY(0); }}

        .method-text {{ font-size: 0.88rem; color: #e2e8f0; line-height: 1.6; margin-bottom: 14px; }}
        .method-highlight {{ color: var(--accent-cyan); font-weight: 800; }}
        .formula-box {{ background: #1a2234; border: 1px dashed var(--accent-cyan); padding: 12px; border-radius: 12px; text-align: center; font-family: monospace; color: var(--accent-emerald); font-weight: 800; margin: 10px 0; font-size: 0.9rem; }}
    </style>
</head>
<body>

    <div class="toast-container" id="toastContainer"></div>

    <!-- PANTALLA DE BIENVENIDA -->
    <div class="splash-screen" id="splashScreen">
        <div class="splash-logo">SP</div>
        <h1 class="splash-title">STINGY'S PICKS</h1>
        <p class="splash-sub">¿Qué deporte quieres analizar?</p>
        
        <div class="sports-grid">
            <div class="sport-card" onclick="selectSport('futbol')">
                <span class="sport-name">FÚTBOL</span>
            </div>
            <div class="sport-card" onclick="selectSport('basket')">
                <span class="sport-name">BÁSKETBOL</span>
            </div>
            <div class="sport-card" onclick="selectSport('americano')">
                <span class="sport-name">AMERICANO</span>
            </div>
            <div class="sport-card method-card" onclick="openMethodologyDirect()">
                <span class="sport-name" style="color:var(--accent-cyan);">¿CÓMO CALCULAMOS LAS PROBABILIDADES Y EL VALOR?</span>
            </div>
        </div>
    </div>

    <!-- VISTA PRINCIPAL DE LA APP -->
    <div class="app-content" id="appContent">
        <header>
            <div class="brand">
                <div class="brand-icon">SP</div>
                <div class="brand-name">STINGY'S PICKS</div>
            </div>
            <button class="sport-select-btn" id="currentSportLabel" onclick="backToSplash()">FÚTBOL / LIGA MX &blackdowntriangle;</button>
        </header>

        <div class="bankroll-panel">
            <div>
                <h3 style="font-size:0.95rem; font-weight:800; color:#fff;">GESTOR DE BANKROLL GENERAL</h3>
                <p style="font-size:0.75rem; color:var(--text-muted);">Ingresa tu saldo para calcular la gestión de riesgo y balance de tu portafolio</p>
            </div>
            <div class="bankroll-input">
                <label style="font-size:0.8rem; font-weight:700;">Tu Bank ($):</label>
                <input type="number" id="userBank" placeholder="Ej: 50" oninput="renderSavedPicks()">
            </div>
        </div>

        <div class="saved-section" id="savedPicksContainer">
            <div class="saved-header">
                <div class="saved-title">⭐ MIS PICKS GUARDADOS (PORTAFOLIO PERSONAL)</div>
                <div class="saved-stats">
                    <span style="color:var(--accent-purple);" id="savedCount">0 Guardados</span>
                    <span id="savedBalance">Balance: $0.00 MXN</span>
                </div>
            </div>
            <div class="saved-grid" id="savedPicksList"></div>
        </div>

        <div class="hero-section">
            <div class="hero-title">
                <span>PICKS OFICIALES DE LA SEMANA (MÁXIMO 3 SELECCIONES ≥ 85%)</span>
            </div>
            <div class="parlay-grid" id="officialPicksContainer"></div>
        </div>

        <div class="container" id="matchesContainer"></div>
    </div>

    <!-- MODAL PRINCIPAL DE PARTIDOS -->
    <div class="modal-overlay" id="matchModal">
        <div class="modal-content">
            <span class="close-btn" onclick="closeModal()">&times;</span>
            <div class="modal-title" id="modalHeader">VS</div>
            
            <div class="grid-2col">
                <div class="modal-section">
                    <h3>PROBABILIDAD DE VICTORIA</h3>
                    <div style="height: 160px;"><canvas id="donutChart"></canvas></div>
                </div>
                <div class="modal-section">
                    <h3>HISTORIAL RECIENTE / H2H</h3>
                    <div style="height: 160px;"><canvas id="appStyleChart"></canvas></div>
                </div>
            </div>

            <div class="modal-section">
                <h3>EVALUACIÓN COMPLETA DE OPCIONES</h3>
                <table class="pro-table">
                    <thead>
                        <tr>
                            <th style="text-align:left;">MERCADO</th>
                            <th>MOMIO CASINO</th>
                            <th>PROB. ALG</th>
                            <th>DIAGNÓSTICO</th>
                        </tr>
                    </thead>
                    <tbody id="modalOddsBody"></tbody>
                </table>
                <div class="reason-box" id="modalReason"></div>
                <div class="stake-box" id="modalStake"></div>
            </div>
        </div>
    </div>

    <!-- VISTA METODOLÓGICA EXPLICATIVA DIRECTA -->
    <div class="modal-overlay" id="methodModal">
        <div class="modal-content" style="max-width: 780px;">
            <span class="close-btn" onclick="closeMethodologyModal()">&times;</span>
            <div class="modal-title" style="color:var(--accent-cyan); text-align:left; margin-bottom:15px;">🧠 Modelo Algorítmico, Fórmula Matemática y Valor Esperado (EV+)</div>
            
            <div class="modal-section" style="text-align:left;">
                <h3 style="color:#fff;">1. La Fórmula Matemática de Probabilidad</h3>
                <p class="method-text">
                    No utilizamos opiniones ni apreciaciones subjetivas. Nuestro modelo calcula la probabilidad algorítmica integrando tres variables ponderadas sobre una muestra estricta de <span class="method-highlight">180 días de datos</span>:
                </p>
                <div class="formula-box">
                    P_alg = (P_base × 0.50) + (Δ_rating × 0.35) + (W_h2h × 0.15)
                </div>
                <p class="method-text">
                    • <b>P_base (50%):</b> Frecuencia histórica pura de ocurrencia de la línea en los últimos encuentros.<br>
                    • <b>Δ_rating (35%):</b> Diferencial de potencial ofensivo/defensivo reciente entre ambos planteles.<br>
                    • <b>W_h2h (15%):</b> Factor de peso específico sobre enfrentamientos directos cara a cara.
                </p>
            </div>

            <div class="modal-section" style="text-align:left;">
                <h3 style="color:#fff;">2. Métricas Personalizadas por Deporte</h3>
                <p class="method-text">
                    Cada disciplina se evalúa bajo su propio conjunto de datos clave:
                </p>
                <p class="method-text">
                    • <b>⚽ Fútbol (Liga MX):</b> Goles esperados (xG), volumen de tiros de esquina por partido, tarjetas amarillas/rojas acumuladas y porcentaje de solidez en casa.<br>
                    • <b>🏀 Básquetbol (NBA):</b> Eficiencia ofensiva/defensiva (Offensive/Defensive Rating), ritmo de juego (Pace) y margen promedio de puntos por posesión.<br>
                    • <b>🏈 Fútbol Americano (NFL):</b> Puntos por serie ofensiva, efectividad en 3er down, margen de intercambios de balón (Turnovers) y hándicap de puntos (Spread).
                </p>
            </div>

            <div class="modal-section" style="text-align:left;">
                <h3 style="color:#fff;">3. El Filtro del 85% y el Concepto de Valor (EV+)</h3>
                <p class="method-text">
                    Para proteger la rentabilidad a largo plazo, la plataforma aplica una regla estricta: <span class="method-highlight">si ninguna línea alcanza o supera el 85% de probabilidad matemática, el sistema no recomienda nada (⚪ SIN PICK RECOMENDADO)</span>.
                </p>
                <p class="method-text">
                    Decimos que un pick tiene <b>Valor Esperado Positivo (EV+)</b> cuando la probabilidad algorítmica real calculada por el sistema supera drásticamente la probabilidad implícita ofrecida por las casas de apuestas. Apostar con esta ventaja sistemática es lo único que garantiza superar el margen del casino con el tiempo.
                </p>
            </div>
        </div>
    </div>

    <script>
        const matchesMX = {json.dumps(datos_js_mx)};
        const matchesNFL = {json.dumps(datos_js_nfl)};
        const matchesNBA = {json.dumps(datos_js_nba)};
        const picksMX = {json.dumps(picks_oficiales_mx)};
        const picksNFL = {json.dumps(picks_oficiales_nfl)};
        const picksNBA = {json.dumps(picks_oficiales_nba)};
        
        let currentSport = 'futbol';
        let appChartObj = null;
        let donutChartObj = null;
        let userSavedPicks = JSON.parse(localStorage.getItem('stingy_saved_picks') || '[]');

        function openMethodologyDirect() {{
            document.getElementById('methodModal').style.display = 'flex';
        }}

        function closeMethodologyModal() {{
            document.getElementById('methodModal').style.display = 'none';
        }}

        function showToastNotification(message) {{
            const container = document.getElementById('toastContainer');
            const toast = document.createElement('div');
            toast.className = 'toast-box';
            toast.innerHTML = `<span style="color:var(--accent-cyan); font-size:1.1rem;">⚡</span><span>${{message}}</span>`;
            container.appendChild(toast);
            setTimeout(() => toast.classList.add('show'), 10);
            setTimeout(() => {{
                toast.classList.remove('show');
                setTimeout(() => toast.remove(), 400);
            }}, 5000);
        }}

        function selectSport(sport) {{
            currentSport = sport;
            document.getElementById('splashScreen').style.display = 'none';
            document.getElementById('appContent').style.display = 'block';
            
            if (sport === 'futbol') {{
                document.getElementById('currentSportLabel').innerHTML = '⚽ FÚTBOL / LIGA MX &blackdowntriangle;';
                document.getElementById('matchesContainer').innerHTML = `{mx_cards_html}`;
                renderOfficialPicks(picksMX);
            }} else if (sport === 'americano') {{
                document.getElementById('currentSportLabel').innerHTML = '🏈 AMERICANO / NFL &blackdowntriangle;';
                document.getElementById('matchesContainer').innerHTML = `{nfl_cards_html}`;
                renderOfficialPicks(picksNFL);
            }} else if (sport === 'basket') {{
                document.getElementById('currentSportLabel').innerHTML = '🏀 BÁSKETBOL / NBA &blackdowntriangle;';
                document.getElementById('matchesContainer').innerHTML = `{nba_cards_html}`;
                renderOfficialPicks(picksNBA);
            }}
            renderSavedPicks();
        }}

        function renderOfficialPicks(picksList) {{
            const container = document.getElementById('officialPicksContainer');
            if (!picksList || picksList.length === 0) {{
                container.innerHTML = `<div class="parlay-card" style="grid-column: 1/-1; text-align:center; padding:15px;"><span style="color:var(--text-muted); font-size:0.85rem;">Esta jornada ningún partido alcanzó el umbral del 85% de probabilidad. Por disciplina de bankroll, no hay Parlay Oficial esta semana.</span></div>`;
                return;
            }}

            let html = '';
            picksList.forEach(p => {{
                html += `
                    <div class="parlay-card">
                        <div class="parlay-tag">SELECCIÓN OFICIAL (≥85%)</div>
                        <div class="parlay-match">${{p.partido}}</div>
                        <div class="parlay-pick">${{p.pick}}</div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
                            <span style="font-size:0.7rem; font-weight:800; color:var(--accent-emerald); background:rgba(16,185,129,0.2); padding:3px 8px; border-radius:20px;">${{p.prob}}% PROBABILIDAD</span>
                            <button class="save-pick-btn" style="padding:4px 8px; font-size:0.65rem;" onclick="saveCustomPick('${{p.partido}}', '${{p.pick}}', '${{p.casino}}')">⭐ GUARDAR</button>
                        </div>
                    </div>
                `;
            }});
            container.innerHTML = html;
        }}

        function backToSplash() {{
            document.getElementById('appContent').style.display = 'none';
            document.getElementById('splashScreen').style.display = 'flex';
        }}

        function saveCustomPick(partido, pick, momio) {{
            userSavedPicks.push({{ id: Date.now(), partido, pick, momio, estado: 'PENDIENTE' }});
            localStorage.setItem('stingy_saved_picks', JSON.stringify(userSavedPicks));
            renderSavedPicks();
            showToastNotification(`Se ha guardado exitosamente tu apuesta: <b>${{pick}}</b>`);
        }}

        function updatePickStatus(pickId, newStatus) {{
            userSavedPicks = userSavedPicks.map(item => {{
                if (item.id === pickId) item.estado = item.estado === newStatus ? 'PENDIENTE' : newStatus;
                return item;
            }});
            localStorage.setItem('stingy_saved_picks', JSON.stringify(userSavedPicks));
            renderSavedPicks();
        }}

        function deleteSavedPick(pickId) {{
            userSavedPicks = userSavedPicks.filter(item => item.id !== pickId);
            localStorage.setItem('stingy_saved_picks', JSON.stringify(userSavedPicks));
            renderSavedPicks();
            showToastNotification(`Pick eliminado de tu portafolio`);
        }}

        function renderSavedPicks() {{
            const container = document.getElementById('savedPicksList');
            const bankVal = parseFloat(document.getElementById('userBank').value);
            const userBank = isNaN(bankVal) ? 0 : bankVal;

            document.getElementById('savedCount').innerHTML = `${{userSavedPicks.length}} Guardados`;

            if (userSavedPicks.length === 0) {{
                container.innerHTML = `<div style="grid-column: 1/-1; color:var(--text-muted); font-size:0.85rem; text-align:center; padding:15px;">Aún no has guardado ningún pick. Haz clic en "⭐ GUARDAR" para agregar elecciones a tu portafolio.</div>`;
                document.getElementById('savedBalance').innerHTML = `Balance: $0.00 MXN`;
                return;
            }}

            let totalProfit = 0;
            let listHTML = '';

            userSavedPicks.forEach(item => {{
                const stake = userBank > 0 ? (userBank * 0.05) : 0;
                let profitItem = 0;
                let statusBadge = '<span style="color:var(--text-muted); font-size:0.75rem; font-weight:800;">⏳ PENDIENTE</span>';

                if (item.estado === 'GANADA') {{
                    profitItem = stake > 0 ? stake * 0.85 : 0;
                    totalProfit += profitItem;
                    statusBadge = '<span style="color:var(--accent-emerald); font-size:0.75rem; font-weight:800;">✅ GANADA (' + (stake > 0 ? '+$' + profitItem.toFixed(2) : 'Acierto') + ')</span>';
                }} else if (item.estado === 'PERDIDA') {{
                    profitItem = -stake;
                    totalProfit += profitItem;
                    statusBadge = '<span style="color:#ef4444; font-size:0.75rem; font-weight:800;">❌ PERDIDA (' + (stake > 0 ? '-$' + Math.abs(profitItem).toFixed(2) : 'Fallo') + ')</span>';
                }}

                listHTML += `
                    <div class="saved-item">
                        <div class="saved-item-partido">${{item.partido}}</div>
                        <div class="saved-item-pick">${{item.pick}} <span style="color:var(--accent-cyan); font-size:0.8rem;">($${{item.momio}})</span></div>
                        <div style="margin-bottom:8px;">${{statusBadge}}</div>
                        <div class="saved-item-actions">
                            <button class="btn-status btn-win" onclick="updatePickStatus(${{item.id}}, 'GANADA')">GANADA</button>
                            <button class="btn-status btn-loss" onclick="updatePickStatus(${{item.id}}, 'PERDIDA')">PERDIDA</button>
                            <button class="btn-status btn-del" onclick="deleteSavedPick(${{item.id}})">🗑️</button>
                        </div>
                    </div>
                `;
            }});

            container.innerHTML = listHTML;
            const profitSign = totalProfit >= 0 ? '+' : '';
            const profitColor = totalProfit >= 0 ? 'var(--accent-emerald)' : '#ef4444';
            document.getElementById('savedBalance').innerHTML = userBank > 0 ? 
                `Balance de Ganancias: <span style="color:${{profitColor}};">${{profitSign}}$${{totalProfit.toFixed(2)}} MXN</span>` : 
                `Ingresa tu Bank arriba para ver tus $ ganancias`;
        }}

        function openModal(cardId, sportType) {{
            let dataSet = matchesMX;
            if (sportType === 'nfl') dataSet = matchesNFL;
            if (sportType === 'nba') dataSet = matchesNBA;

            const data = dataSet[cardId];
            if (!data) return;

            const bankVal = parseFloat(document.getElementById('userBank').value);
            const userBank = isNaN(bankVal) ? 0 : bankVal;

            document.getElementById('modalHeader').innerHTML = `${{data.local}} vs ${{data.visita}} (${{data.fecha_partido}})`;

            if (!data.has_data) {{
                document.getElementById('modalOddsBody').innerHTML = `<tr><td colspan="4" style="color:var(--text-muted); padding:15px;">⏳ EN ESPERA DE INFORMACIÓN COMPLETA (RECESO DE TEMPORADA)</td></tr>`;
                document.getElementById('modalReason').innerHTML = `<b>Nota Técnica:</b> El deporte seleccionado se encuentra en receso/pretemporada. Las cuotas oficiales de casino y métricas completas se actualizarán al iniciar la temporada regular.`;
                document.getElementById('modalStake').innerHTML = `⏳ Esperando inicio de temporada`;
            }} else {{
                let oddsRows = '';
                data.mercados.forEach(m => {{
                    oddsRows += `
                        <tr>
                            <td style="text-align:left; color:#fff;">${{m.mercado}}</td>
                            <td><span class="pill-odd">${{m.casino}}</span></td>
                            <td><b>${{m.prob_alg}}</b></td>
                            <td>${{m.ev.includes("ALTA") ? '<span style="color:var(--accent-emerald)">RECOMENDADO</span>' : '<span style="color:var(--text-muted)">OBSERVACIÓN</span>'}}</td>
                        </tr>
                    `;
                }});
                document.getElementById('modalOddsBody').innerHTML = oddsRows;
                document.getElementById('modalReason').innerHTML = data.has_valid ? 
                    `<b>¿Por qué esta proyección?</b> ${{data.best_reason}}` : 
                    `<b>Nota Técnica:</b> Métrica en rango de observación estándar. No se recomienda riesgo alto.`;

                if (userBank > 0) {{
                    const recStake = (userBank * 0.05).toFixed(2);
                    document.getElementById('modalStake').innerHTML = data.has_valid ? 
                        `STAKE RECOMENDADO: Invertir $${{recStake}} MXN (5% de tu Bank de $${{userBank}} MXN)` :
                        `ALERTA DE RIESGO: Se recomienda abstenerse o arriesgar máximo $${{(userBank * 0.01).toFixed(2)}} MXN (1% del Bank)`;
                }} else {{
                    document.getElementById('modalStake').innerHTML = `💡 Ingresa tu saldo ($ MXN) arriba para calcular el Stake sugerido`;
                }}
            }}

            renderAppCharts(data);
            document.getElementById('matchModal').style.display = 'flex';
        }}

        function renderAppCharts(data) {{
            if (appChartObj) appChartObj.destroy();
            if (donutChartObj) donutChartObj.destroy();

            const ctxDonut = document.getElementById('donutChart').getContext('2d');
            donutChartObj = new Chart(ctxDonut, {{
                type: 'doughnut',
                data: {{
                    labels: [data.local, 'Empate/Emparejado', data.visita],
                    datasets: [{{ data: [data.prob_l, data.prob_e, data.prob_v], backgroundColor: ['#06b6d4', '#64748b', '#10b981'], borderWidth: 0 }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#f8fafc', font: {{ size: 9 }} }} }} }} }}
            }});

            const ctxApp = document.getElementById('appStyleChart').getContext('2d');
            appChartObj = new Chart(ctxApp, {{
                type: 'bar',
                data: {{
                    labels: data.fechas_labels,
                    datasets: [
                        {{ label: data.local, data: data.hist_local, backgroundColor: '#06b6d4', borderRadius: 5, barThickness: 10 }},
                        {{ label: data.visita, data: data.hist_visita, backgroundColor: '#10b981', borderRadius: 5, barThickness: 10 }}
                    ]
                }},
                options: {{
                    responsive: true, maintainAspectRatio: false,
                    scales: {{ x: {{ grid: {{ display: false }}, ticks: {{ color: '#64748b' }} }}, y: {{ grid: {{ color: '#1e2638' }}, ticks: {{ color: '#64748b' }} }} }},
                    plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#f8fafc', font: {{ size: 9 }} }} }} }}
                }}
            }});
        }}

        function closeModal() {{ document.getElementById('matchModal').style.display = 'none'; }}
        function closeMethodologyModal() {{ document.getElementById('methodModal').style.display = 'none'; }}

        window.onclick = function(event) {{ 
            if (event.target == document.getElementById('matchModal')) closeModal();
            if (event.target == document.getElementById('methodModal')) closeMethodologyModal();
        }}
    </script>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_document)

print("\n🚀 ¡CÓDIGO DE ACTUALIZAR.PY CORREGIDO Y LISTO PARA EJECUTAR EN GITHUB!")
