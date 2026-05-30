<#
PowerShell helper to push repo to GitHub and deploy to Hugging Face Spaces.
Usage:
  1. Open PowerShell in repo root.
  2. Set environment variables or edit the script values below.
     - $GitRemote: your GitHub remote (already provided)
     - $HF_USERNAME: your Hugging Face username
     - $HF_SPACE_NAME: desired space name
     - Optionally set HF_TOKEN env var to avoid interactive login.
  3. Run: .\scripts\push_and_deploy.ps1
#>

# --- User config (change as needed) ---------------------------------
$GitRemote = 'https://github.com/RaviSoni804426/Personal-Rag-Project.git'
$HF_USERNAME = $env:HF_USERNAME
$HF_SPACE_NAME = $env:HF_SPACE_NAME
$MakeSpacePrivate = $false

if (-not $HF_USERNAME) {
    Write-Host "Enter your Hugging Face username (required to create space):"
    $HF_USERNAME = Read-Host
}
if (-not $HF_SPACE_NAME) {
    $HF_SPACE_NAME = Read-Host "Enter desired Hugging Face Space name (e.g. datamind)"
}

# --- Push to GitHub --------------------------------------------------
Write-Host "Adding GitHub remote and pushing to GitHub..."
if (git remote get-url origin -ErrorAction SilentlyContinue) {
    git remote remove origin
}
git remote add origin $GitRemote

git add -A
if (-not (git rev-parse --verify HEAD -ErrorAction SilentlyContinue)) {
    git commit --allow-empty -m "chore: initial commit for deploy"
}
else {
    git commit -m "chore: prepare repo for deploy" -a -q || Write-Host "No changes to commit"
}

git branch -M main
git push -u origin main

# --- Prepare Hugging Face CLI ---------------------------------------
if (-not (Get-Command huggingface-cli -ErrorAction SilentlyContinue)) {
    Write-Host "huggingface-cli not found. Installing huggingface-hub package..."
    python -m pip install --user huggingface-hub
}

# Login to HF (use HF_TOKEN env var to skip interactive)
if ($env:HF_TOKEN) {
    Write-Host "Logging into Hugging Face using HF_TOKEN environment variable..."
    huggingface-cli login --token $env:HF_TOKEN
} else {
    Write-Host "If you haven't logged into Hugging Face CLI, you'll be prompted now."
    huggingface-cli login
}

# Create Space repository (if not exists) and push files
$hf_repo_url = "https://huggingface.co/spaces/$HF_USERNAME/$HF_SPACE_NAME"
Write-Host "Creating HF Space (if it doesn't exist) and pushing files to $hf_repo_url"

# Attempt to create the space via CLI (may fail if already exists)
try {
    huggingface-cli repo create $HF_USERNAME/$HF_SPACE_NAME --type space --sdk docker --private:($MakeSpacePrivate) | Out-Null
} catch {
    Write-Host "Space create command returned: $_. Proceeding (it may already exist)."
}

# Add remote and push
if (git remote get-url hf -ErrorAction SilentlyContinue) {
    git remote remove hf
}

git remote add hf $hf_repo_url

git push hf main:main -u

Write-Host "Push complete. Visit https://huggingface.co/spaces/$HF_USERNAME/$HF_SPACE_NAME to view logs and set Secrets."
