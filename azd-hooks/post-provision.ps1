# azd hook attribute indicating that this script should always be run
$env:AZD_RUN_ALWAYS = "true"

Write-Host "Deployed environment $env:AZURE_ENV_NAME successfully."