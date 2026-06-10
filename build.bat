@echo off
setlocal EnableExtensions

rem ============================================================
rem build.bat - Gera o pacote portatil da Barra de Uso de IA
rem (adaptado do build.bat do PomodoroTimer)
rem ============================================================

set "APP_NAME=BarraUsoIA"
set "DIST_ROOT=C:\tmp\BarraUsoIA_dist"
set "WORK_ROOT=C:\tmp\BarraUsoIA_build"
set "RELEASE_ROOT=C:\tmp\BarraUsoIA_release"
set "SPEC_ROOT=build\spec"
set "APP_DIR=%DIST_ROOT%\%APP_NAME%"
set "EXE_PATH=%APP_DIR%\%APP_NAME%.exe"
set "ZIP_PATH=%RELEASE_ROOT%\%APP_NAME%-portable.zip"

echo ============================================================
echo  Barra de Uso de IA - Build e pacote portatil
echo ============================================================
echo.

echo [1/5] Preparando ambiente de build...
cd /d "%~dp0"

if not exist "main.py" (
    echo ERRO: main.py nao encontrado. Rode este script pela raiz do projeto.
    exit /b 1
)

if not exist "assets\icon.png" (
    echo ERRO: assets\icon.png nao encontrado. O icone e necessario para o executavel.
    exit /b 1
)

set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py"

if "%PYTHON_CMD%"=="" (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if "%PYTHON_CMD%"=="" (
    echo ERRO: Python nao encontrado no PATH.
    echo Instale o Python 3.11+ ou habilite o launcher py.
    exit /b 1
)

echo Python selecionado: %PYTHON_CMD%
%PYTHON_CMD% -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
    echo ERRO: PyInstaller nao esta instalado neste Python.
    echo Execute: %PYTHON_CMD% -m pip install pyinstaller
    exit /b 1
)

echo [2/5] Limpando artefatos anteriores...

rem A distribuicao final fica fora do Google Drive porque a pasta sincronizada
rem pode bloquear a criacao do .exe.
if exist "build" rmdir /s /q "build"
if exist "%WORK_ROOT%" rmdir /s /q "%WORK_ROOT%"
if exist "%DIST_ROOT%" rmdir /s /q "%DIST_ROOT%"
if exist "%RELEASE_ROOT%" rmdir /s /q "%RELEASE_ROOT%"

if exist "%DIST_ROOT%" (
    echo.
    echo ERRO: Nao foi possivel limpar %DIST_ROOT%.
    echo Feche o %APP_NAME%.exe e qualquer janela usando essa pasta, depois rode o build novamente.
    exit /b 1
)

mkdir "%RELEASE_ROOT%" >nul 2>nul
if errorlevel 1 (
    echo ERRO: Nao foi possivel criar %RELEASE_ROOT%.
    exit /b 1
)

echo [3/5] Rodando PyInstaller...

%PYTHON_CMD% -m PyInstaller -y ^
  --clean ^
  --onedir ^
  --windowed ^
  --distpath "%DIST_ROOT%" ^
  --workpath "%WORK_ROOT%" ^
  --specpath "%SPEC_ROOT%" ^
  --name %APP_NAME% ^
  --icon="%CD%\assets\icon.png" ^
  --add-data "%CD%\assets;assets" ^
  --hidden-import PyQt6.QtCore ^
  --hidden-import PyQt6.QtGui ^
  --hidden-import PyQt6.QtWidgets ^
  --hidden-import PyQt6.sip ^
  main.py

if errorlevel 1 (
    echo.
    echo ERRO: PyInstaller falhou. O executavel final nao foi atualizado.
    exit /b 1
)

if not exist "%EXE_PATH%" (
    echo.
    echo ERRO: Build terminou, mas o executavel final nao foi encontrado.
    exit /b 1
)

echo [4/5] Preparando arquivos de distribuicao...

if exist "README.md" copy /y "README.md" "%APP_DIR%\README.md" >nul

echo [5/5] Gerando pacote .zip portatil...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Compress-Archive -LiteralPath '%APP_DIR%' -DestinationPath '%ZIP_PATH%' -Force"

if not exist "%ZIP_PATH%" (
    echo.
    echo AVISO: O executavel foi gerado, mas o arquivo .zip nao foi encontrado.
    echo Executavel disponivel em: %EXE_PATH%
    exit /b 1
)

echo.
echo Build concluido com sucesso.
echo.
echo Executavel: %EXE_PATH%
echo Pacote portatil: %ZIP_PATH%
echo.
