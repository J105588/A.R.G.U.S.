@echo off  
echo ========================================  
echo Network Monitor Setup for Windows  
echo ========================================  
echo.  

echo 1. Checking for Python...  
python --version >nul 2>&1  
if %errorlevel% neq 0 (  
    echo [ERROR] Python is not installed or not in PATH.  
    echo Please install Python from https://python.org and ensure "Add Python to PATH" is checked.  
    pause  
    exit /b 1  
)  
echo Python found.  
echo.  

echo 2. Creating virtual environment...  
if not exist "venv" (  
    python -m venv venv  
    echo Virtual environment 'venv' created.  
) else (  
    echo Virtual environment 'venv' already exists.  
)  
echo.  

echo 3. Activating virtual environment and installing dependencies...  
call venv\Scripts\activate.bat  
pip install -r requirements.txt  
if %errorlevel% neq 0 (  
    echo [ERROR] Failed to install dependencies from requirements.txt.  
    pause  
    exit /b 1  
)  
echo Dependencies installed successfully.  
echo.  

echo 4. Creating necessary directories...  
if not exist "config" mkdir config  
if not exist "logs" mkdir logs  
if not exist "data" mkdir data  
echo.  

echo 5. Creating default configuration files...  
if not exist "config\blocked_domains.txt" (  
    echo # Enter one domain to block per line > config\blocked_domains.txt  
    echo example-social.com >> config\blocked_domains.txt  
    echo example-video.com >> config\blocked_domains.txt  
)  

if not exist "config\blocked_keywords.txt" (  
    echo # Enter one keyword to block per line > config\blocked_keywords.txt  
    echo bad-word >> config\blocked_keywords.txt  
    echo distraction >> config\blocked_keywords.txt  
)  

if not exist "config\filter_config.json" (  
    echo { > config\filter_config.json  
    echo   "filtering_enabled": true, >> config\filter_config.json  
    echo   "web_port": 8081, >> config\filter_config.json  
    echo   "proxy_port": 8080, >> config\filter_config.json  
    echo   "host": "0.0.0.0", >> config\filter_config.json  
    echo   "log_level": "INFO" >> config\filter_config.json  
    echo } >> config\filter_config.json  
)  
echo Default configuration files created.  
echo.  

echo 6. Checking Windows Firewall settings...  
netsh advfirewall firewall show rule name="Network Monitor Proxy" >nul  
if %errorlevel% neq 0 (  
    echo Adding firewall rule for Network Monitor ports (8080-8081)...  
    netsh advfirewall firewall add rule name="Network Monitor Proxy" dir=in action=allow protocol=TCP localport=8080-8081  
    echo Firewall rule added.  
) else (  
    echo Firewall rule 'Network Monitor Proxy' already exists.  
)  
echo.  

echo ========================================  
echo Setup Complete!  
echo ========================================  
echo.  
echo To start the system, run:  
echo   run.bat  
echo.  
echo Access the web interface at: http://localhost:8081  
echo ========================================  
pause  