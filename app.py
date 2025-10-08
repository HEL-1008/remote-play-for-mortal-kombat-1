from flask import Flask, render_template_string, request, jsonify, Response
import pydirectinput
import time
import cv2
import numpy as np
import pyautogui
import threading
import gc

app = Flask(__name__)
pydirectinput.FAILSAFE = False
pydirectinput.PAUSE = 0.005

# Global variables
streaming = False
frame_delay = 1.0 / 60
quality = 40

def generate_screen_frames():
    """Generate frames with memory optimization"""
    global streaming, frame_delay, quality
    
    frame_count = 0
    while streaming:
        try:
            start_time = time.time()
            
            # Capture screen
            screenshot = pyautogui.screenshot()
            
            # Convert and resize
            frame = np.array(screenshot)
            height, width = frame.shape[:2]
            new_width = width // 2
            new_height = height // 2
            frame = cv2.resize(frame, (new_width, new_height))
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # Encode with quality
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            # Memory cleanup every 100 frames
            frame_count += 1
            if frame_count % 100 == 0:
                gc.collect()
            
            # Maintain FPS
            processing_time = time.time() - start_time
            sleep_time = max(0.001, frame_delay - processing_time)
            time.sleep(sleep_time)
            
        except Exception as e:
            print(f"Screen capture error: {e}")
            time.sleep(0.1)

@app.route('/screen_stream')
def screen_stream():
    """Screen streaming route"""
    global streaming
    streaming = True
    return Response(generate_screen_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/stop_stream')
def stop_stream():
    """Stop the screen stream"""
    global streaming
    streaming = False
    return jsonify({'status': 'stream stopped'})

@app.route('/restart_stream')
def restart_stream():
    """Restart stream to fix glitches"""
    global streaming
    streaming = False
    time.sleep(0.5)
    streaming = True
    return jsonify({'status': 'stream restarted'})

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Gamepad Pro | Mortal Kombat 1</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #ff0000;
            --secondary: #2c3e50;
            --dark: #1a1a1a;
            --light: #f5f5f5;
        }
        * {
            box-sizing: border-box;
            touch-action: manipulation;
            user-select: none;
            -webkit-tap-highlight-color: transparent;
        }
        body {
            margin: 0;
            padding: 0;
            background-color: var(--dark);
            color: var(--light);
            font-family: 'Orbitron', sans-serif;
            overflow: hidden;
            height: 100vh;
            width: 100vw;
            position: relative;
        }
        
        /* Stream Container */
        .stream-container {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 1;
            background: #000;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        #streamVideo {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }
        
        /* Overlay Controls */
        .controls-overlay {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 2;
            pointer-events: none;
        }
        
        .gamepad-container {
            position: relative;
            width: 100%;
            height: 100%;
            padding: 15px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            pointer-events: none;
        }
        
        /* ЛЕДЬ ЗАМІТНІ кнопки руху */
        .movement-buttons {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            grid-template-rows: repeat(3, 1fr);
            gap: 12px;
            width: 220px;
            height: 220px;
            margin-left: 20px;
            margin-bottom: 25px;
            pointer-events: auto;
        }
        
        .movement-btn {
            width: 65px;
            height: 65px;
            border-radius: 12px;
            background: rgba(10, 10, 10, 0.3);
            border: 2px solid rgba(255, 0, 0, 0.3);
            color: rgba(255, 255, 255, 0.6);
            font-size: 1.4rem;
            display: flex;
            justify-content: center;
            align-items: center;
            font-weight: bold;
            pointer-events: auto;
            transition: all 0.1s ease;
            touch-action: manipulation;
        }
        
        .movement-btn.center {
            background: rgba(20, 20, 20, 0.2);
            border-color: rgba(102, 102, 102, 0.3);
        }
        
        /* ЛЕДЬ ЗАМІТНІ кнопки дій */
        .action-buttons {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            grid-template-rows: repeat(2, 1fr);
            gap: 15px;
            width: 240px;
            height: 160px;
            margin-right: 25px;
            margin-bottom: 30px;
            pointer-events: auto;
        }
        
        .action-btn {
            width: 70px;
            height: 70px;
            border-radius: 50%;
            background: rgba(10, 10, 10, 0.3);
            border: 2px solid rgba(255, 0, 0, 0.3);
            color: rgba(255, 255, 255, 0.6);
            font-size: 1.3rem;
            display: flex;
            justify-content: center;
            align-items: center;
            font-weight: bold;
            pointer-events: auto;
            transition: all 0.1s ease;
            touch-action: manipulation;
        }
        
        /* Control Panel - тільки одна кнопка */
        .control-panel {
            position: absolute;
            top: 15px;
            left: 15px;
            z-index: 3;
            pointer-events: auto;
        }
        
        .control-btn {
            padding: 8px 12px;
            background: rgba(0, 0, 0, 0.4);
            border: 2px solid rgba(255, 0, 0, 0.4);
            color: rgba(255, 255, 255, 0.7);
            border-radius: 6px;
            font-family: 'Orbitron', sans-serif;
            font-size: 0.7rem;
            font-weight: bold;
            cursor: pointer;
        }
        
        .status-panel {
            position: absolute;
            top: 15px;
            right: 15px;
            display: flex;
            flex-direction: column;
            gap: 5px;
            z-index: 3;
        }
        
        .status-item {
            background: rgba(0, 0, 0, 0.4);
            padding: 6px 10px;
            border-radius: 6px;
            border: 2px solid rgba(0, 255, 0, 0.4);
            font-size: 0.7rem;
            text-align: center;
            color: rgba(255, 255, 255, 0.7);
        }
        
        .fps-counter {
            border-color: rgba(255, 255, 0, 0.4);
            color: rgba(255, 255, 0, 0.7);
        }
        
        .debug-info {
            position: absolute;
            bottom: 60px;
            left: 15px;
            background: rgba(0, 0, 0, 0.4);
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.8rem;
            z-index: 3;
            max-width: 250px;
            color: rgba(255, 255, 255, 0.7);
        }
        
        .connection-status {
            position: absolute;
            bottom: 15px;
            left: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(0, 0, 0, 0.4);
            padding: 8px 12px;
            border-radius: 6px;
            z-index: 3;
            font-size: 0.8rem;
            color: rgba(255, 255, 255, 0.7);
        }
        
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: rgba(0, 255, 0, 0.6);
            animation: pulse 1s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 0.6; }
            50% { opacity: 0.3; }
            100% { opacity: 0.6; }
        }
    </style>
</head>
<body>
    <!-- Stream Video -->
    <div class="stream-container">
        <img id="streamVideo" src="/screen_stream" alt="Game Stream">
    </div>
    
    <!-- Control Panel - тільки одна кнопка -->
    <div class="control-panel">
        <button class="control-btn" onclick="restartStream()">🔄 Restart Stream</button>
    </div>
    
    <!-- Status Panel -->
    <div class="status-panel">
        <div class="status-item" id="streamStatus">🟢 STREAM ACTIVE</div>
        <div class="status-item fps-counter" id="fpsCounter">FPS: --</div>
    </div>
    
    <div class="debug-info" id="debugInfo">
        ✅ Ready - Use transparent buttons!
    </div>
    
    <!-- Game Controls Overlay -->
    <div class="controls-overlay">
        <div class="gamepad-container">
            <!-- ЛЕДЬ ЗАМІТНІ кнопки руху -->
            <div class="movement-buttons">
                <div class="movement-btn center"></div>
                <div class="movement-btn" data-key="w">W</div>
                <div class="movement-btn center"></div>
                
                <div class="movement-btn" data-key="a">A</div>
                <div class="movement-btn center"></div>
                <div class="movement-btn" data-key="d">D</div>
                
                <div class="movement-btn center"></div>
                <div class="movement-btn" data-key="s">S</div>
                <div class="movement-btn center"></div>
            </div>

            <!-- ЛЕДЬ ЗАМІТНІ кнопки дій (O і L поміняні місцями) -->
            <div class="action-buttons">
                <div class="action-btn" data-key="i">I</div>
                <div class="action-btn" data-key="l">L</div>
                <div class="action-btn" data-key="semicolon">;</div>
                
                <div class="action-btn" data-key="j">J</div>
                <div class="action-btn" data-key="k">K</div>
                <div class="action-btn" data-key="o">O</div>
            </div>
        </div>
        
        <div class="connection-status">
            <div class="status-dot"></div>
            <span>CONTROLLER CONNECTED</span>
        </div>
    </div>

    <script>
        const videoElement = document.getElementById('streamVideo');
        const statusElement = document.getElementById('streamStatus');
        const fpsElement = document.getElementById('fpsCounter');
        const debugElement = document.getElementById('debugInfo');
        
        let frameCount = 0;
        let lastFpsTime = Date.now();
        let currentFps = 0;
        let activeKeys = new Set();

        function restartStream() {
            debugElement.textContent = '🔄 Restarting stream...';
            fetch('/restart_stream')
                .then(() => {
                    setTimeout(() => {
                        refreshStream();
                        debugElement.textContent = '✅ Stream restarted';
                    }, 500);
                })
                .catch(err => {
                    debugElement.textContent = '❌ Restart failed';
                });
        }

        function refreshStream() {
            const newUrl = '/screen_stream?t=' + Date.now();
            videoElement.src = newUrl;
        }

        function releaseAllKeys() {
            const keys = ['w', 'a', 's', 'd', 'i', 'o', ';', 'j', 'k', 'l'];
            keys.forEach(key => {
                sendKey(key, 'up');
            });
            activeKeys.clear();
        }

        // FPS counter
        function updateFps() {
            frameCount++;
            const now = Date.now();
            const delta = now - lastFpsTime;
            
            if (delta >= 1000) {
                currentFps = Math.round((frameCount * 1000) / delta);
                fpsElement.textContent = `FPS: ${currentFps}`;
                
                if (currentFps < 30) {
                    fpsElement.style.borderColor = 'rgba(255, 0, 0, 0.4)';
                    fpsElement.style.color = 'rgba(255, 0, 0, 0.7)';
                } else if (currentFps < 50) {
                    fpsElement.style.borderColor = 'rgba(255, 255, 0, 0.4)';
                    fpsElement.style.color = 'rgba(255, 255, 0, 0.7)';
                } else {
                    fpsElement.style.borderColor = 'rgba(0, 255, 0, 0.4)';
                    fpsElement.style.color = 'rgba(0, 255, 0, 0.7)';
                }
                
                frameCount = 0;
                lastFpsTime = now;
            }
            requestAnimationFrame(updateFps);
        }

        // Gamepad input
        function sendKey(key, type) {
            const actualKey = key === 'semicolon' ? ';' : key;
            
            if (type === 'down') {
                activeKeys.add(actualKey);
            } else {
                activeKeys.delete(actualKey);
            }
            
            debugElement.textContent = `Active: ${Array.from(activeKeys).join(', ') || 'none'}`;
            
            fetch('/input', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({key: actualKey, type: type})
            })
            .then(response => response.json())
            .then(data => {
                if (data.status !== 'success') {
                    console.error('Server error:', data);
                }
            })
            .catch(error => {
                console.error('Network error:', error);
                debugElement.textContent = '❌ Connection error';
            });
        }

        // Button handling
        function setupButtons() {
            const buttons = document.querySelectorAll('.movement-btn, .action-btn');
            console.log(`Setting up ${buttons.length} TRANSPARENT buttons`);
            
            buttons.forEach(btn => {
                const key = btn.getAttribute('data-key');
                if (!key) return;
                
                // Touch events
                btn.addEventListener('touchstart', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.style.background = 'rgba(255, 0, 0, 0.6)';
                    this.style.transform = 'scale(0.95)';
                    sendKey(key, 'down');
                }, { passive: false });
                
                btn.addEventListener('touchend', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.style.background = '';
                    this.style.transform = '';
                    sendKey(key, 'up');
                }, { passive: false });
                
                btn.addEventListener('touchcancel', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.style.background = '';
                    this.style.transform = '';
                    sendKey(key, 'up');
                }, { passive: false });
                
                // Mouse events
                btn.addEventListener('mousedown', function(e) {
                    e.preventDefault();
                    this.style.background = 'rgba(255, 0, 0, 0.6)';
                    this.style.transform = 'scale(0.95)';
                    sendKey(key, 'down');
                });
                
                btn.addEventListener('mouseup', function(e) {
                    e.preventDefault();
                    this.style.background = '';
                    this.style.transform = '';
                    sendKey(key, 'up');
                });
                
                btn.addEventListener('mouseleave', function(e) {
                    if (this.style.background === 'rgba(255, 0, 0, 0.6)') {
                        this.style.background = '';
                        this.style.transform = '';
                        sendKey(key, 'up');
                    }
                });
            });
        }

        // Safety features
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'hidden') {
                releaseAllKeys();
            }
        });
        
        window.addEventListener('beforeunload', () => {
            releaseAllKeys();
        });
        
        // Auto-cleanup every 2 minutes
        setInterval(() => {
            if (activeKeys.size > 0) {
                console.log('Auto-cleaning active keys:', activeKeys);
            }
        }, 120000);
        
        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            setupButtons();
            updateFps();
            
            setTimeout(() => {
                refreshStream();
                debugElement.textContent = '✅ Ready - Use transparent buttons!';
            }, 500);
        });
        
        // Stream events
        videoElement.addEventListener('load', () => {
            statusElement.textContent = '🟢 STREAM ACTIVE';
            statusElement.style.borderColor = 'rgba(0, 255, 0, 0.4)';
        });
        
        videoElement.addEventListener('error', () => {
            statusElement.textContent = '🔴 STREAM ERROR';
            statusElement.style.borderColor = 'rgba(255, 0, 0, 0.4)';
            debugElement.textContent = '❌ Stream error - try restarting';
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/input', methods=['POST'])
def handle_input():
    try:
        data = request.get_json()
        key = data.get('key')
        action_type = data.get('type')
        
        print(f"Input: {key} {action_type}")
        
        if action_type == 'up':
            pydirectinput.keyUp(key)
        elif action_type == 'down':
            pydirectinput.keyDown(key)
            
        return jsonify({'status': 'success', 'key': key, 'action': action_type})
        
    except Exception as e:
        print(f"Error in /input: {e}")
        # Emergency key release
        for k in ['w', 'a', 's', 'd', 'i', 'o', ';', 'j', 'k', 'l']:
            try:
                pydirectinput.keyUp(k)
            except:
                pass
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    print("🎮 MORTAL KOMBAT 1 - FINAL VERSION")
    print("🔄 Only one button: Restart Stream")
    print("🔀 Swapped O and L buttons")
    print("🎯 Very transparent buttons - barely visible")
    print("📱 Open http://[YOUR_IP]:5000 on your phone")
    app.run(host='0.0.0.0', port=5000, threaded=True)