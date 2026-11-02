[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Confirmation,
    [string]$EnvFile = (Join-Path (Split-Path $PSScriptRoot -Parent | Split-Path -Parent) ".env")
)

$ErrorActionPreference = "Stop"
$requiredConfirmation = "CONFIRMO RECREAR transporte_frutas"
if ($Confirmation -cne $requiredConfirmation) {
    throw "Recreación bloqueada. Escribe exactamente -Confirmation '$requiredConfirmation'."
}

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
if ($envValues["APP_ENV"].ToLowerInvariant() -ne "development") { throw "Recreación bloqueada: APP_ENV debe ser development." }
$databaseUrl = [Uri]$envValues["DATABASE_URL"]
$databaseName = [Uri]::UnescapeDataString($databaseUrl.AbsolutePath.TrimStart('/'))
if ($databaseUrl.Host -notin @("localhost", "127.0.0.1") -or $databaseUrl.Port -ne 3306 -or $databaseName -cne "transporte_frutas") {
    throw "Recreación bloqueada: solo se permite localhost:3306/transporte_frutas."
}
$userInfo = $databaseUrl.UserInfo.Split(':', 2)
if ($userInfo.Count -ne 2) { throw "DATABASE_URL no contiene credenciales MySQL válidas." }
$mysqlUser = [Uri]::UnescapeDataString($userInfo[0])
$mysqlPassword = [Uri]::UnescapeDataString($userInfo[1])
$clientFile = Find-MySqlClient "mysql"
$defaultsPath = Join-Path $env:TEMP "mysql_recreate_$([guid]::NewGuid().ToString('N')).cnf"
$defaults = "[client]`nhost=$($databaseUrl.Host)`nport=$($databaseUrl.Port)`nuser=$(Quote-OptionValue $mysqlUser)`npassword=$(Quote-OptionValue $mysqlPassword)`ndefault-character-set=utf8mb4`n"
[System.IO.File]::WriteAllText($defaultsPath, $defaults, [System.Text.UTF8Encoding]::new($false))
try {
    $sql = "DROP DATABASE IF EXISTS transporte_frutas; CREATE DATABASE transporte_frutas CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    & $clientFile "--defaults-extra-file=$defaultsPath" "--execute=$sql"
    if ($LASTEXITCODE -ne 0) { throw "mysql terminó con código $LASTEXITCODE." }
    & $clientFile "--defaults-extra-file=$defaultsPath" "--database=information_schema" "--batch" "--skip-column-names" "--execute=SELECT CONCAT(DEFAULT_CHARACTER_SET_NAME, '/', DEFAULT_COLLATION_NAME) FROM SCHEMATA WHERE SCHEMA_NAME='transporte_frutas'"
    if ($LASTEXITCODE -ne 0) { throw "No se pudo verificar el charset y collation de la base recreada." }
}
finally {
    Remove-Item -LiteralPath $defaultsPath -Force -ErrorAction SilentlyContinue
    $mysqlPassword = $null
}
