"""一键：抓取 → 出 MD → 出 PDF（不上传知识库）
用法：python run_all.py [--relogin]
"""
import subprocess, sys, pathlib

HERE = pathlib.Path(__file__).resolve().parent
PY = sys.executable

for step in ["fetch_wrong.py", "build_md.py", "build_pdf.py"]:
    print(f"\n===== {step} =====")
    args = [PY, str(HERE / step)]
    if step == "fetch_wrong.py" and "--relogin" in sys.argv:
        args.append("--relogin")
    r = subprocess.run(args)
    if r.returncode != 0:
        sys.exit(f"{step} 失败，退出码 {r.returncode}")
print("\n全部完成。上传知识库请按 SKILL.md 的“上传”步骤操作。")
