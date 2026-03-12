"""
dag_flood_samarinda.py
============================================================
Airflow DAG: Pipeline Prediksi Banjir Samarinda (DOCKER VERSION)
============================================================
Menggunakan SSHOperator agar Airflow (di dalam Docker) bisa 
menjalankan perintah di server Host (di mana Conda & GIS terpasang).

Setup di Airflow Web UI:
1. Admin > Connections > Add New:
   - Conn Id: ssh_host_server
   - Conn Type: SSH
   - Host: 103.152.244.71 (atau host.docker.internal)
   - Username: datains
   - Port: 22
   - Password / Private Key: (Sesuai akses server Anda)
2. Admin > Variables:
   - flood_project_dir: /home/datains/data-platform/samarinda-banjir
   - flood_conda_env: flood_pipeline
   - flood_vercel_deploy_hook: (URL dari Vercel)
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.models import Variable

# ── Konfigurasi ──────────────────────────────────────────────
SSH_CONN_ID = "ssh_host_server"
PROJECT_DIR = Variable.get("flood_project_dir", default_var="/home/datains/data-platform/samarinda-banjir")
CONDA_ENV   = Variable.get("flood_conda_env", default_var="flood_pipeline")
DEPLOY_HOOK = Variable.get("flood_vercel_deploy_hook", default_var="")

default_args = {
    "owner":            "bidang4",
    "depends_on_past":  False,
    "email_on_failure": False,
    "email_on_retry":   False,
    "retries":          2,
    "retry_delay":      timedelta(minutes=5),
}

# ── Helper: Aktivasi Conda (di Server Host) ──────────────────
# Sesuaikan path conda init jika berbeda di server host
CONDA_ACTIVATE = f"""
    eval "$(conda shell.bash hook)" && \
    conda activate {CONDA_ENV}
"""

with DAG(
    dag_id="flood_samarinda_daily",
    default_args=default_args,
    description="Pipeline harian via SSH ke Host Server",
    schedule_interval="0 22 * * *",
    start_date=datetime(2026, 3, 11),
    catchup=False,
    tags=["ssh", "docker", "samarinda", "daily"],
    max_active_runs=1,
) as dag:

    # ── Task 1: Git Pull ─────────────────────────────────────
    git_pull = SSHOperator(
        task_id="git_pull",
        ssh_conn_id=SSH_CONN_ID,
        command=f"""
            set -e
            cd {PROJECT_DIR}
            echo "🔄 Mengambil kode terbaru..."
            git fetch origin main
            git reset --hard origin/main
            mkdir -p data/raw data/processed data/boundary data/dem model output cache dashboard/public/data
            echo "✅ Repo updated: $(git log -1 --oneline)"
        """,
    )

    # ── Task 2: Jalankan Pipeline (main.py) ──────────────────
    run_pipeline = SSHOperator(
        task_id="run_pipeline",
        ssh_conn_id=SSH_CONN_ID,
        command=f"""
            set -e
            {CONDA_ACTIVATE}
            cd {PROJECT_DIR}
            export PYTHONPATH={PROJECT_DIR}
            echo "🌊 Running pipeline..."
            python main.py
        """,
        timeout=timedelta(minutes=25),
    )

    # ── Task 3: Export JSON Statis ────────────────────────────
    export_json = SSHOperator(
        task_id="export_json",
        ssh_conn_id=SSH_CONN_ID,
        command=f"""
            set -e
            {CONDA_ACTIVATE}
            cd {PROJECT_DIR}
            export PYTHONPATH={PROJECT_DIR}
            echo "📦 Exporting JSON..."
            python scripts/export_static.py
        """,
        timeout=timedelta(minutes=10),
    )

    # ── Task 4: Git Push ─────────────────────────────────────
    git_push = SSHOperator(
        task_id="git_push",
        ssh_conn_id=SSH_CONN_ID,
        command=f"""
            set -e
            cd {PROJECT_DIR}
            git config user.name "airflow-bot"
            git config user.email "airflow@server"
            
            echo "📝 Staging changes in dashboard/public/data/..."
            git add dashboard/public/data/*.json
            
            if git diff --staged --quiet; then
                echo "ℹ️ No changes to commit."
            else
                echo "🚀 Committing changes..."
                COMMIT_MSG="Auto-update data $(date +'%Y-%m-%d %H:%M') [airflow-ssh]"
                git commit -m "$COMMIT_MSG"
                
                echo "🔄 Fetching and pulling with rebase to avoid conflicts..."
                git fetch origin main
                git rebase origin/main
                
                echo "📤 Pushing to GitHub..."
                git push origin main
                echo "✅ Pushed to GitHub: $COMMIT_MSG"
            fi
        """,
    )

    # ── Task 5: Trigger Vercel Deploy ─────────────────────────
    # Task ini tetap BashOperator karena bisa dijalankan dari container (hanya curl)
    from airflow.operators.bash import BashOperator
    trigger_vercel = BashOperator(
        task_id="trigger_vercel_deploy",
        bash_command=f"""
            set -e
            HOOK_URL="{DEPLOY_HOOK}"
            if [ -z "$HOOK_URL" ]; then
                echo "⚠️ Hook URL missing."
                exit 0
            fi
            echo "🚀 Triggering Vercel..."
            curl -X POST "$HOOK_URL"
        """,
    )

    git_pull >> run_pipeline >> export_json >> git_push >> trigger_vercel
