"""Windows manager for the proven COUGAR segment protocol."""
import argparse
import ctypes as c
from ctypes import wintypes as w
from datetime import datetime
import json
import os
from pathlib import Path
import queue
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

SOURCE = Path(__file__).resolve().parent
sys.path.insert(0, str(SOURCE / 'usb-investigation'))
from cougar_studio_core import Profile, Player, load_profile, save_profile
from sensor_client import SensorClient
from app_version import VERSION, REPOSITORY
from studio_updates import check_latest, download_update
from display_protocol import HidWriter, LOGO_BIT, numeric_packet, missing_temperature_packet, load
from segment_scenes import DIGIT_LAYOUT, INTERNET_SCENES, CIRCULAR_SCENES, SCENE_LABELS, scene_packet, read_masks
from preview_personalization import SEGMENTS
from gif_segments import load_gif
from display_ownership import DisplayOwnership

ROOT = Path(sys.executable).parent if getattr(sys, 'frozen', False) else SOURCE
ASSETS = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else SOURCE / 'assets'
DATA = Path(os.environ.get('COUGAR_STUDIO_DATA_DIR') or str(Path(os.environ.get('LOCALAPPDATA', str(ROOT))) / 'COUGAR Studio'))
BG, CARD, INK, MUTED, ACCENT = '#10141b', '#1c2430', '#f4f6fa', '#a4b2c5', '#ff9652'


def run(preview=False, smoke=False, screenshot=None, initial='sensors', gif_demo=False):
    if sys.platform == 'win32':
        c.windll.shell32.SetCurrentProcessExplicitAppUserModelID('cgallego17.COUGARStudio')
    root = tk.Tk()
    root.title('COUGAR Studio')
    root.iconbitmap(default=str(ASSETS / 'studio.ico'))
    root.geometry('1120x780')
    root.minsize(1060, 760)
    root.configure(bg=BG)
    mutex, kernel = None, None
    if not preview:
        kernel = c.WinDLL('kernel32', use_last_error=True)
        kernel.CreateMutexW.argtypes = [c.c_void_p, w.BOOL, w.LPCWSTR]
        kernel.CreateMutexW.restype = w.HANDLE
        kernel.CloseHandle.argtypes = [w.HANDLE]
        mutex = kernel.CreateMutexW(None, False, 'Local\\COUGARPersonalizationSegments')
        if not mutex:
            root.destroy()
            raise c.WinError(c.get_last_error())
        if c.get_last_error() == 183:
            user = c.WinDLL('user32', use_last_error=True)
            user.FindWindowW.argtypes = [w.LPCWSTR, w.LPCWSTR]
            user.FindWindowW.restype = w.HWND
            user.ShowWindow.argtypes = [w.HWND, c.c_int]
            user.SetForegroundWindow.argtypes = [w.HWND]
            existing = user.FindWindowW(None, 'COUGAR Studio')
            if existing:
                user.ShowWindow(existing, 9)
                user.SetForegroundWindow(existing)
            else:
                messagebox.showinfo('Pantalla en uso', 'Cierra la ventana anterior de escenas para usar COUGAR Studio.', parent=root)
            kernel.CloseHandle(mutex)
            root.destroy()
            return
    profile_path = DATA / 'cougar-studio.json'
    profile_error = ''
    try:
        profile = load_profile(profile_path)
    except (OSError, ValueError, TypeError) as exc:
        profile, profile_error = Profile(), str(exc)
    stop, commands, events = threading.Event(), queue.Queue(), queue.Queue()
    ui = {'profile': profile, 'log': [], 'values': [None]*6, 'closing': False,
          'last_packet': None, 'usb': 'Simulación' if preview else 'Conectando…', 'gif': None, 'gif_path': None}
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('TNotebook', background=BG, borderwidth=0)
    style.configure('TNotebook.Tab', background=CARD, foreground=MUTED, padding=(16, 10), font=('Segoe UI', 10))
    style.map('TNotebook.Tab', background=[('selected', '#344257')], foreground=[('selected', INK)])
    style.configure('TCombobox', fieldbackground=CARD, foreground=INK, background=CARD)
    style.map('TCombobox', fieldbackground=[('readonly', CARD)], foreground=[('readonly', INK)],
              selectbackground=[('readonly', CARD)], selectforeground=[('readonly', INK)])

    def label(parent, text='', size=11, color=INK, **kw):
        return tk.Label(parent, text=text, bg=parent.cget('bg'), fg=color, font=('Segoe UI', size), **kw)

    def button(parent, text, command, primary=False):
        return tk.Button(parent, text=text, command=command, bg=ACCENT if primary else '#344257',
                         fg=BG if primary else INK, activebackground='#d97e43', activeforeground=BG,
                         relief='flat', padx=13, pady=8, font=('Segoe UI', 10), cursor='hand2')

    def select(mode):
        commands.put(('select', mode))

    header = tk.Frame(root, bg=BG, padx=24, pady=18)
    header.pack(fill='x')
    label(header, 'COUGAR', 24, ACCENT).pack(side='left')
    label(header, '  STUDIO', 24).pack(side='left')
    label(header, 'SIMULACIÓN · SIN USB' if preview else 'POSEIDON VISTEK · CONTROL LOCAL', 10, MUTED).pack(side='right')
    content = tk.Frame(root, bg=BG)
    content.pack(fill='both', expand=True, padx=24)
    left = tk.Frame(content, bg=CARD, padx=16, pady=8)
    left.pack(side='left', fill='y', padx=(0, 20))
    right = tk.Frame(content, bg=BG)
    right.pack(side='left', fill='both', expand=True)
    label(left, 'PANTALLA', 10, MUTED).pack(anchor='w')
    canvas = tk.Canvas(left, width=310, height=300, bg=CARD, highlightthickness=0)
    canvas.pack(pady=8)
    scale = .7
    canvas.create_oval(12*scale, 2*scale, 428*scale, 418*scale, fill='#080a0d', outline='#465367', width=3)
    logo = canvas.create_text(220*scale, 65*scale, text='COUGAR', fill=INK, font=('Segoe UI', 15, 'bold italic'))
    units = [canvas.create_text(x*scale, y*scale, text=text, fill=INK, font=('Segoe UI', size, 'bold'))
             for x, y, text, size in [(355, 140, '°C', 15), (338, 275, 'RPM', 10), (312, 344, 'W', 11)]]
    decimal = canvas.create_oval(248*scale, 218*scale, 256*scale, 226*scale, fill=INK, outline='')
    power_dot = canvas.create_oval(238*scale, 366*scale, 242*scale, 370*scale, fill=INK, outline='')
    polygons = []
    for x, y, digit_scale in DIGIT_LAYOUT:
        group = []
        for polygon in SEGMENTS:
            raw = [float(value) for pair in polygon.split() for value in pair.split(',')]
            points = [(value*digit_scale+(x if i % 2 == 0 else y))*scale for i, value in enumerate(raw)]
            group.append(canvas.create_polygon(points, fill='#1b2027', outline=''))
        polygons.append(group)
    current = label(left, 'Preparando…', 13, ACCENT, wraplength=390)
    current.pack(fill='x', pady=(2, 8))
    transport = label(left, 'Conectando…', 10, MUTED, wraplength=385, justify='left')
    transport.pack(fill='x')
    sensor_labels = []
    sensor_frame = tk.Frame(left, bg=CARD)
    sensor_frame.pack(fill='x', pady=8)
    for i, title in enumerate(['CPU °C', 'GPU °C', 'CPU FAN', 'CPU W', 'CPU %', 'GPU %']):
        frame = tk.Frame(sensor_frame, bg=CARD)
        frame.grid(row=i//3, column=i%3, sticky='w', padx=12, pady=5)
        label(frame, title, 9, MUTED).pack(anchor='w')
        value = label(frame, '—', 16)
        value.pack(anchor='w')
        sensor_labels.append(value)
    tabs = ttk.Notebook(right)
    tabs.pack(fill='both', expand=True)
    designs, gif_tab, cycle, settings, diagnosis, updates = [tk.Frame(tabs, bg=BG, padx=14, pady=14) for _ in range(6)]
    for pane, title in [(designs, 'Diseños'), (gif_tab, 'GIF'), (cycle, 'Mi ciclo'), (settings, 'Ajustes'), (diagnosis, 'Diagnóstico'), (updates, 'Actualizar')]:
        tabs.add(pane, text=title)
    label(designs, '23 diseños para tu pantalla', 17).pack(anchor='w')
    label(designs, 'Elige un efecto. Al terminar volverá a los datos de CPU.', 10, MUTED, wraplength=510).pack(anchor='w', pady=(6, 12))
    scene_list = tk.Listbox(designs, bg=CARD, fg=INK, selectbackground='#a85d2b', selectforeground=INK,
                           font=('Segoe UI', 11), relief='flat', height=12, exportselection=False)
    scene_scroll = ttk.Scrollbar(designs, orient='vertical', command=scene_list.yview)
    scene_scroll.pack(side='right', fill='y')
    scene_list.configure(yscrollcommand=scene_scroll.set)
    scene_list.pack(fill='both', expand=True)
    all_scenes = list(SCENE_LABELS)
    for scene in all_scenes:
        scene_list.insert('end', SCENE_LABELS[scene])
    scene_list.selection_set(0)

    def selected_scene():
        return all_scenes[scene_list.curselection()[0]] if scene_list.curselection() else all_scenes[0]

    scene_list.bind('<Double-Button-1>', lambda event: select(selected_scene()))
    row = tk.Frame(designs, bg=BG)
    row.pack(fill='x', pady=12)
    button(row, 'Mostrar diseño', lambda: select(selected_scene()), True).pack(side='left')
    button(row, 'Añadir a mi ciclo', lambda: add_scene()).pack(side='left', padx=8)
    quick = tk.Frame(designs, bg=BG)
    quick.pack(fill='x')
    for caption, mode in [('CPU', 'sensors'), ('GPU', 'gpu'), ('Apagar', 'blank'), ('SoulKilleR', 'name')]:
        button(quick, caption, lambda mode=mode: select(mode)).pack(side='left', padx=(0, 7))
    label(gif_tab, 'GIF sobre los segmentos', 17).pack(anchor='w')
    label(gif_tab, 'Como luces de un teclado: el brillo del GIF enciende las barras cercanas.\n'
          'Prueba siluetas claras sobre fondo negro; los detalles pequeños se pierden.',
          10, MUTED, justify='left', wraplength=570).pack(anchor='w', pady=(6, 10))
    gif_status = label(gif_tab, 'Importa un GIF o carga la demostración incluida.', 10, MUTED,
                       wraplength=560, justify='left')
    gif_status.pack(anchor='w', pady=6)
    gif_thumbnail = label(gif_tab, 'El original aparecerá aquí', 10, MUTED)
    gif_thumbnail.pack(anchor='w', pady=5)
    gif_threshold = tk.IntVar(value=64)
    gif_invert = tk.BooleanVar(value=False)
    gif_region = tk.StringVar(value='Dígitos')
    gif_fit = tk.StringVar(value='Ajustar completo')
    gif_seconds = tk.StringVar(value='12')
    gif_busy = {'value': False}

    def convert_gif(path=None, autoplay=None):
        if gif_busy['value']:
            return
        if path is None:
            path = filedialog.askopenfilename(parent=root, title='Importar GIF', filetypes=[('GIF animado', '*.gif')])
        if not path:
            return
        try:
            options = dict(threshold=gif_threshold.get(), invert=gif_invert.get(),
                           region='digits' if gif_region.get() == 'Dígitos' else 'circle',
                           fit='contain' if gif_fit.get() == 'Ajustar completo' else 'cover')
            if not 1 <= options['threshold'] <= 254:
                raise ValueError('Usa un umbral entre 1 y 254.')
        except (ValueError, tk.TclError) as exc:
            messagebox.showerror('Revisa los ajustes del GIF', str(exc), parent=root)
            return
        gif_busy['value'] = True
        gif_status.configure(text='Convirtiendo cuadros a segmentos…')
        for control in gif_controls:
            control.configure(state='disabled')
        def task():
            try:
                animation = load_gif(path, **options)
                events.put(('gif_loaded', animation, str(path), autoplay))
            except Exception as exc:
                events.put(('gif_error', str(exc)))
        threading.Thread(target=task, daemon=True).start()

    def play_gif(live=False):
        if not ui['gif'] or gif_busy['value']:
            return
        try:
            seconds = float(gif_seconds.get().replace(',', '.'))
            if not 2 <= seconds <= 60:
                raise ValueError('Usa una duración entre 2 y 60 segundos.')
        except ValueError as exc:
            messagebox.showerror('Duración del GIF', str(exc), parent=root)
            return
        commands.put(('gif', (ui['gif'], seconds, live)))
        tabs.select(gif_tab)
        gif_status.configure(text=('Vista previa local' if preview else ('Mostrando en el dispositivo' if live else 'Solo vista previa; el dispositivo sigue mostrando CPU'))+
                             f' · {seconds:g} s; después vuelve a CPU.')

    row = tk.Frame(gif_tab, bg=BG)
    row.pack(fill='x', pady=8)
    gif_import = button(row, 'Importar GIF…', convert_gif, True)
    gif_import.pack(side='left')
    gif_demo_button = button(row, 'Cargar demo', lambda: convert_gif(ASSETS/'demo-segmentos.gif'))
    gif_demo_button.pack(side='left', padx=8)
    row = tk.Frame(gif_tab, bg=BG)
    row.pack(fill='x', pady=5)
    label(row, 'Umbral de luz (menor = más barras)', 10).pack(side='left', padx=(0, 10))
    ttk.Spinbox(row, from_=1, to=254, textvariable=gif_threshold, width=6).pack(side='left')
    tk.Checkbutton(gif_tab, text='Invertir claros y oscuros', variable=gif_invert, bg=BG,
                   fg=INK, selectcolor=CARD, activebackground=BG, activeforeground=INK).pack(anchor='w')
    row = tk.Frame(gif_tab, bg=BG)
    row.pack(fill='x', pady=8)
    ttk.Combobox(row, textvariable=gif_region, values=['Dígitos', 'Cara circular'], state='readonly', width=15).pack(side='left')
    ttk.Combobox(row, textvariable=gif_fit, values=['Ajustar completo', 'Llenar y recortar'], state='readonly', width=19).pack(side='left', padx=8)
    gif_apply = button(gif_tab, 'Aplicar ajustes al GIF', lambda: convert_gif(ui['gif_path']) if ui['gif_path'] else None)
    gif_apply.pack(anchor='w', pady=2)
    row = tk.Frame(gif_tab, bg=BG)
    row.pack(fill='x', pady=2)
    label(row, 'Mostrar durante (s)', 10).pack(side='left', padx=(0, 10))
    ttk.Spinbox(row, from_=2, to=60, textvariable=gif_seconds, width=6).pack(side='left')
    row = tk.Frame(gif_tab, bg=BG)
    row.pack(fill='x', pady=8)
    gif_preview = button(row, 'Vista previa', play_gif)
    gif_preview.pack(side='left')
    gif_show = button(row, 'Mostrar en pantalla', lambda: play_gif(True), True)
    gif_show.pack(side='left', padx=8)
    button(row, 'Volver a CPU', lambda: select('sensors')).pack(side='left')
    row.pack_configure(pady=3)
    label(gif_tab, 'Hasta 20 MB y 60 s · adaptación a 10 cuadros/s · no conserva colores.\n'
          'El GIF cargado y sus ajustes se usan en esta sesión.', 9, MUTED, justify='left').pack(anchor='w', pady=6)
    gif_controls = [gif_import, gif_demo_button, gif_apply, gif_preview, gif_show]
    for control in (gif_apply, gif_preview, gif_show):
        control.configure(state='disabled')
    label(cycle, 'Tu secuencia', 17).pack(anchor='w')
    label(cycle, 'Cada diseño se alterna con CPU y GPU. Puedes ordenar la lista.', 10, MUTED, wraplength=510).pack(anchor='w', pady=(6, 12))
    playlist = tk.Listbox(cycle, bg=CARD, fg=INK, selectbackground='#a85d2b', font=('Segoe UI', 11),
                          relief='flat', height=12, exportselection=False)
    playlist.pack(fill='both', expand=True)
    working_scenes = list(profile.scenes)

    def refresh_playlist(index=0):
        playlist.delete(0, 'end')
        for i, scene in enumerate(working_scenes):
            playlist.insert('end', f'{i+1:02}  {SCENE_LABELS[scene]}')
        if working_scenes:
            playlist.selection_set(min(index, len(working_scenes)-1))

    def add_scene():
        scene = selected_scene()
        if scene not in working_scenes:
            working_scenes.append(scene)
            refresh_playlist(len(working_scenes)-1)
        tabs.select(cycle)

    def move_scene(delta):
        if not playlist.curselection():
            return
        index = playlist.curselection()[0]
        destination = index+delta
        if 0 <= destination < len(working_scenes):
            working_scenes[index], working_scenes[destination] = working_scenes[destination], working_scenes[index]
            refresh_playlist(destination)

    def remove_scene():
        if playlist.curselection():
            working_scenes.pop(playlist.curselection()[0])
            refresh_playlist()

    row = tk.Frame(cycle, bg=BG)
    row.pack(fill='x', pady=10)
    for text, action in [('↑ Subir', lambda: move_scene(-1)), ('↓ Bajar', lambda: move_scene(1)), ('Quitar', remove_scene)]:
        button(row, text, action).pack(side='left', padx=(0, 8))
    row = tk.Frame(cycle, bg=BG)
    row.pack(fill='x')

    def preset(names):
        working_scenes[:] = list(names)
        refresh_playlist()

    for text, names in [('Circulares', CIRCULAR_SCENES), ('Nuevos', INTERNET_SCENES), ('Todos', SCENE_LABELS)]:
        button(row, text, lambda names=names: preset(names)).pack(side='left', padx=(0, 8))
    refresh_playlist()
    label(settings, 'Tiempos y presentación', 17).pack(anchor='w', pady=(0, 15))
    numeric_inputs = {}
    for field, title, low, high in [('scene_seconds', 'Duración de cada diseño (s)', 2, 30),
                                   ('cpu_seconds', 'Datos CPU (s; 0 para omitir)', 0, 60),
                                   ('gpu_seconds', 'Temperatura GPU (s; 0 para omitir)', 0, 60),
                                   ('speed', 'Velocidad de animación (0,4–1,6)', .4, 1.6)]:
        label(settings, title, 11).pack(anchor='w', pady=(8, 5))
        variable = tk.StringVar(value=str(getattr(profile, field)))
        ttk.Spinbox(settings, from_=low, to=high, increment=.1 if field == 'speed' else 1,
                    textvariable=variable, width=12).pack(anchor='w')
        numeric_inputs[field] = variable
    logo_setting = tk.BooleanVar(value=profile.logo)
    tk.Checkbutton(settings, text='Logo COUGAR en las páginas de temperatura', variable=logo_setting,
                   bg=BG, fg=INK, selectcolor=CARD, activebackground=BG, activeforeground=INK,
                   font=('Segoe UI', 10)).pack(anchor='w', pady=18)
    label(settings, 'Las preferencias se guardan en tu perfil de Windows.\n'
          'El logo se mantiene apagado durante los diseños.', 10, MUTED, justify='left').pack(anchor='w')

    def collect_profile():
        return Profile.from_dict(dict(scenes=working_scenes, logo=logo_setting.get(),
                                      **{key: variable.get().replace(',', '.') for key, variable in numeric_inputs.items()}))

    def apply_profile(play=False):
        try:
            updated = collect_profile()
            DATA.mkdir(parents=True, exist_ok=True)
            save_profile(profile_path, updated)
        except (ValueError, OSError, TypeError) as exc:
            messagebox.showerror('Revisa la configuración', str(exc), parent=root)
            return
        ui['profile'] = updated
        commands.put(('profile', updated))
        if play:
            select('cycle')
        record('Preferencias guardadas' + (' · ciclo iniciado' if play else ''))

    button(settings, 'Guardar y aplicar', apply_profile, True).pack(anchor='w', pady=15)
    label(diagnosis, 'Conexión y registro', 17).pack(anchor='w')
    label(diagnosis, 'El instalador incluye el servicio de sensores COUGAR Studio.\n'
          'La aplicación envía únicamente cuadros de pantalla por USB.', 10, MUTED, justify='left').pack(anchor='w', pady=10)
    journal = tk.Text(diagnosis, height=14, bg=CARD, fg=INK, relief='flat', font=('Consolas', 9), state='disabled')
    journal.pack(fill='both', expand=True)

    def record(text):
        entry = datetime.now().strftime('%H:%M:%S') + '  ' + text
        ui['log'] = (ui['log']+[entry])[-300:]
        journal.configure(state='normal')
        journal.delete('1.0', 'end')
        journal.insert('end', '\n'.join(ui['log']))
        journal.see('end')
        journal.configure(state='disabled')

    def export():
        path = filedialog.asksaveasfilename(parent=root, defaultextension='.json', initialfile='cougar-studio-diagnostico.json')
        if path:
            try:
                Path(path).write_text(json.dumps(dict(time=datetime.now().isoformat(), sensors=ui['values'],
                    usb=ui['usb'], profile=ui['profile'].to_dict(), log=ui['log']), indent=2, ensure_ascii=False), encoding='utf-8')
            except OSError as exc:
                messagebox.showerror('No se pudo guardar', str(exc), parent=root)

    def restart_sensors():
        if preview:
            record('Simulación: no se reinició ningún servicio.')
            return
        script = ASSETS / 'restart-sensors.ps1'
        shell = c.WinDLL('shell32', use_last_error=True)
        shell.ShellExecuteW.argtypes = [w.HWND, w.LPCWSTR, w.LPCWSTR, w.LPCWSTR, w.LPCWSTR, c.c_int]
        shell.ShellExecuteW.restype = c.c_ssize_t
        result = shell.ShellExecuteW(None, 'runas', 'powershell.exe', f'-NoProfile -ExecutionPolicy Bypass -File "{script}"', None, 0)
        record('Reinicio de sensores solicitado a Windows.' if result > 32 else 'Windows no inició el reinicio de sensores.')

    row = tk.Frame(diagnosis, bg=BG)
    row.pack(fill='x', pady=12)
    button(row, 'Exportar diagnóstico', export).pack(side='left')
    button(row, 'Reiniciar sensores', restart_sensors).pack(side='left', padx=8)
    label(updates, 'Actualizaciones desde GitHub', 17).pack(anchor='w')
    label(updates, f'Versión instalada: {VERSION}\nRepositorio público: {REPOSITORY}', 11, MUTED, justify='left').pack(anchor='w', pady=15)
    update_status = label(updates, 'Puedes comprobar si hay una nueva versión.', 11, wraplength=560, justify='left')
    update_status.pack(anchor='w', pady=10)
    update_state = {'busy': False, 'info': None, 'installer': None}

    def check_updates():
        if update_state['busy']:
            return
        update_state['busy'] = True
        update_status.configure(text='Comprobando la última versión…')
        def task():
            try:
                events.put(('update_info', check_latest()))
            except Exception as exc:
                events.put(('update_error', str(exc)))
        threading.Thread(target=task, daemon=True).start()

    def fetch_update():
        if update_state['busy'] or not update_state['info']:
            return
        update_state['busy'] = True
        update_status.configure(text='Descargando y verificando el instalador…')
        def task():
            try:
                events.put(('update_downloaded', download_update(update_state['info'], DATA/'updates')))
            except Exception as exc:
                events.put(('update_error', str(exc)))
        threading.Thread(target=task, daemon=True).start()

    def install_update():
        installer = update_state['installer']
        if installer and messagebox.askyesno('Instalar actualización', 'Se cerrará COUGAR Studio y se abrirá el instalador verificado. ¿Continuar?', parent=root):
            ui['installer_on_exit'] = installer
            ui['closing'] = True
            stop.set()
            wait_close()

    button(updates, 'Buscar actualizaciones', check_updates, True).pack(anchor='w', pady=8)
    download_button = button(updates, 'Descargar nueva versión', fetch_update)
    download_button.pack(anchor='w', pady=8)
    download_button.configure(state='disabled')
    install_button = button(updates, 'Instalar y reiniciar', install_update)
    install_button.pack(anchor='w', pady=8)
    install_button.configure(state='disabled')
    label(updates, 'La descarga se verifica con SHA-256 antes de ejecutarse.\n'
          'Sin Internet, la pantalla y los sensores siguen funcionando.', 10, MUTED, justify='left').pack(anchor='w', pady=15)
    bar = tk.Frame(root, bg=BG, padx=24, pady=12)
    bar.pack(fill='x')
    button(bar, 'Guardar y reproducir ciclo', lambda: apply_profile(True), True).pack(side='left')
    pause_button = button(bar, 'Pausar', lambda: commands.put(('pause', None)))
    pause_button.pack(side='left', padx=10)
    label(bar, 'Mantén la aplicación abierta para actualizar la pantalla.', 9, MUTED).pack(side='right')

    def sensor_worker():
        connection = SensorClient() if not preview else None
        try:
            while not stop.is_set():
                try:
                    values = [48.3, 2057, 55.5, 20, 57.6, 35] if preview else connection.read()
                    commands.put(('sensor', (values, None)))
                    events.put(('sensor', values))
                except Exception as exc:
                    commands.put(('sensor', ([None]*6, str(exc))))
                    events.put(('sensor', [None]*6))
                stop.wait(1)
        finally:
            if connection:
                connection.close()

    def controller():
        writer = None
        ownership = DisplayOwnership(enabled=not preview)
        blob, code, _ = load()
        player = Player(profile, time.monotonic())
        player.select(initial, time.monotonic())
        latest = [None]*6
        next_open, last_write, previous_packet = 0, 0, None
        last_status, last_scene = None, None
        last_cpu = missing_temperature_packet(blob, 'cpu')
        gif_animation, gif_live = None, False
        last_clock, last_ownership = time.monotonic(), None
        try:
            while not stop.is_set():
                now = time.monotonic()
                try:
                    while True:
                        kind, value = commands.get_nowait()
                        if kind == 'sensor':
                            latest, sensor_error = value
                        elif kind == 'select':
                            player.select(value, now)
                        elif kind == 'pause':
                            player.toggle_pause(now)
                        elif kind == 'profile':
                            player.profile = value
                            player.select(player.mode, now)
                        elif kind == 'gif':
                            gif_animation, player.gif_seconds, gif_live = value
                            player.select('gif', now)
                except queue.Empty:
                    pass
                scene, elapsed, remaining = player.current(now)
                needs_display = scene != 'sensors' and not (scene == 'gif' and not gif_live)
                exclusive_ready = ownership.request(needs_display)
                if not exclusive_ready:
                    # Wait for the service to stop the competing writer before
                    # starting the scene clock. CPU remains visible meanwhile.
                    delay = max(0, now-last_clock)
                    player.started = min(now, player.started+delay)
                    if player.paused_at is not None:
                        player.paused_at += delay
                    scene, elapsed, remaining = player.current(now)
                ownership_state = ('Esperando control de pantalla · '+(ownership.error or 'pausando RM-Hardware')) if not exclusive_ready else ''
                if ownership_state != last_ownership:
                    events.put(('ownership', ownership_state))
                    if needs_display and exclusive_ready and ownership.enabled:
                        events.put(('log', 'Control exclusivo confirmado · RM-Hardware pausado durante la escena'))
                    last_ownership = ownership_state
                try:
                    last_cpu = numeric_packet(blob, code, latest)
                except ValueError:
                    last_cpu = missing_temperature_packet(blob, 'cpu')
                if scene == 'gif' and gif_animation:
                    packet = gif_animation.packet_at(elapsed)
                elif scene == 'gpu':
                    try:
                        packet = numeric_packet(blob, code, latest, 'gpu')
                    except ValueError:
                        packet = missing_temperature_packet(blob, 'gpu')
                else:
                    packet = scene_packet(blob, last_cpu, scene, elapsed)
                if scene in ('sensors', 'gpu') and not player.profile.logo:
                    cleared = bytearray(packet)
                    cleared[2+LOGO_BIT//8] &= ~(1 << (LOGO_BIT%8))
                    packet = bytes(cleared)
                if not preview and writer is None and now >= next_open:
                    try:
                        writer = HidWriter()
                        events.put(('log', 'Pantalla USB conectada · HWCX / USB Display'))
                    except Exception as exc:
                        events.put(('usb', 'USB sin conexión · '+str(exc)))
                        next_open = now+3
                usb_packet = last_cpu if scene == 'gif' and not gif_live else packet
                if not exclusive_ready:
                    usb_packet = last_cpu
                if scene == 'gif' and not gif_live and not player.profile.logo:
                    cleared = bytearray(usb_packet)
                    cleared[2+LOGO_BIT//8] &= ~(1 << (LOGO_BIT%8))
                    usb_packet = bytes(cleared)
                if writer and (usb_packet != previous_packet or now-last_write >= 1):
                    try:
                        writer.write(usb_packet)
                        previous_packet, last_write = usb_packet, now
                    except Exception as exc:
                        writer.close()
                        writer = None
                        next_open = now+3
                        events.put(('log', 'Escritura USB fallida: '+str(exc)))
                status = 'Simulación · sin órdenes USB' if preview else ('USB conectado' if writer else 'Esperando pantalla USB')
                if status != last_status:
                    events.put(('usb', status))
                    last_status = status
                if scene != last_scene:
                    events.put(('log', 'Página: '+SCENE_LABELS.get(scene, {'sensors':'CPU', 'gpu':'GPU', 'blank':'Pantalla apagada', 'soulkiller_all':'SoulKilleR'}.get(scene, scene))))
                    last_scene = scene
                events.put(('frame', packet, scene, player.paused_at is not None, remaining))
                last_clock = now
                stop.wait(.05 if scene == 'gif' else (.2 if scene not in ('sensors', 'gpu') else .15))
        except Exception as exc:
            events.put(('log', 'Error del controlador: '+str(exc)))
        finally:
            if writer:
                try:
                    writer.write(last_cpu)
                except Exception:
                    pass
                writer.close()
            ownership.close()

    def pump():
        try:
            while True:
                event = events.get_nowait()
                if event[0] == 'log':
                    record(event[1])
                elif event[0] == 'sensor':
                    ui['values'] = event[1]
                    for widget, index in zip(sensor_labels, (0, 4, 1, 2, 3, 5)):
                        value = event[1][index]
                        widget.configure(text='—' if value is None else f'{value:.1f}' if index in (0, 4) else f'{value:.0f}')
                elif event[0] == 'usb':
                    ui['usb'] = event[1]
                elif event[0] == 'update_info':
                    update_state.update(busy=False, info=event[1])
                    download_button.configure(state='normal' if event[1] else 'disabled')
                    update_status.configure(text=f'Nueva versión disponible: {event[1].version}' if event[1] else 'Ya tienes la última versión publicada.')
                elif event[0] == 'update_downloaded':
                    update_state.update(busy=False, installer=event[1])
                    install_button.configure(state='normal')
                    update_status.configure(text='Instalador descargado. SHA-256 correcto. Listo para instalar.')
                elif event[0] == 'update_error':
                    update_state['busy'] = False
                    update_status.configure(text='No se pudo completar: '+event[1])
                elif event[0] == 'ownership':
                    ui['ownership'] = event[1]
                    if event[1]:
                        record(event[1])
                elif event[0] == 'gif_loaded':
                    _, animation, path, autoplay = event
                    ui.update(gif=animation, gif_path=path)
                    gif_busy['value'] = False
                    for control in gif_controls:
                        control.configure(state='normal')
                    ui['gif_thumbnail'] = tk.PhotoImage(data=animation.preview_png)
                    gif_thumbnail.configure(image=ui['gif_thumbnail'], text='')
                    gif_status.configure(text=f'{animation.name} · {animation.source_frames} cuadros originales · '
                                         f'{animation.duration:g} s · adaptado a 10 cuadros/s.\n'
                                         'Ajusta la conversión y pulsa Aplicar ajustes antes de reproducir.')
                    record(f'GIF convertido: {animation.source_frames} cuadros → {len(animation.packets)} cuadros de segmentos')
                    tabs.select(gif_tab)
                    if autoplay:
                        play_gif(autoplay == 'screen')
                elif event[0] == 'gif_error':
                    gif_busy['value'] = False
                    gif_status.configure(text='No se pudo convertir: '+event[1])
                    for control in gif_controls:
                        control.configure(state='normal' if ui['gif'] or control in (gif_import, gif_demo_button) else 'disabled')
                    record('Error GIF: '+event[1])
                elif event[0] == 'frame':
                    _, packet, scene, paused, remaining = event
                    if ui.get('scene') == 'gif' and scene == 'sensors':
                        gif_status.configure(text='Reproducción terminada. El dispositivo muestra los datos de CPU.')
                    ui['scene'] = scene
                    ui['last_packet'] = packet.hex()
                    title = SCENE_LABELS.get(scene, {'gif':'GIF · segmentos', 'sensors':'Datos de CPU', 'gpu':'Temperatura GPU', 'blank':'Pantalla apagada', 'soulkiller_all':'SoulKilleR · solo arriba'}.get(scene, scene))
                    current.configure(text=title+(' · pausa' if paused else '')+(f' · {remaining:.0f} s' if remaining is not None else ''))
                    pause_button.configure(text='Reanudar' if paused else 'Pausar')
                    for items, mask in zip(polygons, read_masks(controller_blob, packet)):
                        for bit, item in enumerate(items):
                            canvas.itemconfigure(item, fill=INK if mask & (1 << bit) else '#1b2027')
                    canvas.itemconfigure(logo, state='normal' if packet[2+LOGO_BIT//8] & (1 << (LOGO_BIT%8)) else 'hidden')
                    for item in units:
                        canvas.itemconfigure(item, state='normal' if scene == 'sensors' and bool(packet[2+27//8] & (1 << (27%8))) else 'hidden')
                    for item, bit in [(decimal, 115), (power_dot, 15)]:
                        canvas.itemconfigure(item, state='normal' if packet[2+bit//8] & (1 << (bit%8)) else 'hidden')
                missing = ui['values'][0] is None or ui['values'][4] is None
                transport.configure(text=ui['usb']+'\n'+(ui.get('ownership') or ('Sensores no disponibles · consulta Diagnóstico' if missing else 'Sensores CPU y GPU actualizados')))
        except queue.Empty:
            pass
        if not ui['closing']:
            root.after(80, pump)

    def close():
        if not preview and not ui['closing'] and not messagebox.askyesno('Cerrar COUGAR Studio',
                'Se detendrá la actualización de la pantalla y los últimos valores pueden quedar congelados. ¿Cerrar?', parent=root):
            return
        ui['closing'] = True
        stop.set()
        wait_close()

    def wait_close():
        if sensor_thread.is_alive() or display_thread.is_alive():
            root.after(100, wait_close)
        else:
            root.destroy()

    controller_blob, _, _ = load()
    sensor_thread = threading.Thread(target=sensor_worker, daemon=True)
    display_thread = threading.Thread(target=controller, daemon=True)
    root.protocol('WM_DELETE_WINDOW', close)
    if profile_error:
        record('Perfil no válido; se usan valores predeterminados: '+profile_error)
    record('COUGAR Studio iniciado'+(' en simulación.' if preview else '.'))
    sensor_thread.start()
    display_thread.start()
    pump()
    if not preview and not smoke:
        root.after(3000, check_updates)
    if gif_demo or smoke:
        root.after(150, lambda: convert_gif(ASSETS/'demo-segmentos.gif', 'preview' if preview else 'screen'))
    if smoke:
        callback_errors = []
        def fail_callback(kind, value, traceback):
            callback_errors.append(value)
            root.after(0, close)
        root.report_callback_exception = fail_callback
        root.after(200, lambda: select('orbit_all'))
        root.after(400, lambda: commands.put(('pause', None)))
        root.after(600, lambda: commands.put(('pause', None)))
        root.after(800, lambda: tabs.select(cycle))
        root.after(1000, lambda: tabs.select(settings))
        root.after(1200, lambda: tabs.select(diagnosis))
        root.after(1400, lambda: (tabs.select(gif_tab), play_gif()))
        if screenshot:
            def capture():
                from PIL import ImageGrab
                root.update()
                ImageGrab.grab(window=root.winfo_id()).save(screenshot)
            root.after(1700, capture)
        root.after(2300, close)
    root.mainloop()
    if mutex:
        kernel.CloseHandle(mutex)
    if ui.get('installer_on_exit'):
        os.startfile(str(ui['installer_on_exit']))
    if smoke and callback_errors:
        raise RuntimeError('Error durante la prueba de interfaz: '+str(callback_errors[0]))
    if smoke and not ui['gif']:
        raise RuntimeError('La prueba de interfaz no pudo cargar el GIF de demostración')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--smoke-test', action='store_true')
    parser.add_argument('--screenshot')
    parser.add_argument('--gif-demo', action='store_true', help='Mostrar el GIF de demostración durante 12 s y volver a CPU')
    parser.add_argument('--mode', choices=['sensors','gpu','cycle','blank','name']+list(SCENE_LABELS), default='sensors')
    args = parser.parse_args()
    try:
        run(args.preview or args.smoke_test, args.smoke_test, args.screenshot, args.mode, args.gif_demo)
    except Exception as exc:
        messagebox.showerror('COUGAR Studio', str(exc))
        raise
