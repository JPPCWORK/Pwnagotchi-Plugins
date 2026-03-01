import os
import logging
import io
import zipfile
from pwnagotchi import plugins
from flask import send_file, render_template_string

class WebHandshakes(plugins.Plugin):
    __author__ = 'HackerOne'
    __version__ = '2.5'
    __license__ = 'GPL3'
    __description__ = 'Download handshakes via WebUI com tema claro.'

    def on_loaded(self):
        logging.info(f"[{self.__author__}] Plugin WebHandshakes v{self.__version__} (White Theme) carregado!")

    def on_webhook(self, path, request):
        handshake_dir = "/root/handshakes"
        
        try:
            files = sorted([f for f in os.listdir(handshake_dir) if f.endswith(('.pcap', '.pcapng'))])
        except Exception as e:
            return f"Erro ao aceder pasta: {str(e)}", 500
        
        # --- Lógica ZIP ---
        if path == "zip":
            try:
                memory_file = io.BytesIO()
                with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for f in files:
                        zf.write(os.path.join(handshake_dir, f), f)
                
                memory_file.seek(0)
                return send_file(
                    memory_file, 
                    mimetype='application/zip', 
                    as_attachment=True, 
                    attachment_filename='handshakes_hackerone.zip'
                )
            except Exception as e:
                return f"Erro ao criar ZIP: {str(e)}", 500
        
        # --- Lógica Download Único ---
        if path == "file":
            fname = request.args.get('name')
            file_path = os.path.join(handshake_dir, fname)
            if os.path.exists(file_path):
                return send_file(file_path, as_attachment=True)
            return "Ficheiro não encontrado", 404

        # --- Interface HTML (Tema Branco) ---
        html = """
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f4f4f9; color: #333; padding: 20px; }
                .container { max-width: 800px; margin: auto; background: #fff; padding: 25px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h2 { color: #222; border-bottom: 2px solid #eee; padding-bottom: 10px; margin-top: 0; }
                .btn { display: inline-block; padding: 10px 20px; background: #2196F3; color: #fff; text-decoration: none; font-weight: bold; border-radius: 4px; margin-bottom: 20px; transition: background 0.2s; }
                .btn:hover { background: #1976D2; }
                ul { list-style: none; padding: 0; }
                li { display: flex; justify-content: space-between; align-items: center; padding: 12px; border-bottom: 1px solid #eee; }
                li:hover { background: #fafafa; }
                .dl { color: #2196F3; text-decoration: none; font-weight: 600; font-size: 0.9em; border: 1px solid #2196F3; padding: 5px 10px; border-radius: 4px; }
                .dl:hover { background: #2196F3; color: #fff; }
                .footer { margin-top: 25px; font-size: 0.8em; color: #999; text-align: center; }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Handshake Manager</h2>
                <p>Gerido por: <strong>{{ author }}</strong> (v{{ version }})</p>
                
                <a href="/plugins/web_handshakes/zip" class="btn">📥 DESCARREGAR TUDO (.ZIP)</a>
                
                <ul>
                    {% if not files %}
                        <li>Nenhum handshake encontrado.</li>
                    {% endif %}
                    {% for f in files %}
                    <li>
                        <span>{{ f }}</span>
                        <a href="/plugins/web_handshakes/file?name={{ f }}" class="dl">DOWNLOAD</a>
                    </li>
                    {% endfor %}
                </ul>
                
                <div class="footer">Pwnagotchi Plugin &bull; HackerOne Edition</div>
            </div>
        </body>
        </html>
        """
        return render_template_string(html, files=files, author=self.__author__, version=self.__version__)