param([switch]$CreateAdmin, [int]$Port = 8000)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$hubLaunchArguments = @('start.py', '--port', "$Port")
if ($CreateAdmin) { $hubLaunchArguments += '--admin' }
if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 @hubLaunchArguments }
elseif (Get-Command python -ErrorAction SilentlyContinue) { & python @hubLaunchArguments }
else { throw 'Installez Python 3.12 ou 3.13 puis relancez ce script.' }
exit $LASTEXITCODE
