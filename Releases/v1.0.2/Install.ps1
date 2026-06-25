New-Item -Path "$env:LOCALAPPDATA\LazyOpt" -ItemType Directory -Force
$extractFolder = "$env:LOCALAPPDATA\LazyOpt\"
Write-Output "INSTALL SCRIPT FOR LazyOpt"
if ((Test-Path -Path ".\LazyOpt.exe") -and (Test-Path -Path ".\server.exe")) {
  Write-Output "Found LazyOpt executable & server executable!"
} else {
  Write-Output "Could not find LazyOpt executable & server executable, getting them!"
  $YesOrNo = Read-Host -Prompt "The script is trying to download the executables, do you wish to download them: "
  if ($YesOrNo -eq "yes") {
    Write-Output "Yes detected! Downloading files..."
    Invoke-WebRequest -Uri "https://github.com/alanbutidk/LazyOpt/releases/download/unified-v1.0.2/LazyOptWindows64v1.0.2.zip" -OutFile ".\LazyOptWindows64v1.0.2.zip"
  } else {
    Write-Output "No detected! Not downloading the files!"
    exit
  }
  Expand-Archive -Path ".\LazyOptWindows64v1.0.2.zip" -DestinationPath "$extractFolder"
  Write-Output "Almost Done! Files extracted to: $extractFolder"
  Write-Output "Cleaning up..."
  Remove-Item -Path ".\LazyOptWindows64v1.0.2.zip"
  Write-Output "Adding executable(s) to PATH!"
  try {
    $oldPath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $newPath = "$oldPath;$extractFolder"
    [System.Environment]::SetEnvironmentVariable("Path", $newPath, "Machine")
    Write-Output "Added to system PATH (Machine)."
  } catch {
    Write-Output "No admin rights, adding to user PATH instead..."
    $oldPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $newPath = "$oldPath;$extractFolder"
    [System.Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Output "Added to user PATH."
  }
  $env:PATH = "$env:PATH;$extractFolder"
  Write-Output "Done! Restart your terminal for PATH to apply in new windows."
}
