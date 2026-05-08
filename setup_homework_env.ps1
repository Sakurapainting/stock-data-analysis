$ErrorActionPreference = "Stop"

$envName = "iot_hw1"

Write-Host "Creating conda environment: $envName"
conda create -n $envName python=3.12 -y

Write-Host "Installing project requirements"
conda run -n $envName python -m pip install -r requirements.txt

Write-Host "Verifying runtime dependencies"
conda run -n $envName python -c "import pymysql, tushare, matplotlib, pandas, numpy; print('runtime ok')"

Write-Host "Verifying pylint"
conda run -n $envName python -m pylint --version

Write-Host "Environment setup completed."
