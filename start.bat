@echo off
setlocal
cd /d "%~dp0"

rem ============================================================
rem  Optional: set your own Python interpreter below (uncomment).
rem  Useful if "python" / "py" are not on PATH.
rem  set "MY_PYTHON=D:\python\python.exe"
rem ============================================================

set "BUNDLED=C:\Users\liyumo\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
set "DPY=D:\python\python.exe"

if defined MY_PYTHON goto :probe_my
goto :probe_dpython

:probe_dpython
if exist "%DPY%" goto :probe_dpython_run
goto :probe_python
:probe_dpython_run
"%DPY%" -c "import tkinter; tkinter.Tk().destroy(); print('__TK_OK__')" 2>nul | findstr /C:"__TK_OK__" >nul
if not errorlevel 1 goto :run_dpython
echo [WARN] D:\python\python.exe has no working Tk; trying next...
goto :probe_python

:probe_my
if exist "%MY_PYTHON%" goto :probe_my_run
echo [ERROR] MY_PYTHON not found: %MY_PYTHON%
goto :fail
:probe_my_run
"%MY_PYTHON%" -c "import tkinter; tkinter.Tk().destroy(); print('__TK_OK__')" 2>nul | findstr /C:"__TK_OK__" >nul
if not errorlevel 1 goto :run_my
echo [WARN] MY_PYTHON has no working Tk; trying others...
goto :probe_python

:probe_python
where python >nul 2>nul
if errorlevel 1 goto :probe_py
python -c "import tkinter; tkinter.Tk().destroy(); print('__TK_OK__')" 2>nul | findstr /C:"__TK_OK__" >nul
if not errorlevel 1 goto :run_python
echo [WARN] 'python' has no working Tk; trying next...
goto :probe_py

:probe_py
where py >nul 2>nul
if errorlevel 1 goto :probe_bundled
py -3 -c "import tkinter; tkinter.Tk().destroy(); print('__TK_OK__')" 2>nul | findstr /C:"__TK_OK__" >nul
if not errorlevel 1 goto :run_py
echo [WARN] 'py -3' has no working Tk; trying next...
goto :probe_bundled

:probe_bundled
if not exist "%BUNDLED%" goto :fail
"%BUNDLED%" -c "import tkinter; tkinter.Tk().destroy(); print('__TK_OK__')" 2>nul | findstr /C:"__TK_OK__" >nul
if not errorlevel 1 goto :run_bundled
goto :fail

:fail
echo [ERROR] No Python with working Tk was found.
echo   - Install Python 3.10+ (official installer includes Tk), or
echo   - Edit start.bat and set MY_PYTHON to a Python that has Tk.
pause
exit /b 1

:run_dpython
echo Launching VPNDefender with: D:\python\python.exe
"%DPY%" app.py
goto :finish

:run_python
echo Launching VPNDefender with: python
python app.py
goto :finish

:run_py
echo Launching VPNDefender with: py -3
py -3 app.py
goto :finish

:run_bundled
echo Launching VPNDefender with: bundled Python
"%BUNDLED%" app.py
goto :finish

:run_my
echo Launching VPNDefender with: %MY_PYTHON%
"%MY_PYTHON%" app.py
goto :finish

:finish
echo.
echo VPNDefender finished (exit code %errorlevel%).
pause
