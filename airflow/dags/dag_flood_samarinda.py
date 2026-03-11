"""
dag_flood_samarinda.py
============================================================
Airflow DAG: Pipeline Prediksi Banjir Samarinda
============================================================
Menggantikan GitHub Actions workflow 'update_data.yml'.
Menjalankan pipeline data harian, export JSON statis,
push ke GitHub, dan trigger Vercel Deploy Hook.

Schedule: Setiap hari pukul 06:00 WITA (22:00 UTC sebelumnya)

Setup Airflow Variables (via Web UI):
  - flood_github_repo       : git@github.com:amsopian22/samarinda-banjir.git
  - flood_conda_env         : flood_pipeline
  - flood_vercel_deploy_hook: https://api.vercel.com/v1/integrations/deploy/prj_xxx/yyy
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.models import Variable

# ── Konfigurasi ──────────────────────────────────────────────
REPO_URL    = Variable.get("flood_github_repo", default_var="git@github.com:amsopian22/samarinda-banjir.git")
CONDA_ENV   = Variable.get("flood_conda_env", default_var="flood_pipeline")
DEPLOY_HOOK = Variable.get("flood_vercel_deploy_hook", default_var="")
WORK_DIR    = "/tmp/samarinda-banjir"

default_args = {
    "owner":            "bidang4",
    "depends_on_past":  False,
    "email_on_failure": False,
    "email_on_retry":   False,
    "retries":          2,
    "retry_delay":      timedelta(minutes=5),
}

# ── Helper: Aktivasi Conda ───────────────────────────────────
# Sesuaikan path conda init dengan lokasi di server Anda.
# Untuk miniconda: /opt/miniconda3 atau ~/miniconda3
CONDA_ACTIVATE = f"""
    eval "$(conda shell.bash hook)" && \
    conda activate {CONDA_ENV}
"""

# ── DAG Definition ───────────────────────────────────────────
with DAG(
    dag_id="flood_samarinda_daily",
    default_args=default_args,
    description="Pipeline harian prediksi banjir Samarinda + deploy ke Vercel",
    # Pukul 06:00 WITA = 22:00 UTC hari sebelumnya
    schedule_interval="0 22 * * *",
    start_date=datetime(2026, 3, 11),
    catchup=False,
    tags=["flood", "samarinda", "geospatial", "daily"],
    max_active_runs=1,
) as dag:

    # ── Task 1: Clone Repository ─────────────────────────────
    clone_repo = BashOperator(
        task_id="clone_repo",
        bash_command=f"""
            set -e
            echo "🔄 Membersihkan folder kerja lama..."
            rm -rf {WORK_DIR}

            echo "📥 Clone repository..."
            git clone --depth 1 {REPO_URL} {WORK_DIR}

            echo "📁 Menyiapkan struktur folder runtime..."
            cd {WORK_DIR}
            mkdir -p data/raw data/processed data/boundary data/dem
            mkdir -p model output cache dashboard/public/data

            echo "✅ Repository siap di {WORK_DIR}"
        """,
    )

    # ── Task 2: Jalankan Pipeline Utama (main.py) ────────────
    run_pipeline = BashOperator(
        task_id="run_pipeline",
        bash_command=f"""
            set -e
            {CONDA_ACTIVATE}
            cd {WORK_DIR}
            export PYTHONPATH={WORK_DIR}

            echo "🌊 Menjalankan pipeline XGBoost Flood Prediction..."
            python main.py

            echo "✅ Pipeline selesai!"
        """,
        execution_timeout=timedelta(minutes=25),
    )

    # ── Task 3: Export JSON Statis ────────────────────────────
    export_json = BashOperator(
        task_id="export_json",
        bash_command=f"""
            set -e
            {CONDA_ACTIVATE}
            cd {WORK_DIR}
            export PYTHONPATH={WORK_DIR}

            echo "📦 Mengekspor data ke JSON statis..."
            python scripts/export_static.py

            echo "✅ Export selesai! File:"
            ls -lh dashboard/public/data/
        """,
        execution_timeout=timedelta(minutes=10),
    )

    # ── Task 4: Git Push Data Baru ────────────────────────────
    git_push = BashOperator(
        task_id="git_push",
        bash_command=f"""
            set -e
            cd {WORK_DIR}

            git config user.name  "airflow-bot"
            git config user.email "airflow@103.152.244.71"

            git add dashboard/public/data/

            if git diff --staged --quiet; then
                echo "ℹ️ Tidak ada perubahan data, skip commit."
            else
                TIMESTAMP=$(date +'%Y-%m-%d %H:%M WITA')
                git commit -m "Auto-update data banjir ${{TIMESTAMP}} [airflow]"
                git push origin main
                echo "✅ Data berhasil dipush ke GitHub!"
            fi
        """,
    )

    # ── Task 5: Trigger Vercel Deploy ─────────────────────────
    trigger_vercel = BashOperator(
        task_id="trigger_vercel_deploy",
        bash_command=f"""
            set -e
            HOOK_URL="{DEPLOY_HOOK}"

            if [ -z "$HOOK_URL" ]; then
                echo "⚠️ Vercel Deploy Hook belum dikonfigurasi."
                echo "   Set Airflow Variable: flood_vercel_deploy_hook"
                echo "   Skipping deploy trigger..."
                exit 0
            fi

            echo "🚀 Triggering Vercel deploy..."
            HTTP_CODE=$(curl -s -o /dev/null -w "%{{http_code}}" -X POST "$HOOK_URL")

            if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 201 ]; then
                echo "✅ Vercel deploy berhasil di-trigger! (HTTP $HTTP_CODE)"
            else
                echo "❌ Vercel deploy gagal! HTTP status: $HTTP_CODE"
                exit 1
            fi
        """,
    )

    # ── Task 6: Cleanup ──────────────────────────────────────
    cleanup = BashOperator(
        task_id="cleanup",
        bash_command=f"""
            echo "🧹 Membersihkan folder kerja..."
            rm -rf {WORK_DIR}
            echo "✅ Cleanup selesai!"
        """,
        trigger_rule="all_done",  # Jalankan meskipun task sebelumnya gagal
    )

    # ── Task Dependencies ────────────────────────────────────
    clone_repo >> run_pipeline >> export_json >> git_push >> trigger_vercel >> cleanup
