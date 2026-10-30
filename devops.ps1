param([ValidateSet('dev','prod','deploy','stop-dev','stop-prod','logs-dev','logs-prod','test','check','migrate','superuser','superuser-dev','ps','backup')][string]$Task = 'dev')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$dev = @('compose','-f','compose.dev.yaml')
$prod = @('compose','--env-file','.env.production','-f','compose.yaml')
function Invoke-Docker([string[]]$Arguments) {
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Docker a echoue (code $LASTEXITCODE)." }
}
switch ($Task) {
    dev { Invoke-Docker ($dev + @('up','-d','--build','--wait')) }
    prod {
        Invoke-Docker ($prod + @('build'))
        Invoke-Docker ($prod + @('up','-d','--wait','db','redis'))
        Invoke-Docker ($prod + @('run','--rm','migrate'))
        Invoke-Docker ($prod + @('up','-d','--wait'))
    }
    deploy {
        Invoke-Docker ($prod + @('pull'))
        Invoke-Docker ($prod + @('up','-d','--wait','db','redis'))
        Invoke-Docker ($prod + @('run','--rm','migrate'))
        Invoke-Docker ($prod + @('up','-d','--no-build','--wait'))
    }
    stop-dev { Invoke-Docker ($dev + @('down')) }
    stop-prod { Invoke-Docker ($prod + @('down')) }
    logs-dev { Invoke-Docker ($dev + @('logs','-f','--tail=100')) }
    logs-prod { Invoke-Docker ($prod + @('logs','-f','--tail=100')) }
    test { Invoke-Docker ($dev + @('exec','-T','web','python','manage.py','test','hub','config','--verbosity','1')) }
    check { Invoke-Docker ($prod + @('run','--rm','web','python','manage.py','check','--deploy','--fail-level','WARNING')) }
    migrate { Invoke-Docker ($prod + @('run','--rm','migrate')) }
    superuser { Invoke-Docker ($prod + @('exec','web','python','manage.py','createsuperuser')) }
    superuser-dev { Invoke-Docker ($dev + @('exec','web','python','manage.py','createsuperuser')) }
    ps { Invoke-Docker ($prod + @('ps')) }
    backup {
        Invoke-Docker ($prod + @('exec','-T','db','pg_dump','-U','hub','-d','hub','-Fc','-f','/tmp/hub.dump'))
        Invoke-Docker ($prod + @('cp','db:/tmp/hub.dump','./hub-backup.dump'))
        Invoke-Docker ($prod + @('exec','-T','web','tar','-czf','/tmp/media.tar.gz','-C','/app','media'))
        Invoke-Docker ($prod + @('cp','web:/tmp/media.tar.gz','./hub-media-backup.tar.gz'))
    }
}
