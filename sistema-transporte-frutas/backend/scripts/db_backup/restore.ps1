[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$BackupFile,
    [Parameter(Mandatory = $true)][string]$Confirmation,
    [string]$EnvFile = (Join-Path (Split-Path $PSScriptRoot -Parent | Split-Path -Parent) ".env")
)

$ErrorActionPreference = "Stop"
$backendRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$backupRoot = Join-Path $backendRoot "backups"

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
if ($envValues["APP_ENV"].ToLowerInvariant() -ne "development") { throw "Restauración bloqueada: APP_ENV debe ser development." }
if ($Confirmation -cne "RESTAURAR transporte_frutas") { throw "Confirmación escrita incorrecta. Usa -Confirmation 'RESTAURAR transporte_frutas'." }
$databaseUrl = [Uri]$envValues["DATABASE_URL"]
$databaseName = [Uri]::UnescapeDataString($databaseUrl.AbsolutePath.TrimStart('/'))
if ($databaseUrl.Host -notin @("localhost", "127.0.0.1") -or $databaseUrl.Port -ne 3306 -or $databaseName -ne "transporte_frutas") {
    throw "Restauración bloqueada: el destino debe ser localhost:3306/transporte_frutas."
}
$resolvedBackup = (Resolve-Path -LiteralPath $BackupFile).Path
$resolvedRoot = (Resolve-Path -LiteralPath $backupRoot).Path.TrimEnd('\') + '\'
if (-not $resolvedBackup.StartsWith($resolvedRoot, [System.StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetExtension($resolvedBackup) -ne ".sql") {
    throw "Restauración bloqueada: el respaldo debe ser un .sql ubicado dentro de backend/backups/."
}
$userInfo = $databaseUrl.UserInfo.Split(':', 2)
if ($userInfo.Count -ne 2) { throw "DATABASE_URL no contiene credenciales MySQL válidas." }
$mysqlUser = [Uri]::UnescapeDataString($userInfo[0])
$mysqlPassword = [Uri]::UnescapeDataString($userInfo[1])
$clientFile = Find-MySqlClient "mysql"
$defaultsPath = Join-Path $env:TEMP "mysql_restore_$([guid]::NewGuid().ToString('N')).cnf"
$defaults = "[client]`nhost=$($databaseUrl.Host)`nport=$($databaseUrl.Port)`nuser=$(Quote-OptionValue $mysqlUser)`npassword=$(Quote-OptionValue $mysqlPassword)`ndefault-character-set=utf8mb4`n"
[System.IO.File]::WriteAllText($defaultsPath, $defaults, [System.Text.UTF8Encoding]::new($false))
try {
    $existingTables = & $clientFile "--defaults-extra-file=$defaultsPath" "--batch" "--skip-column-names" "--execute=SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$databaseName'" "--database=information_schema"
    if ($LASTEXITCODE -ne 0) { throw "No se pudo verificar el destino antes de restaurar." }
    if ([int]$existingTables -ne 0) { throw "Restauración bloqueada: la base destino ya tiene tablas. El script no elimina ni sobrescribe datos." }
    $mysqlPath = $resolvedBackup.Replace('\', '/')
    & $clientFile "--defaults-extra-file=$defaultsPath" "--default-character-set=utf8mb4" "--database=$databaseName" "--execute=source '$mysqlPath'"
    if ($LASTEXITCODE -ne 0) { throw "mysql terminó con código $LASTEXITCODE." }
    Write-Output "Respaldo restaurado en $databaseName."
}
finally {
    Remove-Item -LiteralPath $defaultsPath -Force -ErrorAction SilentlyContinue
    $mysqlPassword = $null
}
