[CmdletBinding()]
param(
    [ValidateSet("transporte_frutas", "transporte_frutas_tmp_migraciones")][string]$DatabaseName,
    [string]$EnvFile = (Join-Path (Split-Path $PSScriptRoot -Parent | Split-Path -Parent) ".env")
)

$ErrorActionPreference = "Stop"
$backendRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$backupDirectory = Join-Path $backendRoot "backups"

function Read-EnvFile([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { throw "No se encontró el archivo .env de desarrollo." }
    $result = @{}
    foreach ($line in Get-Content -LiteralPath $Path) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$' -and $line -notmatch '^\s*#') {
            $value = $Matches[2].Trim()
            if ($value.Length -ge 2 -and (($value[0] -eq '"' -and $value[-1] -eq '"') -or ($value[0] -eq "'" -and $value[-1] -eq "'"))) {
                $value = $value.Substring(1, $value.Length - 2)
            }
            $result[$Matches[1]] = $value
        }
    }
    return $result
}

function Find-MySqlClient([string]$Name) {
    $available = Get-Command "$Name.exe" -ErrorAction SilentlyContinue
    if ($available) { return $available.Source }
    $root = Join-Path $env:ProgramFiles "MySQL"
    if (Test-Path -LiteralPath $root) {
        $found = Get-ChildItem -LiteralPath $root -Filter "$Name.exe" -File -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) { return $found.FullName }
    }
    throw "$Name.exe no está instalado o no se encuentra en PATH ni en Program Files\MySQL."
}

function Quote-OptionValue([string]$Value) {
    return '"' + $Value.Replace('\', '\\').Replace('"', '\"') + '"'
}

$envValues = Read-EnvFile $EnvFile
if ($envValues["APP_ENV"].ToLowerInvariant() -ne "development") { throw "Respaldo bloqueado: APP_ENV debe ser development." }
$databaseUrl = [Uri]$envValues["DATABASE_URL"]
$configuredDatabase = [Uri]::UnescapeDataString($databaseUrl.AbsolutePath.TrimStart('/'))
if (-not $DatabaseName) { $DatabaseName = $configuredDatabase }
if ($databaseUrl.Host -notin @("localhost", "127.0.0.1") -or ($databaseUrl.Port -ne 3306) -or $configuredDatabase -ne "transporte_frutas" -or $DatabaseName -notin @("transporte_frutas", "transporte_frutas_tmp_migraciones")) {
    throw "Respaldo bloqueado: .env debe apuntar a localhost:3306/transporte_frutas y el destino debe ser transporte_frutas o transporte_frutas_tmp_migraciones."
}
$userInfo = $databaseUrl.UserInfo.Split(':', 2)
if ($userInfo.Count -ne 2) { throw "DATABASE_URL no contiene credenciales MySQL válidas." }
$mysqlUser = [Uri]::UnescapeDataString($userInfo[0])
$mysqlPassword = [Uri]::UnescapeDataString($userInfo[1])
$clientFile = Find-MySqlClient "mysqldump"
New-Item -ItemType Directory -Path $backupDirectory -Force | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss_fff"
$backupPath = Join-Path $backupDirectory "$($DatabaseName)_$timestamp.sql"
$defaultsPath = Join-Path $env:TEMP "mysql_backup_$([guid]::NewGuid().ToString('N')).cnf"
$defaults = "[client]`nhost=$($databaseUrl.Host)`nport=$($databaseUrl.Port)`nuser=$(Quote-OptionValue $mysqlUser)`npassword=$(Quote-OptionValue $mysqlPassword)`ndefault-character-set=utf8mb4`n"
[System.IO.File]::WriteAllText($defaultsPath, $defaults, [System.Text.UTF8Encoding]::new($false))
try {
    & $clientFile "--defaults-extra-file=$defaultsPath" "--single-transaction" "--routines" "--triggers" "--events" "--skip-add-drop-table" "--set-gtid-purged=OFF" "--default-character-set=utf8mb4" "--databases" $databaseName "--result-file=$backupPath"
    if ($LASTEXITCODE -ne 0) { throw "mysqldump terminó con código $LASTEXITCODE." }
    if (-not (Test-Path -LiteralPath $backupPath) -or (Get-Item -LiteralPath $backupPath).Length -eq 0) { throw "El archivo de respaldo está vacío." }
    Write-Output "Respaldo creado: $backupPath"
}
finally {
    Remove-Item -LiteralPath $defaultsPath -Force -ErrorAction SilentlyContinue
    $mysqlPassword = $null
}
