@echo off
setlocal enabledelayedexpansion

:: Set variables
set IMAGE_NAME=loki-reader
set IMAGE_TAG=latest
set EXPORT_PATH=.\exported-images
set TIMESTAMP=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=!TIMESTAMP: =0!

echo Building image %IMAGE_NAME%:%IMAGE_TAG%...
podman build -t %IMAGE_NAME%:%IMAGE_TAG% .

if %ERRORLEVEL% neq 0 (
    echo Error: Image build failed
    exit /b 1
)

echo Image built successfully.

:: Create export directory if it doesn't exist
if not exist "%EXPORT_PATH%" mkdir "%EXPORT_PATH%"

echo Exporting image to %EXPORT_PATH%\%IMAGE_NAME%_%TIMESTAMP%.tar...
podman save -o "%EXPORT_PATH%\%IMAGE_NAME%_%TIMESTAMP%.tar" %IMAGE_NAME%:%IMAGE_TAG%

if %ERRORLEVEL% neq 0 (
    echo Error: Image export failed
    exit /b 1
)

echo Image exported successfully to %EXPORT_PATH%\%IMAGE_NAME%_%TIMESTAMP%.tar
echo Build and export process completed. 