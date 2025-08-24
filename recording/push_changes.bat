@echo off
echo Pushing changes to GitHub...

REM Move the git config file temporarily
move .git\config .git\config.backup 2>nul

REM Create a minimal working config
echo [core] > .git\config
echo 	repositoryformatversion = 0 >> .git\config
echo 	filemode = false >> .git\config
echo 	bare = false >> .git\config
echo 	logallrefupdates = true >> .git\config
echo 	symlinks = false >> .git\config
echo 	ignorecase = true >> .git\config
echo [remote "origin"] >> .git\config
echo 	url = https://github.com/yourusername/yourrepo.git >> .git\config
echo 	fetch = +refs/heads/*:refs/remotes/origin/* >> .git\config
echo [branch "main"] >> .git\config
echo 	remote = origin >> .git\config
echo 	merge = refs/heads/main >> .git\config

REM Add files
git add daily_call_processor_dev_optimized.py .github/workflows/ultra-high-volume.yml 2>nul

REM Commit
git commit -m "Add dev tier optimized processor with concurrent processing" 2>nul

REM Push
git push origin main 2>nul

REM Restore original config if needed
if exist .git\config.backup (
    del .git\config
    move .git\config.backup .git\config
)

echo Done!
