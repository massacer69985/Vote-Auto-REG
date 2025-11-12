import sys
import webbrowser
import json
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel,
    QVBoxLayout, QWidget, QLineEdit, QGroupBox,
    QMessageBox, QFileDialog, QCheckBox, QHBoxLayout,
    QProgressBar, QSizePolicy, QSpacerItem, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QTimer
from PyQt6.QtMultimedia import QSoundEffect

# --- Worker Thread ---
class Worker(QThread):
    tick = pyqtSignal(str, int)
    notify = pyqtSignal(str)

    def __init__(self, url, interval_minutes):
        super().__init__()
        self.url = url
        self.interval_seconds = interval_minutes * 60
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            self.notify.emit(self.url)
            self.sleep(5)
            if not self.running:
                break
            webbrowser.open(self.url)
            remaining = self.interval_seconds
            while remaining > 0 and self.running:
                self.tick.emit(self.objectName(), remaining)
                self.sleep(1)
                remaining -= 1

    def stop(self):
        self.running = False

# --- Main Window ---
class LienAutomatiqueApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🌐 Vote Automatique")
        self.setGeometry(100, 100, 700, 800)
        self.setMinimumSize(500, 500)

        # Variables
        self.serveurprive_url = "https://serveur-prive.net/minecraft/reg-mc/vote"
        self.listeserveur_url = "https://www.liste-serveurs-minecraft.org/vote/?idc=202957"
        self.sound_file = "notify.wav"
        self.sound_effect = QSoundEffect()

        # Workers
        self.worker_sp = Worker(self.serveurprive_url, 90)
        self.worker_sp.setObjectName("serveurprive")
        self.worker_ls = Worker(self.listeserveur_url, 180)
        self.worker_ls.setObjectName("listeserveur")
        self.worker_sp.tick.connect(self.update_time)
        self.worker_ls.tick.connect(self.update_time)
        self.worker_sp.notify.connect(self.play_notification)
        self.worker_ls.notify.connect(self.play_notification)

        self.setup_ui()
        self.setup_style()
        self.auto_load_settings()

        # Timers smooth progress
        self.timer_sp = QTimer()
        self.timer_sp.timeout.connect(self.update_progress_sp)
        self.timer_ls = QTimer()
        self.timer_ls.timeout.connect(self.update_progress_ls)
        self.elapsed_sp = 0
        self.elapsed_ls = 0

    # --- UI ---
    def setup_ui(self):
        # ScrollArea pour éviter superpositions
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        scroll.setWidget(container)
        central_layout = QVBoxLayout(container)
        central_layout.setSpacing(15)
        central_layout.setContentsMargins(15, 15, 15, 15)
        self.setCentralWidget(scroll)

        # --- Serveur Privé ---
        self.grp1 = QGroupBox("🕹️ Serveur Privé")
        self.grp1.setMinimumWidth(400)
        lay1 = QVBoxLayout()

        # URL
        lay1.addWidget(QLabel("URL :"))
        self.url_sp = QLineEdit(self.serveurprive_url)
        self.url_sp.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        lay1.addWidget(self.url_sp)

        # Intervalle
        interval_layout_sp = QHBoxLayout()
        label_interval_sp = QLabel("Intervalle (minutes) :")
        self.interval_sp = QLineEdit("90")
        self.interval_sp.setMinimumWidth(80)
        self.interval_sp.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        interval_layout_sp.addWidget(label_interval_sp)
        interval_layout_sp.addWidget(self.interval_sp)
        lay1.addLayout(interval_layout_sp)

        # Boutons horizontal
        btn_layout_sp = QHBoxLayout()
        btn_open_sp = QPushButton("Ouvrir maintenant")
        btn_start_sp = QPushButton("Démarrer")
        btn_stop_sp = QPushButton("Arrêter")
        for btn in [btn_open_sp, btn_start_sp, btn_stop_sp]:
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.setup_hover_anim(btn)
            btn_layout_sp.addWidget(btn)
        btn_open_sp.clicked.connect(lambda: webbrowser.open(self.url_sp.text()))
        btn_start_sp.clicked.connect(self.start_sp)
        btn_stop_sp.clicked.connect(self.stop_sp)
        lay1.addLayout(btn_layout_sp)

        # Label + ProgressBar
        self.label_sp = QLabel("Temps restant : 0 s")
        self.label_sp.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        lay1.addWidget(self.label_sp)
        self.progress_sp = QProgressBar()
        self.progress_sp.setValue(0)
        self.progress_sp.setTextVisible(False)
        self.progress_sp.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        lay1.addWidget(self.progress_sp)

        self.grp1.setLayout(lay1)
        central_layout.addWidget(self.grp1, stretch=1)

        # --- Liste Serveur ---
        self.grp2 = QGroupBox("📋 Liste Serveur")
        self.grp2.setMinimumWidth(400)
        lay2 = QVBoxLayout()

        # URL
        lay2.addWidget(QLabel("URL :"))
        self.url_ls = QLineEdit(self.listeserveur_url)
        self.url_ls.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        lay2.addWidget(self.url_ls)

        # Intervalle
        interval_layout_ls = QHBoxLayout()
        label_interval_ls = QLabel("Intervalle (minutes) :")
        self.interval_ls = QLineEdit("180")
        self.interval_ls.setMinimumWidth(80)
        self.interval_ls.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        interval_layout_ls.addWidget(label_interval_ls)
        interval_layout_ls.addWidget(self.interval_ls)
        lay2.addLayout(interval_layout_ls)

        # Boutons
        btn_layout_ls = QHBoxLayout()
        btn_open_ls = QPushButton("Ouvrir maintenant")
        btn_start_ls = QPushButton("Démarrer")
        btn_stop_ls = QPushButton("Arrêter")
        for btn in [btn_open_ls, btn_start_ls, btn_stop_ls]:
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.setup_hover_anim(btn)
            btn_layout_ls.addWidget(btn)
        btn_open_ls.clicked.connect(lambda: webbrowser.open(self.url_ls.text()))
        btn_start_ls.clicked.connect(self.start_ls)
        btn_stop_ls.clicked.connect(self.stop_ls)
        lay2.addLayout(btn_layout_ls)

        # Label + ProgressBar
        self.label_ls = QLabel("Temps restant : 0 s")
        self.label_ls.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        lay2.addWidget(self.label_ls)
        self.progress_ls = QProgressBar()
        self.progress_ls.setValue(0)
        self.progress_ls.setTextVisible(False)
        self.progress_ls.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        lay2.addWidget(self.progress_ls)

        self.grp2.setLayout(lay2)
        central_layout.addWidget(self.grp2, stretch=1)

        # --- Son ---
        grp3 = QGroupBox("🔔 Son")
        lay3 = QVBoxLayout()
        self.sound_checkbox = QCheckBox("Activer le son")
        self.sound_checkbox.setChecked(True)
        self.entry_sound = QLineEdit(self.sound_file)
        btn_choose = QPushButton("Choisir un son")
        btn_test = QPushButton("Tester 🔊")
        btn_choose.clicked.connect(self.choose_sound)
        btn_test.clicked.connect(self.test_sound)
        for btn in [btn_choose, btn_test]:
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.setup_hover_anim(btn)
        row = QHBoxLayout()
        row.addWidget(self.entry_sound)
        row.addWidget(btn_choose)
        lay3.addWidget(self.sound_checkbox)
        lay3.addLayout(row)
        lay3.addWidget(btn_test)
        grp3.setLayout(lay3)
        central_layout.addWidget(grp3, stretch=0)

        # --- Charger / Sauvegarder ---
        btn_layout_bottom = QHBoxLayout()
        btn_load = QPushButton("📂 Charger")
        btn_save = QPushButton("💾 Sauvegarder")
        for btn in [btn_load, btn_save]:
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.setup_hover_anim(btn)
            btn_layout_bottom.addWidget(btn)
        btn_load.clicked.connect(self.load_settings)
        btn_save.clicked.connect(self.save_settings)
        central_layout.addLayout(btn_layout_bottom)

        # Spacer
        central_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    # --- Style Windows 11 Fluent ---
    def setup_style(self):
        self.setStyleSheet("""
            QWidget { background-color: rgba(232,236,244,0.95); font-family: 'Segoe UI Variable'; font-size: 11pt; color: #1c1c1c; }
            QGroupBox { font-weight: bold; border: none; border-radius: 16px; margin-top: 10px; padding: 15px; 
                        background-color: rgba(255,255,255,0.7); }
            QPushButton { background-color: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #4a90e2, stop:1 #1976d2);
                         color:white; border-radius:20px; padding:12px; font-weight:bold; min-height:36px; }
            QPushButton:hover { background-color: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #5aa0f2, stop:1 #2196f3); }
            QPushButton:pressed { background-color: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #0d47a1, stop:1 #1565c0); }
            QLineEdit, QProgressBar { background: #f5f7fa; border:1px solid #cfd8dc; border-radius:12px; padding:8px; color:#1c1c1c; }
            QProgressBar::chunk { background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #42a5f5, stop:1 #1976d2); border-radius:12px; }
            QLabel { color: #1c1c1c; font-weight: 500; }
            QCheckBox { color: #1c1c1c; font-weight:500; }
        """)

    # --- Hover animation ---
    def setup_hover_anim(self, btn):
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

    # --- Workers ---
    def start_sp(self):
        try:
            mins = int(self.interval_sp.text())
            self.worker_sp.url = self.url_sp.text()
            self.worker_sp.interval_seconds = mins*60
            self.elapsed_sp = 0
            self.total_sp = mins*60
            if not self.worker_sp.isRunning():
                self.worker_sp.start()
        except ValueError:
            QMessageBox.critical(self, "Erreur", "Intervalle invalide")

    def stop_sp(self):
        self.worker_sp.stop()
        self.progress_sp.setValue(0)
        self.label_sp.setText("Temps restant : 0 s")

    def start_ls(self):
        try:
            mins = int(self.interval_ls.text())
            self.worker_ls.url = self.url_ls.text()
            self.worker_ls.interval_seconds = mins*60
            self.elapsed_ls = 0
            self.total_ls = mins*60
            if not self.worker_ls.isRunning():
                self.worker_ls.start()
        except ValueError:
            QMessageBox.critical(self, "Erreur", "Intervalle invalide")

    def stop_ls(self):
        self.worker_ls.stop()
        self.progress_ls.setValue(0)
        self.label_ls.setText("Temps restant : 0 s")

    # --- Progress ---
    def update_progress_sp(self):
        if self.worker_sp.running:
            self.elapsed_sp += 0.05
            pct = min(100, (self.elapsed_sp / self.total_sp)*100)
            self.progress_sp.setValue(int(pct))

    def update_progress_ls(self):
        if self.worker_ls.running:
            self.elapsed_ls += 0.05
            pct = min(100, (self.elapsed_ls / self.total_ls)*100)
            self.progress_ls.setValue(int(pct))

    # --- Sound ---
    def play_notification(self, url):
        if self.sound_checkbox.isChecked() and os.path.exists(self.sound_file):
            self.sound_effect.setSource(QUrl.fromLocalFile(os.path.abspath(self.sound_file)))
            self.sound_effect.play()
        QMessageBox.information(self, "Notification", f"Le lien {url} va s’ouvrir dans 5 secondes.")

    def choose_sound(self):
        f, _ = QFileDialog.getOpenFileName(self, "Choisir un son", "", "Fichiers WAV (*.wav)")
        if f:
            self.sound_file = f
            self.entry_sound.setText(f)

    def test_sound(self):
        if not os.path.exists(self.entry_sound.text()):
            QMessageBox.warning(self, "Erreur", "Fichier introuvable.")
            return
        self.sound_effect.setSource(QUrl.fromLocalFile(os.path.abspath(self.entry_sound.text())))
        self.sound_effect.play()

    # --- Update label ---
    def update_time(self, name, remaining):
        if name=="serveurprive": self.label_sp.setText(f"Temps restant : {remaining}s")
        else: self.label_ls.setText(f"Temps restant : {remaining}s")

    # --- Settings ---
    def save_settings(self):
        f,_ = QFileDialog.getSaveFileName(self,"Sauvegarder","","Fichiers JSON (*.json)")
        if not f: return
        data = {
            "serveurprive_url": self.url_sp.text(),
            "listeserveur_url": self.url_ls.text(),
            "serveurprive_interval": self.interval_sp.text(),
            "listeserveur_interval": self.interval_ls.text(),
            "sound_file": self.entry_sound.text(),
            "sound_enabled": self.sound_checkbox.isChecked()
        }
        with open(f,"w",encoding="utf-8") as file:
            json.dump(data,file,indent=4)
        QMessageBox.information(self,"Sauvegarde","Paramètres enregistrés ✅")

    def load_settings(self):
        f,_ = QFileDialog.getOpenFileName(self,"Charger","","Fichiers JSON (*.json)")
        if f: self.load_settings_file(f)

    def auto_load_settings(self):
        if os.path.exists("settings.json"): self.load_settings_file("settings.json")

    def load_settings_file(self,path):
        with open(path,"r",encoding="utf-8") as file: data = json.load(file)
        self.url_sp.setText(data.get("serveurprive_url",self.serveurprive_url))
        self.url_ls.setText(data.get("listeserveur_url",self.listeserveur_url))
        self.interval_sp.setText(data.get("serveurprive_interval","90"))
        self.interval_ls.setText(data.get("listeserveur_interval","180"))
        self.entry_sound.setText(data.get("sound_file","notify.wav"))
        self.sound_checkbox.setChecked(data.get("sound_enabled",True))
        self.sound_file = data.get("sound_file","notify.wav")

# --- Run ---
if __name__=="__main__":
    app = QApplication(sys.argv)
    win = LienAutomatiqueApp()
    win.show()
    sys.exit(app.exec())
