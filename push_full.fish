#!/usr/bin/env fish

function usage
    echo "Uso: ./push_full.fish [opzioni]"
    echo
    echo "Opzioni:"
    echo "  -m, --message <msg>     Messaggio commit (default auto timestamp)"
    echo "  -b, --branch <nome>     Branch di push (default: branch corrente)"
    echo "  -n, --no-verify         Commit senza hook git"
    echo "  -d, --deploy-vps        Dopo il push esegue anche deploy remoto"
    echo "  -H, --vps-host <host>   Host SSH (es: ubuntu@vps-b054ede5)"
    echo "  -P, --vps-path <path>   Path progetto su VPS (es: ~/archibald)"
    echo "  -h, --help              Mostra questo aiuto"
end

argparse 'm/message=' 'b/branch=' 'n/no-verify' 'd/deploy-vps' 'H/vps-host=' 'P/vps-path=' 'h/help' -- $argv
or begin
    usage
    exit 1
end

if set -q _flag_help
    usage
    exit 0
end

set script_file (status --current-filename)
set project_dir (cd (dirname $script_file); and pwd)
cd $project_dir

if not git rev-parse --is-inside-work-tree >/dev/null 2>&1
    echo "Errore: $project_dir non e una repository git."
    exit 1
end

if not type -q git
    echo "Errore: git non disponibile."
    exit 1
end

set branch (git branch --show-current)
if set -q _flag_branch
    set branch $_flag_branch
end

if set -q _flag_message
    set commit_message $_flag_message
else
    set commit_message (string join "" "chore: sync " (date "+%Y-%m-%d %H:%M"))
end

if git ls-files --error-unmatch .env >/dev/null 2>&1
    echo "Errore: .env risulta tracciato in git."
    echo "Esegui prima: git rm --cached .env"
    exit 1
end

echo "==> Staging completo (escludo .env)"
git add -A
git restore --staged .env >/dev/null 2>&1

if git diff --cached --quiet
    echo "==> Nessuna modifica da committare."
else
    echo "==> Commit: $commit_message"
    if set -q _flag_no_verify
        git commit --no-verify -m "$commit_message"
    else
        git commit -m "$commit_message"
    end
end

echo "==> Push origin/$branch"
git push origin "HEAD:$branch"

if set -q _flag_deploy_vps
    if not set -q _flag_vps_host
        echo "Errore: con --deploy-vps devi passare --vps-host <utente@host>."
        exit 1
    end
    if not set -q _flag_vps_path
        echo "Errore: con --deploy-vps devi passare --vps-path </path/progetto>."
        exit 1
    end

    echo "==> Deploy remoto su $_flag_vps_host:$_flag_vps_path"
    ssh $_flag_vps_host "cd '$_flag_vps_path' && ./deploy_vps.sh --branch '$branch' --force-sync"
end

echo "==> Operazione completata."
