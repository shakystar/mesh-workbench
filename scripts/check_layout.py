"""Check the user-requested ten-direct-files limit; .git/.venv are excluded."""
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def check():
    violations=[];maximum=0;folders=0
    for current,dirs,files in os.walk(ROOT):
        dirs[:]=[d for d in dirs if d not in ('.git','.venv') and not (Path(current)/d).is_symlink()]
        folders+=1;maximum=max(maximum,len(files))
        if len(files)>10:
            violations.append({'path':Path(current).relative_to(ROOT).as_posix(),'files':len(files)})
    result={'limit':10,'excluded':['.git','.venv'],'folders':folders,'maximum':maximum,'violations':violations}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return result


if __name__=='__main__':
    raise SystemExit(bool(check()['violations']))
