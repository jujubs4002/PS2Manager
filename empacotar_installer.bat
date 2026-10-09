@echo off
title Construindo Instalador do PS2 Manager
color 0B

echo ========================================================
echo   COMPILANDO INSTALADOR PROFISSIONAL (MODO ONE-FILE)
echo ========================================================
echo.

echo Verificando e instalando PyInstaller via inicializador 'py'...
py -m pip install pyinstaller customtkinter
echo.

echo Iniciando a compactacao de TODOS os arquivos na memoria...
echo Aguarde...
echo.

REM VEJA A CORRECAO AQUI:
REM O --version-file puxa o arquivo com o codigo "version_info.txt"
REM O --add-data puxa o texto simples "version.txt" pro seu instalador ler

py -m PyInstaller ^
  --noconfirm ^
  --onefile ^
  --windowed ^
  --uac-admin ^
  --icon "icon.ico" ^
  --version-file "version_info.txt" ^
  --add-data "PS2Manager.exe;." ^
  --add-data "pcsx2;pcsx2" ^
  --add-data "sounds;sounds" ^
  --add-data "VER;VER" ^
  --add-data "scripts;scripts" ^
  --add-data "DO NOT DELETE DATA.JSON.txt;." ^
  --add-data "version.txt;." ^
  --copy-metadata customtkinter ^
  --name "Installer_PS2Manager" ^
  custom_installer.py

echo.
echo ========================================================
echo COMPILACAO FINALIZADA! 
echo O arquivo "Installer_PS2Manager.exe" esta na pasta "dist".
echo ========================================================
pause