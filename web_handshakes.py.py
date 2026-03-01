import os
import logging
import io
import zipfile
from pwnagotchi import plugins
from flask import send_file, render_template_string

class WebHandshakes(plugins.Plugin):
    __author__ = 'Pwnagotchi Helper'
    __version__ = '1.2.0'
    __license__ = 'GPL3'
    __description__ = 'Download handshakes individualmente ou em massa (Versão Fix).'

    def on_loaded(self):
        logging.info("[!] Plugin WebHandshakes carregado e pronto!")

    def on_webhook(self, path, request):
        handshake_dir = "/root/handshakes"
        
        # Filtrar apenas ficheiros de handshake válidos
        try:
            files = [f for f in os.listdir(handshake_dir) if f.endswith(('.pcap', '.pcapng'))]
        except Exception as e:
            return f"Erro ao aceder pasta: {str(e)}", 500
        
        # --- Lógica para Baixar TUDO em ZIP ---
        if path == "zip":
            try:
                memory_file = io.BytesIO()
                with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for f in files:
                        file_path = os.path.join(handshake_dir, f)
                        zf.write(file_path, f)
                
                memory_file.seek(0)
                # Usamos attachment_filename para compatibilidade com Flask antigo
                return send_file(
                    memory_file, 
                    mimetype='application/zip', 
                    as_attachment=True, 
                    attachment_filename='todos_handshakes.zip',
                    cache_timeout=0
                )
            except Exception as e:
                logging.error(f"[WebHandshakes] Erro no ZIP: {e}")
                return f"Erro ao criar ZIP: {str(e)}", 500
        
        # --- Lógica para Baixar UM ficheiro ---
        if path == "file":
            fname = request.args.get('name')
            if not fname:
                return "Nome do ficheiro não fornecido", 400
            
            file_path = os.path.join(handshake_dir, fname)
            if os.path.exists(file_path):
                return send_file(file_path, as_attachment=True)
            return "Ficheiro não encontrado", 404

        # --- Interface Visual (HTML) ---
        html = """
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { font-family: 'Courier New', Courier, monospace; padding: 20px; background: #000; color: #00ff00; }
                .btn { display: inline-block; padding: 12px 24px; background: #00ff00; color: #000; text-decoration: none; font-weight: bold; border-radius: 3px; margin-bottom: 20px; border: none; cursor: pointer; }
                .btn-all { background: #0088ff; color: white; }
                li { margin-bottom: 12px; border-bottom: 1px solid #222; padding-bottom: 8px; list-style: none; display: flex; justify-content: space-between; align-items: center; }
                a.dl-link { color: #00ff00; text-decoration: underline; }
                .container { max-width: 800px; margin: auto; }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>📟 Handshake Manager</h2>
                <a href="/plugins/web_handshakes/zip" class="btn btn-all">📥 DESCARREGAR TODOS (.ZIP)</a>
                <br>
                <ul>
                {% for f in files %}
                    <li>
                        <span>📄 {{ f }}</span>
                        <a href="/plugins/web_handshakes/file?name={{ f }}" class="dl-link"><b>[Download]</b></a>
                    </li>
                {% endfor %}
                </ul>
            </div>
        </body>
        </html>
        """
        return render_template_string(html, files=files)