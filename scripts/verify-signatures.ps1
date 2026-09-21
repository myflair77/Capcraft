param(
    [Parameter(Mandatory)][string]$AppPath,
    [Parameter(Mandatory)][string]$InstallerPath,
    [Parameter(Mandatory)][ValidatePattern('^[a-fA-F0-9]{40}$')][string]$ExpectedThumbprint
)

# Read-only release gate. Never changes trust stores or security settings.
$ErrorActionPreference = 'Stop'
$failures = @()
foreach ($artifact in @($AppPath, $InstallerPath)) {
    $resolved = (Resolve-Path -LiteralPath $artifact).Path
    $signature = Get-AuthenticodeSignature -LiteralPath $resolved
    if ($signature.Status -ne 'Valid') {
        $failures += "$resolved : $($signature.Status)"
        continue
    }
    if ($signature.SignerCertificate.Thumbprint -ne $ExpectedThumbprint) {
        $failures += "$resolved : unexpected signing certificate"
        continue
    }
    if (-not $signature.TimeStamperCertificate) {
        $failures += "$resolved : trusted timestamp missing"
        continue
    }
    [PSCustomObject]@{
        Path = $resolved
        Status = $signature.Status
        Publisher = $signature.SignerCertificate.Subject
        Thumbprint = $signature.SignerCertificate.Thumbprint
        SHA256 = (Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash
    }
}
if ($failures.Count) {
    throw "Signing verification failed; do not publish as signed:`n$($failures -join "`n")"
}
