#!/usr/bin/env python3
"""
Network Monitor & Filter System for Windows
Main entry point for starting the proxy server and web interface.
"""

import sys
import os
import argparse
import threading
import time
import logging
import asyncio
import json
import webbrowser
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.monitor import NetworkFilterManager
from src.filter_addon import NetworkMonitorAddon
from src.web_interface import create_web_app
from src.utils import initialize_database

def setup_logging(log_level='INFO', log_dir='logs'):
    """Configures logging for the application."""
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path / 'network_monitor.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.info("Logging initialized.")

def load_config(config_path='config/filter_config.json'):
    """Loads configuration from a JSON file."""
    defaults = {
        'host': '0.0.0.0',
        'proxy_port': 8080,
        'web_port': 8081,
        'log_level': 'INFO'
    }
    path = Path(config_path)
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                defaults.update(config)
        except (json.JSONDecodeError, IOError) as e:
            logging.warning(f"Could not load config file '{path}': {e}. Using defaults.")
    return defaults

async def start_proxy_server(filter_manager, host, port):
    """Starts the mitmproxy server."""
    from mitmproxy.tools.dump import DumpMaster
    from mitmproxy import options

    opts = options.Options(
        listen_host=host,
        listen_port=port,
        mode=['regular'],
        confdir=str(Path.home() / '.mitmproxy'),
        ssl_insecure=True  # Simplifies certificate handling for this use case
    )

    logging.info(f"Starting proxy server on {host}:{port}")
    master = DumpMaster(opts, with_termlog=False)
    master.addons.add(NetworkMonitorAddon(filter_manager))
    
    try:
        await master.run()
    except KeyboardInterrupt:
        logging.info("Proxy server shutting down.")
        master.shutdown()

def start_web_interface_thread(app, host, port):
    """Runs the Flask web server in a separate thread."""
    logging.info(f"Starting web interface on http://{host}:{port}")
    # Use waitress or another production-ready server for better performance
    # For simplicity, using Flask's built-in server here.
    app.run(host=host, port=port, use_reloader=False, debug=False)

def main():
    """Main function to orchestrate the application startup."""
    config = load_config()
    
    parser = argparse.ArgumentParser(description='Network Monitor & Filter System')
    parser.add_argument('--host', default=config['host'], help='Host address to bind to')
    parser.add_argument('--port', type=int, default=config['proxy_port'], help='Proxy server port')
    parser.add_argument('--web-port', type=int, default=config['web_port'], help='Web interface port')
    parser.add_argument('--log-level', default=config['log_level'], choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='Logging level')
    
    args = parser.parse_args()
    
    # Setup logging and directories
    setup_logging(args.log_level)
    Path('data').mkdir(exist_ok=True)
    
    # Initialize components
    filter_manager = NetworkFilterManager()
    app = create_web_app(filter_manager)
    
    # Start web interface in a daemon thread
    web_thread = threading.Thread(
        target=start_web_interface_thread,
        args=(app, '0.0.0.0', args.web_port),
        daemon=True
    )
    web_thread.start()

    # Give the web server a moment to start and open browser
    time.sleep(1)
    webbrowser.open(f"http://localhost:{args.web_port}")
    
    # Start proxy server in the main thread (blocking)
    try:
        asyncio.run(start_proxy_server(filter_manager, args.host, args.port))
    except Exception as e:
        logging.critical(f"A critical error occurred: {e}", exc_info=True)
        print(f"Failed to start proxy server: {e}")
        sys.exit(1)
    
    print("System shutting down.")

if __name__ == '__main__':
    # Mitmproxy can have issues with multiprocessing on Windows when frozen
    # This check helps prevent recursive execution
    if sys.platform == 'win32':
        from multiprocessing import freeze_support
        freeze_support()
        
    main()