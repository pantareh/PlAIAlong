#!/usr/bin/env python3
"""
PlAIAlong Main Entry Point - Python Application
"""
import sys
import os
import yaml
import signal
import subprocess
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from session_state import SessionStateManager
from input_listener import InputListener
from local_generator import LocalGenerator
from cloud_manager import CloudManager


class PlAIAlongApp:
    """Main application class."""
    
    def __init__(self, config_path: str):
        self.running = False
        self.cpp_process = None
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Initialize components
        self.ssm = SessionStateManager(
            self.config['audio']['shared_memory_name']
        )
        
        self.input_listener = InputListener(self.ssm, self.config)
        self.local_generator = LocalGenerator(self.ssm, self.config)
        self.cloud_manager = CloudManager(self.ssm, self.config)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print("\nShutting down...")
        self.stop()
        sys.exit(0)
    
    def start_cpp_process(self):
        """Start the C++ audio engine process."""
        try:
            # Find C++ executable
            cpp_exe = None
            if os.name == 'nt':  # Windows
                cpp_exe = Path(__file__).parent.parent.parent / "build" / "bin" / "plaialong_audio.exe"
            else:  # Linux/Mac
                cpp_exe = Path(__file__).parent.parent.parent / "build" / "bin" / "plaialong_audio"
            
            if not cpp_exe.exists():
                print(f"Warning: C++ executable not found at {cpp_exe}")
                print("Running in Python-only mode (simulation)")
                return None
            
            # Start process
            self.cpp_process = subprocess.Popen(
                [str(cpp_exe)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print(f"Started C++ audio engine (PID: {self.cpp_process.pid})")
            return self.cpp_process
            
        except Exception as e:
            print(f"Error starting C++ process: {e}")
            return None
    
    def start(self):
        """Start the application."""
        print("PlAIAlong Starting...")
        
        # Initialize shared memory (create it)
        if not self.ssm.init_shared_state(create=True):
            print("Error: Failed to initialize shared memory")
            return False
        
        # Set initial state
        self.ssm.set_system_running(True)
        self.ssm.update_musical_context(
            key=0.0,  # C major
            tempo=self.config['session']['default_tempo']
        )
        
        # Start C++ process
        self.start_cpp_process()
        
        # Give C++ process time to attach to shared memory
        time.sleep(0.5)
        
        # Start Python components
        print("Starting Python components...")
        self.input_listener.start()
        self.local_generator.start()
        self.cloud_manager.start()
        
        self.running = True
        print("PlAIAlong is running. Press Ctrl+C to stop.")
        
        # Main loop
        try:
            while self.running:
                # Check if C++ process is still running
                if self.cpp_process and self.cpp_process.poll() is not None:
                    print("C++ process exited")
                    break
                
                # Update loop timer in SSM (simplified for MVP)
                # In production, this would be driven by audio clock
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        """Stop the application."""
        if not self.running:
            return
        
        self.running = False
        
        print("Stopping components...")
        
        # Stop Python components
        self.input_listener.stop()
        self.local_generator.stop()
        self.cloud_manager.stop()
        
        # Stop C++ process
        if self.cpp_process:
            self.cpp_process.terminate()
            try:
                self.cpp_process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self.cpp_process.kill()
            print("C++ process stopped")
        
        # Close shared memory
        self.ssm.close()
        
        print("Shutdown complete")


def main():
    """Main entry point."""
    # Find config file
    script_dir = Path(__file__).parent
    config_path = script_dir.parent / "config" / "config.yaml"
    
    if not config_path.exists():
        print(f"Error: Config file not found at {config_path}")
        return 1
    
    # Create and run app
    app = PlAIAlongApp(str(config_path))
    if app.start():
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
