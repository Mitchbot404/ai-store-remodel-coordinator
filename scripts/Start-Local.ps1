param(
    [string]$PythonExe = '.venv\Scripts\python.exe',
    [switch]$LoadApiKey
)
# Run interactively in your own local Windows PowerShell terminal.
# A hidden prompt keeps the key out of source files and command history.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
$keyPointer = [IntPtr]::Zero
$secureKey = $null
try {
    if (-not (Test-Path -LiteralPath $PythonExe)) {
        throw 'Python environment not found. Follow README setup or supply -PythonExe.'
    }
    # This preparation launcher cannot enable live requests before reference review.
    $env:CANDIDATE_PROVIDER = 'mock_bounded'
    Remove-Item Env:OPENAI_LIVE_ENABLED -ErrorAction SilentlyContinue
    Remove-Item Env:PHASE6A_REFERENCE_APPROVED -ErrorAction SilentlyContinue
    if ($LoadApiKey) {
        $secureKey = Read-Host 'Enter your restricted OpenAI API key (hidden; local only)' -AsSecureString
        $keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
        $env:OPENAI_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer)
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer)
        $keyPointer = [IntPtr]::Zero
        Write-Host 'Key loaded for this local process only. Live requests remain disabled.'
    }
    & $PythonExe -m streamlit run app.py
} finally {
    if ($keyPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer) }
    if ($null -ne $secureKey) { $secureKey.Dispose() }
    if ($LoadApiKey) { Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue }
    Pop-Location
}
