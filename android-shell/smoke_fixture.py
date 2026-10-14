from pathlib import Path
p = Path('android-shell/project/app/src/main/assets/index.html')
p.write_text('<!doctype html><h1>Android smoke test</h1>')
