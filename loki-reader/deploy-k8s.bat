@echo off
setlocal enabledelayedexpansion

:: Set variables
set IMAGE_NAME=loki-reader
set IMAGE_TAG=latest
set EXPORT_PATH=.\exported-images
set NAMESPACE=monitoring
set LATEST_IMAGE=

:: Find the most recent exported image
for /f "delims=" %%i in ('dir /b /o-d "%EXPORT_PATH%\%IMAGE_NAME%_*.tar" 2^>nul') do (
    set "LATEST_IMAGE=%%i"
    goto :found
)
:found

if "%LATEST_IMAGE%"=="" (
    echo Error: No exported image found in %EXPORT_PATH%
    exit /b 1
)

echo Found image: %LATEST_IMAGE%

:: Load the image into local registry
echo Loading image into local registry...
podman load -i "%EXPORT_PATH%\%LATEST_IMAGE%"
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to load image
    exit /b 1
)

:: Create namespace if it doesn't exist
echo Creating namespace if it doesn't exist...
kubectl create namespace %NAMESPACE% --dry-run=client -o yaml | kubectl apply -f -

:: Create ConfigMap from .env file
echo Creating ConfigMap from .env file...
kubectl create configmap loki-reader-config --from-file=.env -n %NAMESPACE% --dry-run=client -o yaml | kubectl apply -f -

:: Apply Kubernetes deployment
echo Creating Kubernetes deployment...
(
echo apiVersion: apps/v1
echo kind: Deployment
echo metadata:
echo   name: loki-reader
echo   namespace: %NAMESPACE%
echo spec:
echo   replicas: 1
echo   selector:
echo     matchLabels:
echo       app: loki-reader
echo   template:
echo     metadata:
echo       labels:
echo         app: loki-reader
echo     spec:
echo       containers:
echo       - name: loki-reader
echo         image: %IMAGE_NAME%:%IMAGE_TAG%
echo         imagePullPolicy: IfNotPresent
echo         envFrom:
echo         - configMapRef:
echo             name: loki-reader-config
echo         volumeMounts:
echo         - name: logs
echo           mountPath: /app/logs
echo       volumes:
echo       - name: logs
echo         emptyDir: {}
) > deployment.yaml

kubectl apply -f deployment.yaml
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to apply deployment
    exit /b 1
)

:: Clean up temporary files
del deployment.yaml

echo Deployment completed successfully.
echo You can check the status with: kubectl get pods -n %NAMESPACE%
echo View logs with: kubectl logs -f deployment/loki-reader -n %NAMESPACE% 