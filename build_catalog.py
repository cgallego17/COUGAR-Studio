"""Build a standalone browser catalog using actual segment packets. No USB I/O."""
import json
from pathlib import Path
from preview_personalization import SEGMENTS
from segment_fonts import STYLES, AMBIGUOUS
from segment_scenes import DIGIT_LAYOUT, SCENE_LABELS, DURATIONS, scene_packet, read_masks
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from display_protocol import load

ROOT = Path(__file__).resolve().parent


def build():
    blob, _, _ = load()
    empty = b'\x03\x00' + bytes(62)
    data = {'layout': DIGIT_LAYOUT, 'segments': SEGMENTS, 'fonts': STYLES, 'ambiguous': AMBIGUOUS, 'scenes': {}}
    for scene, label in SCENE_LABELS.items():
        frames = [read_masks(blob, scene_packet(blob, empty, scene, tick/5))
                  for tick in range(DURATIONS[scene]*5)]
        data['scenes'][scene] = {'label': label, 'frames': frames}
    html = TEMPLATE.replace('__CATALOG_DATA__', json.dumps(data, ensure_ascii=False)).replace('__SCENE_COUNT__', str(len(SCENE_LABELS)))
    path = ROOT / 'catalogo-animaciones-y-letras.html'
    path.write_text(html, encoding='utf-8')
    return path


TEMPLATE = r'''<!doctype html>
<html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>COUGAR · catálogo de segmentos</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#101216;color:#f3f4f6;font:16px system-ui,Segoe UI,sans-serif}
main{max-width:1100px;margin:auto;padding:28px}h1{font-size:29px;margin:0 0 10px}h2{font-size:19px}
p{line-height:1.55;color:#b4bdca}.badge{display:inline-block;background:#26362e;color:#a8e5bc;padding:6px 12px;border-radius:20px;font-size:13px}
.layout{display:grid;grid-template-columns:1fr 1fr;gap:25px;margin-top:25px}.card{background:#1b2027;border:1px solid #343c48;border-radius:18px;padding:23px}
button,select,input{font:inherit;color:#f3f4f6;background:#292f39;border:1px solid #566171;border-radius:8px;padding:10px}button{cursor:pointer}button:hover{border-color:#ff9a55}
.buttons{display:flex;gap:8px;flex-wrap:wrap}button.active{background:#96461b;border-color:#ff9a55}.field{display:grid;gap:9px;margin:20px 0}input[type=text]{width:100%;text-transform:none}
#display{width:100%;max-height:440px}#status{color:#ffc08d;min-height:28px}#warnings{color:#ffb3a8;min-height:50px;font-size:14px}
.letters{display:grid;grid-template-columns:repeat(auto-fit,minmax(70px,1fr));gap:9px}.letter{background:#101216;padding:10px;border-radius:8px;text-align:center}.letter svg{height:75px;width:50px}.letter b{display:block;margin-top:5px}
.small{font-size:14px}.wide{grid-column:1/-1}label{color:#d6dce5}[hidden]{display:none!important}@media(max-width:760px){.layout{grid-template-columns:1fr}main{padding:17px}}
</style>
<main><span class="badge">Simulación local · no envía nada al dispositivo</span>
<h1 style="margin-top:18px">Escenas y letras para tu COUGAR</h1>
<p>Vista basada en los diez dígitos y en los paquetes de segmentos del proyecto. La distribución aproxima la foto; no es una medición ni una resolución en píxeles.</p>
<div class="layout"><section class="card"><svg id="display" viewBox="0 0 440 420" role="img" aria-label="Vista previa de los diez dígitos de la pantalla"></svg>
<p id="status" aria-live="polite"></p><p class="small">Las zonas vacías y los segmentos apagados conservan su posición física. El logo y las unidades se omiten en las escenas, tal como permite el borrado ya confirmado.</p></section>
<section class="card"><div class="buttons"><button id="animations" class="active">Animaciones</button><button id="letterMode">Letras y números</button></div>
<div id="animationControls"><h2>__SCENE_COUNT__ escenas de segmentos</h2><div id="sceneButtons" class="buttons"></div>
<div class="field"><label for="speed">Velocidad de la vista previa</label><input id="speed" type="range" min="0.4" max="1.6" value="1" step="0.1"></div>
<button id="pause">Pausar</button><p class="small">Órbita, radar, ondas circulares, espiral, doble órbita e iris se calculan alrededor del centro de la cara circular. Se encienden los segmentos más próximos al recorrido: no crean píxeles en los huecos. Las barras son decorativas y no usan audio.</p></div>
<div id="fontControls" hidden><h2>Variantes de los mismos segmentos</h2><div class="field"><label for="font">Estilo</label><select id="font"></select></div>
<div class="field"><label for="text">Texto de prueba (hasta 10 posiciones: 3 / 4 / 3)</label><input id="text" maxlength="10" value="CPU GPU123" spellcheck="false"></div>
<p id="warnings" aria-live="polite"></p><p class="small">Clásico: trazos habituales. Compacto: variantes parecidas a minúsculas. Números alternativos: otras formas de 1, 6, 7 y 9. La geometría, el grosor y la separación siguen siendo los del cristal.</p></div>
</section><section class="card wide"><h2>Letras y números que puedes comparar</h2><p id="ambiguity" class="small"></p><div id="glyphs" class="letters"></div></section>
<section class="card wide"><h2>Qué admite la pantalla que hemos probado</h2><p>Diez dígitos de siete segmentos: 128 combinaciones por dígito, muchas sin significado. Podemos hacer cuentas, movimiento, barridos, escritura progresiva, barras, patrones y letras aproximadas; apagar todo y después recuperar la presentación de CPU o GPU.</p>
<p>No hay una matriz de píxeles demostrada para cargar Arial, Roboto, fotos, emoji o sprites detallados. M, W, K, Q, X, tildes y ñ no tienen una representación clara con estos siete segmentos y no se incluyen. Cambiar una variante modifica qué barras se encienden, sin cambiar su forma física.</p>
<p class="small">El catálogo no cambia el ciclo que está funcionando. Para el dispositivo siguen usándose únicamente cuadros HID 03, sin grabar firmware.</p>
<h2>Referencias consultadas para los nuevos diseños</h2><p class="small">Ideas adaptadas con código propio a la distribución 3 / 4 / 3 del COUGAR:
<a style="color:#ffc08d" href="https://liksu.github.io/7SegmentsSnake/">Snake para siete segmentos, de Liksu</a>;
<a style="color:#ffc08d" href="https://github.com/jvisualschool/ESP8266-7segment">colección de efectos de jvisualschool</a>;
<a style="color:#ffc08d" href="https://bynirav.com/seven-segment/">editor de animaciones de Nirav</a>.
Las vistas y el hardware de esos proyectos son diferentes; los efectos de este catálogo se calculan con nuestro mapa de segmentos.</p></section></div></main>
<script>
const data=__CATALOG_DATA__;
const $=id=>document.getElementById(id);
const layout=data.layout;
const polygon=(points,on)=>`<polygon points="${points}" fill="${on?'#f4f6fa':'#1b2027'}"/>`;
function digit(mask){return data.segments.map((points,bit)=>polygon(points,mask&(1<<bit))).join('')}
function display(masks){$('display').innerHTML='<circle cx="220" cy="210" r="204" fill="#080a0d" stroke="#414b59" stroke-width="4"/>'+layout.map(([x,y,s],i)=>`<g transform="translate(${x},${y}) scale(${s})">${digit(masks[i]||0)}</g>`).join('')}
let scene='snake_all',mode='animation',paused=false,elapsed=0,last=performance.now();
function chooseScene(name){scene=name;elapsed=0;document.querySelectorAll('[data-scene]').forEach(b=>b.classList.toggle('active',b.dataset.scene===name));renderAnimation()}
for(const [name,item] of Object.entries(data.scenes)){const button=document.createElement('button');button.textContent=item.label;button.dataset.scene=name;button.onclick=()=>chooseScene(name);$('sceneButtons').append(button)}
for(const name of Object.keys(data.fonts)){const option=document.createElement('option');option.textContent=name;option.value=name;$('font').append(option)}
function glyphs(){const table=data.fonts[$('font').value];$('glyphs').replaceChildren();for(const ch of '0123456789ABCDEFGHIJLNOPRSTUY-_'){if(!(ch in table))continue;const tile=document.createElement('div');tile.className='letter';tile.innerHTML=`<svg viewBox="0 0 68 114" aria-hidden="true">${digit(table[ch])}</svg>`;const label=document.createElement('b');label.textContent=ch;tile.append(label);$('glyphs').append(tile)}}
function renderText(){const table=data.fonts[$('font').value],text=$('text').value.padEnd(10,' '),missing=[...new Set([...text].filter(ch=>!(ch in table)))];display([...text].map(ch=>table[ch]||0));$('warnings').textContent=missing.length?'Sin representación: '+missing.join(', ')+'. Esas posiciones se dejan vacías.':'Todos los caracteres tienen una aproximación por segmentos.';$('status').textContent='Estilo: '+$('font').value+' · distribución 3 / 4 / 3'}
function renderAnimation(){const item=data.scenes[scene],index=Math.floor(elapsed*5)%item.frames.length;display(item.frames[index]);$('status').textContent=item.label+' · solo segmentos · '+(paused?'pausado':'reproduciendo')}
function switchMode(next){mode=next;$('animationControls').hidden=mode!=='animation';$('fontControls').hidden=mode!=='font';$('animations').classList.toggle('active',mode==='animation');$('letterMode').classList.toggle('active',mode==='font');if(mode==='font')renderText();else renderAnimation()}
$('animations').onclick=()=>switchMode('animation');$('letterMode').onclick=()=>switchMode('font');$('font').onchange=()=>{glyphs();if(mode==='font')renderText()};$('text').oninput=renderText;
$('pause').onclick=()=>{paused=!paused;$('pause').textContent=paused?'Reanudar':'Pausar';renderAnimation()};$('ambiguity').textContent=data.ambiguous;
function loop(now){const delta=Math.min((now-last)/1000,.2);last=now;if(mode==='animation'){if(!paused)elapsed+=delta*Number($('speed').value);renderAnimation()}requestAnimationFrame(loop)}
glyphs();chooseScene(scene);requestAnimationFrame(loop);
</script></html>'''

if __name__ == '__main__':
    print(build())
