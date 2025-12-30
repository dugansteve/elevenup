# Send Seedline validation email
# Loads the password from User environment variable

$env:SEEDLINE_EMAIL_PASSWORD = [System.Environment]::GetEnvironmentVariable('SEEDLINE_EMAIL_PASSWORD', 'User')

if (-not $env:SEEDLINE_EMAIL_PASSWORD) {
    Write-Host "ERROR: SEEDLINE_EMAIL_PASSWORD not found in User environment variables"
    exit 1
}

Write-Host "Password loaded successfully"
& "C:\Python313\python.exe" "C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\validate_and_email.py"
