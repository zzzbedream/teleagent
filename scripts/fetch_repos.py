import os
import subprocess
import logging
import shutil

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def run_cmd(cmd, cwd=None):
    logging.info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(f"Command failed: {result.stderr}")
        # Fallar ruidosamente: si un repo no se clona, el corpus queda cojo y es mejor
        # abortar (p.ej. el build de Docker) que publicar un cerebro a medias.
        raise SystemExit(f"fetch_repos abortado: fallo '{' '.join(cmd)}'")

def fetch_repo_sparse(repo_url, target_dir, paths):
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir, ignore_errors=True)
    os.makedirs(target_dir)
    
    run_cmd(["git", "clone", "--no-checkout", "--depth", "1", repo_url, target_dir])
    run_cmd(["git", "sparse-checkout", "init", "--cone"], cwd=target_dir)
    run_cmd(["git", "sparse-checkout", "set"] + paths, cwd=target_dir)
    run_cmd(["git", "checkout"], cwd=target_dir)
    # clean up .git folder
    shutil.rmtree(os.path.join(target_dir, ".git"), ignore_errors=True)

def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs"))
    os.makedirs(base_dir, exist_ok=True)
    
    # 1. ACPs
    logging.info("Fetching ACPs...")
    fetch_repo_sparse("https://github.com/avalanche-foundation/ACPs.git", os.path.join(base_dir, "acps"), ["ACPs/"])
    
    # 2. Avalanche Docs (repo renombrado a builders-hub). Además de content/docs, traemos
    # blog/common/academy: ahí vive el contenido de la actualización Etna/Avalanche9000
    # (etna-changes.mdx, etna-upgrade-motivation.mdx, 05-etna-upgrade.mdx, etc.).
    logging.info("Fetching Avalanche Docs...")
    fetch_repo_sparse(
        "https://github.com/ava-labs/builders-hub.git",
        os.path.join(base_dir, "docs"),
        ["content/docs", "content/blog", "content/common", "content/academy"],
    )
    
    # 3. Teleporter
    logging.info("Fetching Teleporter contracts...")
    fetch_repo_sparse("https://github.com/ava-labs/teleporter.git", os.path.join(base_dir, "teleporter"), ["contracts/"])

if __name__ == "__main__":
    main()
