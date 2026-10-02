@echo off
cd /d "%~dp0.."
git config core.hooksPath scripts/hooks
echo Subida automatica a GitHub activada: cada commit se publicara solo.
pause
