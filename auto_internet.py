import os
import time
import logging
import subprocess
import re
import socket
import glob
from threading import Thread
import pwnagotchi.plugins as plugins
from flask import render_template_string

class AutoInternet(plugins.Plugin):
    __author__ = 'HackerOne'
    __version__ = '3.5.2'
    __license__ = 'GPL3'
    __description__ = 'Tema Invertido com Conexão Instantânea ao clicar na rede guardada.'

    def __init__(self):
        self.running = False
        self.enabled = True
        self.agent = None
        self.networks = []
        self.threshold = 5 
        self.logs = ["Pronto para conectar."]

    def _add_log(self, msg):
        self.logs.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
        if len(self.logs) > 6: self.logs.pop(0)

    def _get_iw_status(self):
        try:
            res = subprocess.check_output(['iw', 'dev', 'wlan0', 'info']).decode()
            mode = re.search(r'type (.*)', res)
            return mode.group(1).upper() if mode else "DESCONHECIDO"
        except: return "ERRO"

    def _get_connected_ssid(self):
        try:
            ssid = subprocess.check_output(['iwgetid', '-r']).decode().strip()
            return ssid if ssid else "SNIFFING..."
        except: return "OFFLINE"

    def _get_saved_networks_detailed(self):
        """Retorna lista de SSIDs e as suas configurações completas."""
        try:
            if os.path.exists('/etc/wpa_supplicant/wpa_supplicant.conf'):
                with open('/etc/wpa_supplicant/wpa_supplicant.conf', 'r') as f:
                    content = f.read()
                    # Encontra blocos de network para identificar SSIDs e se têm PSK
                    networks = []
                    blocks = re.findall(r'network={.*?ssid="(.*?)".*?}', content, re.DOTALL)
                    for ssid in blocks:
                        has_psk = f'ssid="{ssid}"' in content and 'psk=' in content
                        networks.append({'ssid': ssid, 'psk': 'S' if has_psk else 'N'})
                    return networks
            return []
        except: return []

    def on_webhook(self, path, request):
        status_info = ""
        if request.method == "POST":
            action = request.form.get('action')
            
            if action == "toggle_plugin":
                self.enabled = not self.enabled
                self._add_log(f"Auto-Upload: {'ON' if self.enabled else 'OFF'}")
            
            elif action == "connect_to":
                ssid = request.form.get('ssid')
                self._add_log(f"A ligar forçado a: {ssid}")
                Thread(target=self._internet_cycle, args=(self.agent,)).start()
                status_info = f"<div style='color:#000; font-weight:bold;'>A tentar ligar a {ssid}...</div>"

            elif action == "force_scan":
                display = self.agent.view() if self.agent else None
                Thread(target=self._do_forced_scan, args=(display,)).start()
                status_info = "<div>Scan em curso...</div>"

            elif request.form.get('ssid_new'):
                self._update_wpa_conf(request.form.get('ssid_new'), request.form.get('password'))
                status_info = "<div>Nova rede guardada.</div>"

        mode = self._get_iw_status()
        ssid_ativo = self._get_connected_ssid()
        saved_nets = self._get_saved_networks_detailed()
        ip = subprocess.check_output(['hostname', '-I']).decode().split()[0] if self.running else "0.0.0.0"
        
        html = """
        <html>
        <head><title>HackerOne Connect</title>
        <style>
            body { font-family: 'Courier New', monospace; padding: 15px; background: #fff; color: #000; text-align: center; }
            .card { background: #fff; padding: 15px; border: 2px solid #000; margin-bottom: 12px; }
            .menu-title { text-align: left; color: #000; font-size: 0.9em; font-weight: bold; margin-bottom: 8px; border-bottom: 2px solid #000; text-transform: uppercase; }
            .status-bar { padding: 10px; margin-bottom: 15px; font-weight: bold; border: 2px solid #000; display: flex; justify-content: space-around; background: #000; color: #fff; }
            .btn { padding: 8px; border: 2px solid #000; cursor: pointer; font-weight: bold; background: #fff; color: #000; text-transform: uppercase; }
            .btn:hover { background: #000; color: #fff; }
            .btn-small { font-size: 0.7em; width: auto; padding: 4px 8px; }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
            ul { list-style: none; padding: 0; text-align: left; font-size: 0.85em; }
            li { padding: 6px 0; border-bottom: 1px solid #ccc; display: flex; justify-content: space-between; align-items: center; }
            .log-box { background: #eee; color: #000; border: 1px dashed #000; padding: 8px; font-size: 0.75em; text-align: left; }
            input { margin: 8px 0; padding: 10px; width: 92%; border: 2px solid #000; background: #fff; color: #000; }
        </style>
        </head>
        <body>
            <h2 style="margin:0 0 15px 0;">📡 CONNECT CONSOLE</h2>

            <div class="status-bar">
                <span>AUTO: {{ 'ON' if enabled else 'OFF' }}</span>
                <span>SSID: {{ ssid_ativo }}</span>
            </div>

            {{ status_info | safe }}

            <div class="card">
                <div class="menu-title">Saved Profiles (Click to Connect)</div>
                <ul>
                    {% for net in saved_nets %} 
                    <li>
                        <span>> {{ net.ssid }} {% if net.psk == 'N' %}(OPEN){% endif %}</span>
                        <form method="POST" style="margin:0;">
                            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                            <input type="hidden" name="ssid" value="{{ net.ssid }}">
                            <button name="action" value="connect_to" class="btn btn-small">CONNECT</button>
                        </form>
                    </li> 
                    {% endfor %}
                </ul>
            </div>

            <div class="card">
                <div class="menu-title">Actions</div>
                <div class="grid">
                    <form method="POST" style="margin:0;"><input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                        <button name="action" value="toggle_plugin" class="btn" style="width:100%;">TOGGLE AUTO</button></form>
                    <form method="POST" style="margin:0;"><input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                        <button name="action" value="force_scan" class="btn" style="width:100%;">RE-SCAN</button></form>
                </div>
            </div>

            <div class="card">
                <div class="menu-title">Add New</div>
                <form method="POST">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                    <input type="text" name="ssid_new" placeholder="SSID" required>
                    <input type="password" name="password" placeholder="PASSWORD">
                    <button type="submit" class="btn" style="width:100%; margin-top:5px;">SAVE PROFILE</button>
                </form>
            </div>

            <div class="card">
                <div class="log-box">
                    {% for log in logs %} <div>{{ log }}</div> {% endfor %}
                </div>
            </div>
            
            <p style="font-size:0.7em;">IP: {{ ip }} | MODE: {{ mode }}</p>
        </body>
        </html>
        """
        return render_template_string(html, enabled=self.enabled, mode=mode, ssid_ativo=ssid_ativo, saved_nets=saved_nets, logs=self.logs, ip=ip, version=self.__version__, status_info=status_info)

    def _do_forced_scan(self, display):
        try:
            subprocess.run(["systemctl", "stop", "bettercap"], check=False)
            subprocess.run(["iw", "dev", "wlan0", "set", "type", "managed"], check=False)
            subprocess.run(["ip", "link", "set", "wlan0", "up"], check=False)
            time.sleep(2)
            result = subprocess.check_output(["iwlist", "wlan0", "scan"], timeout=15).decode('utf-8')
            found = re.findall(r'ESSID:"([^"]*)"', result)
            self.networks = sorted(list(set([n for n in found if n.strip()])))
        finally:
            subprocess.run(["iw", "dev", "wlan0", "set", "type", "monitor"], check=False)
            subprocess.run(["systemctl", "start", "bettercap"], check=False)

    def _internet_cycle(self, agent):
        self.running = True
        display = agent.view() if agent else None
        if display: display.set('status', 'CONNECTING...'); display.update(force=True)
        try:
            subprocess.run(["systemctl", "stop", "bettercap"], check=False)
            subprocess.run(["iw", "dev", "wlan0", "set", "type", "managed"], check=False)
            subprocess.run(["systemctl", "restart", "wpa_supplicant"], check=False)
            time.sleep(180) 
        finally:
            subprocess.run(["systemctl", "stop", "wpa_supplicant"], check=False)
            subprocess.run(["iw", "dev", "wlan0", "set", "type", "monitor"], check=False)
            subprocess.run(["systemctl", "start", "bettercap"], check=False)
            if display: display.set('status', 'SCANNING'); display.update(force=True)
            self.running = False

    def _update_wpa_conf(self, ssid, password):
        if not password: block = f'network={{\n    ssid="{ssid}"\n    key_mgmt=NONE\n}}'
        else: block = f'network={{\n    ssid="{ssid}"\n    psk="{password}"\n    scan_ssid=1\n}}'
        conf = f'ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\nupdate_config=1\ncountry=PT\n\n{block}'
        with open('/etc/wpa_supplicant/wpa_supplicant.conf', 'w') as f: f.write(conf)
        self._add_log(f"Novo perfil: {ssid}")

    def on_ready(self, agent): self.agent = agent