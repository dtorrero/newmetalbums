#!/usr/bin/env python3
"""
Development Startup Script
Starts both backend (FastAPI) and frontend (React) for development
"""

import subprocess
import threading
import time
import sys
import os
import signal
from pathlib import Path

class DevServer:
    def __init__(self):
        self.backend_process = None
        self.frontend_process = None
        self.project_root = Path(__file__).parent
        self.frontend_dir = self.project_root / "frontend"
        
    def start_backend(self):
        """Start the FastAPI backend server"""
        print("🚀 Starting FastAPI backend on http://127.0.0.1:8000")
        try:
            self.backend_process = subprocess.Popen(
                [sys.executable, "daily_orchestrator.py", "--test"],
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Stream backend output
            def stream_backend():
                for line in iter(self.backend_process.stdout.readline, ''):
                    print(f"[BACKEND] {line.rstrip()}")
            
            backend_thread = threading.Thread(target=stream_backend, daemon=True)
            backend_thread.start()
            
        except Exception as e:
            print(f"❌ Failed to start backend: {e}")
            return False
        return True
    
    def start_frontend(self):
        """Start the React frontend development server"""
        print("🎨 Starting React frontend on http://localhost:3000")
        
        # Check if node_modules exists
        if not (self.frontend_dir / "node_modules").exists():
            print("📦 Installing frontend dependencies...")
            npm_install = subprocess.run(
                ["npm", "install"],
                cwd=self.frontend_dir,
                capture_output=True,
                text=True
            )
            if npm_install.returncode != 0:
                print(f"❌ npm install failed: {npm_install.stderr}")
                return False
            print("✅ Frontend dependencies installed")
        
        try:
            # Set environment variable to avoid browser auto-opening
            env = os.environ.copy()
            env["BROWSER"] = "none"
            
            self.frontend_process = subprocess.Popen(
                ["npm", "start"],
                cwd=self.frontend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env
            )
            
            # Stream frontend output
            def stream_frontend():
                for line in iter(self.frontend_process.stdout.readline, ''):
                    if line.strip():  # Filter empty lines
                        print(f"[FRONTEND] {line.rstrip()}")
            
            frontend_thread = threading.Thread(target=stream_frontend, daemon=True)
            frontend_thread.start()
            
        except Exception as e:
            print(f"❌ Failed to start frontend: {e}")
            return False
        return True
    
    def wait_for_servers(self):
        """Wait for both servers to be ready"""
        print("⏳ Waiting for servers to start...")
        time.sleep(3)
        
        # Check backend health
        try:
            import requests
            response = requests.get("http://127.0.0.1:8000/api/health", timeout=5)
            if response.status_code == 200:
                print("✅ Backend is ready")
            else:
                print("⚠️ Backend may not be fully ready")
        except:
            print("⚠️ Backend health check failed (may still be starting)")
        
        print("✅ Frontend should be starting...")
        time.sleep(2)
    
    def show_urls(self):
        """Display access URLs"""
        print("\n" + "="*60)
        print("🎯 DEVELOPMENT SERVERS READY")
        print("="*60)
        print("📊 Backend API:     http://127.0.0.1:8000")
        print("📊 API Docs:        http://127.0.0.1:8000/docs")
        print("🎨 Frontend:        http://localhost:3000")
        print("="*60)
        print("💡 The frontend will proxy API requests to the backend")
        print("🔄 Both servers will auto-reload on file changes")
        print("⏹️  Press Ctrl+C to stop both servers")
        print("="*60 + "\n")
    
    def cleanup(self):
        """Stop both servers"""
        print("\n🛑 Stopping development servers...")
        
        if self.frontend_process:
            try:
                self.frontend_process.terminate()
                self.frontend_process.wait(timeout=5)
                print("✅ Frontend stopped")
            except:
                self.frontend_process.kill()
                print("🔪 Frontend force-killed")
        
        if self.backend_process:
            try:
                self.backend_process.terminate()
                self.backend_process.wait(timeout=5)
                print("✅ Backend stopped")
            except:
                self.backend_process.kill()
                print("🔪 Backend force-killed")
    
    def start(self):
        """Start both development servers"""
        print("🚀 Starting Metal Albums Development Environment")
        print("="*60)
        
        # Start backend first
        if not self.start_backend():
            print("❌ Failed to start backend")
            return 1
        
        time.sleep(2)  # Give backend time to start
        
        # Start frontend
        if not self.start_frontend():
            print("❌ Failed to start frontend")
            self.cleanup()
            return 1
        
        # Wait and show status
        self.wait_for_servers()
        self.show_urls()
        
        # Keep running until interrupted
        try:
            while True:
                # Check if processes are still running
                if self.backend_process and self.backend_process.poll() is not None:
                    print("❌ Backend process died")
                    break
                if self.frontend_process and self.frontend_process.poll() is not None:
                    print("❌ Frontend process died")
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()
        
        return 0

def main():
    """Main entry point"""
    dev_server = DevServer()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        dev_server.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    return dev_server.start()

if __name__ == "__main__":
    sys.exit(main())
