import os, zipfile

base_dir = '/mnt/E8A2D79FA2D77114/Source/repos/GameRandomizers/Randomizers/ShadowsOverLoathing/shadows_over_loathing'
os.makedirs(base_dir, exist_ok=True)

CHAPTERS = [
    'Prologue - Gilmore Antiques',
    'Chapter 1 - Ocean City',
    'Chapter 2 - Crystaldream Lake',
    'Chapter 3 - The Big Moist',
    'Chapter 4 - Gray County',
    'Chapter 5 - Black Gold',
    'Chapter 6 - Government Valley',
]

def build():
    out = '/mnt/E8A2D79FA2D77114/Games/Archipelago/custom_worlds/shadows_over_loathing.apworld'
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fn in sorted(os.listdir(base_dir)):
            if fn.endswith('.py'):
                zf.write(os.path.join(base_dir, fn), arcname=f'shadows_over_loathing/{fn}')
    print('[SUCCESS] Rebuilt', out)

if __name__ == '__main__':
    build()
