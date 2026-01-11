import sys
import os
import gpxpy
import folium
import json
import tempfile
import shutil
import subprocess
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QFileDialog)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QEventLoop, QTimer

class GPXAnimator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GPX Animator")
        self.resize(1000, 800)

        self.tracks = [] 

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Buttons
        btn_layout = QHBoxLayout()
        self.open_btn = QPushButton("Open GPX")
        self.open_btn.clicked.connect(self.open_gpx)
        
        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.play_animation)
        self.play_btn.setEnabled(False)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_animation)
        self.stop_btn.setEnabled(False)

        self.export_btn = QPushButton("Export Video")
        self.export_btn.clicked.connect(self.export_video)
        self.export_btn.setEnabled(False)

        btn_layout.addWidget(self.open_btn)
        btn_layout.addWidget(self.play_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.export_btn)
        layout.addLayout(btn_layout)

        # Web view for Folium map
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)

        # Initial empty map
        self.load_map()

    def load_map(self, tracks=None, animate=False):
        # Default center
        m = folium.Map(location=[0, 0], zoom_start=2)
        
        if tracks:
            all_points = []
            for track_points in tracks:
                all_points.extend(track_points)
                if not animate:
                    folium.PolyLine(track_points, color="blue", weight=3, opacity=0.7).add_to(m)
            
            if all_points:
                sw = [min(p[0] for p in all_points), min(p[1] for p in all_points)]
                ne = [max(p[0] for p in all_points), max(p[1] for p in all_points)]
                m.fit_bounds([sw, ne])

            if animate:
                # JavaScript for animation
                tracks_json = json.dumps(tracks)
                map_id = m.get_name()
                
                script = f"""
                var tracksData = {tracks_json};
                var polylines = [];
                var animationFrame;
                var currentStep = 0;
                var totalSteps = 1000; 

                function initAnimation() {{
                    // Clear existing polylines
                    polylines.forEach(p => p.remove());
                    polylines = [];
                    
                    tracksData.forEach(track => {{
                        var poly = L.polyline([], {{color: 'red', weight: 4}}).addTo({map_id});
                        polylines.push({{poly: poly, fullPoints: track}});
                    }});
                }}

                function renderStep(step) {{
                    currentStep = step;
                    var progress = currentStep / totalSteps;
                    
                    polylines.forEach(item => {{
                        var count = Math.ceil(item.fullPoints.length * progress);
                        item.poly.setLatLngs(item.fullPoints.slice(0, count));
                    }});
                }}

                function startAnimation() {{
                    initAnimation();
                    currentStep = 0;
                    animate();
                }}

                function animate() {{
                    currentStep++;
                    renderStep(currentStep);

                    var finished = (currentStep >= totalSteps);
                    if (!finished) {{
                        animationFrame = requestAnimationFrame(animate);
                    }} else {{
                        console.log("Animation finished");
                    }}
                }}

                function stopAnimation() {{
                    if (animationFrame) {{
                        cancelAnimationFrame(animationFrame);
                    }}
                }}
                
                window.startGpxAnimation = startAnimation;
                window.stopGpxAnimation = stopAnimation;
                window.renderGpxStep = renderStep;
                window.initGpxAnimation = initAnimation;
                """
                m.get_root().script.add_child(folium.Element(script))

        self.web_view.setHtml(m.get_root().render())

    def open_gpx(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open GPX File", "", "GPX Files (*.gpx)")
        if file_path:
            try:
                with open(file_path, 'r') as gpx_file:
                    gpx = gpxpy.parse(gpx_file)
                    
                self.tracks = []
                for track in gpx.tracks:
                    for segment in track.segments:
                        points = [(p.latitude, p.longitude) for p in segment.points]
                        if points:
                            self.tracks.append(points)
                
                if self.tracks:
                    self.load_map(self.tracks)
                    self.play_btn.setEnabled(True)
                    self.stop_btn.setEnabled(False)
                    self.export_btn.setEnabled(True)
            except Exception as e:
                print(f"Error loading GPX: {e}")

    def play_animation(self):
        self.web_view.loadFinished.connect(self._start_js_animation)
        self.load_map(self.tracks, animate=True)
        self.play_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.export_btn.setEnabled(False)

    def _start_js_animation(self):
        self.web_view.loadFinished.disconnect(self._start_js_animation)
        self.web_view.page().runJavaScript("window.startGpxAnimation();")

    def stop_animation(self):
        # We don't strictly need to call stopGpxAnimation if we are reloading the map,
        # but it's cleaner.
        self.web_view.page().runJavaScript("window.stopGpxAnimation();")
        self.load_map(self.tracks)
        self.play_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.export_btn.setEnabled(True)

    def export_video(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Video", "animation.mp4", "Video Files (*.mp4)")
        if not file_path:
            return

        # Disable buttons
        self.open_btn.setEnabled(False)
        self.play_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.export_btn.setEnabled(False)

        # Prepare map for animation
        loop = QEventLoop()
        self.web_view.loadFinished.connect(loop.quit)
        self.load_map(self.tracks, animate=True)
        loop.exec()
        self.web_view.loadFinished.disconnect(loop.quit)

        # Initialize animation in JS
        self.web_view.page().runJavaScript("window.initGpxAnimation();")
        
        total_steps = 1000 
        temp_dir = tempfile.mkdtemp()
        try:
            for i in range(total_steps + 1):
                # Render step i
                self.web_view.page().runJavaScript(f"window.renderGpxStep({i});", lambda r: loop.quit())
                loop.exec()
                
                # Small delay to ensure rendering is complete
                # QWebEngineView.grab() is usually reliable after JS callback,
                # but Leaflet needs a moment to repaint the canvas.
                QTimer.singleShot(10, loop.quit)
                loop.exec()
                
                frame_path = os.path.join(temp_dir, f"frame_{i:04d}.png")
                pixmap = self.web_view.grab()
                
                # yuv420p requires dimensions to be divisible by 2
                width = pixmap.width()
                height = pixmap.height()
                if width % 2 != 0 or height % 2 != 0:
                    pixmap = pixmap.copy(0, 0, width - (width % 2), height - (height % 2))
                
                pixmap.save(frame_path)
                
                if i % 50 == 0:
                    self.statusBar().showMessage(f"Exporting: {i}/{total_steps} frames...")
                    QApplication.processEvents()

            # Run FFmpeg
            self.statusBar().showMessage("Encoding video...")
            QApplication.processEvents()
            cmd = [
                'ffmpeg', '-y',
                '-framerate', '60', # Using 60fps for smoother video since we have 1000 steps
                '-i', os.path.join(temp_dir, 'frame_%04d.png'),
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"FFmpeg failed with return code {result.returncode}.\nStderr: {result.stderr}")
            
            self.statusBar().showMessage("Export finished!", 5000)
        except Exception as e:
            print(f"Export error: {e}")
            self.statusBar().showMessage(f"Export error: {e}", 5000)
            # Log full error to a file for the user to see if it's too long for status bar
            with open("export_error.log", "w") as f:
                f.write(str(e))
        finally:
            shutil.rmtree(temp_dir)
            self.open_btn.setEnabled(True)
            self.play_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.export_btn.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GPXAnimator()
    window.show()
    sys.exit(app.exec())
