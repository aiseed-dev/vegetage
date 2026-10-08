#!/usr/bin/env bash
set -euo pipefail

# ============================================
# Vegetage — scp デプロイスクリプト
# ============================================
#
# 使い方:
#   ./web/deploy.sh                     # ビルド + デプロイ
#   ./web/deploy.sh --build-only        # ビルドのみ
#   ./web/deploy.sh --deploy-only       # デプロイのみ (既存の site/ を送信)
#
# 環境変数 (.env または export):
#   DEPLOY_HOST     サーバーのホスト名/IP       (例: aiseed.dev)
#   DEPLOY_USER     SSH ユーザー名              (例: deploy)
#   DEPLOY_PATH     リモートのドキュメントルート (例: /var/www/aiseed.dev/vegitage)
#   DEPLOY_PORT     SSH ポート                  (デフォルト: 22)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SITE_DIR="$SCRIPT_DIR/site"

# .env があれば読み込む
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "$PROJECT_ROOT/.env"
    set +a
fi

# デフォルト値
DEPLOY_HOST="${DEPLOY_HOST:-}"
DEPLOY_USER="${DEPLOY_USER:-}"
DEPLOY_PATH="${DEPLOY_PATH:-}"
DEPLOY_PORT="${DEPLOY_PORT:-22}"

# ── ビルド ──────────────────────────────────
do_build() {
    echo "==> ビルド開始"
    python3 "$SCRIPT_DIR/build.py"
    echo ""
}

# ── デプロイ ────────────────────────────────
do_deploy() {
    if [[ -z "$DEPLOY_HOST" || -z "$DEPLOY_USER" || -z "$DEPLOY_PATH" ]]; then
        echo "エラー: デプロイ先が未設定です。"
        echo ""
        echo "以下の環境変数を .env または export で設定してください:"
        echo "  DEPLOY_HOST=aiseed.dev"
        echo "  DEPLOY_USER=youruser"
        echo "  DEPLOY_PATH=/var/www/aiseed.dev/vegitage"
        echo ""
        echo "例:"
        echo "  DEPLOY_HOST=aiseed.dev DEPLOY_USER=deploy DEPLOY_PATH=/var/www/html/vegitage ./web/deploy.sh"
        exit 1
    fi

    if [[ ! -d "$SITE_DIR" ]]; then
        echo "エラー: $SITE_DIR が存在しません。先にビルドしてください。"
        exit 1
    fi

    REMOTE="$DEPLOY_USER@$DEPLOY_HOST"
    echo "==> デプロイ: $REMOTE:$DEPLOY_PATH"

    # リモートディレクトリ作成
    ssh -p "$DEPLOY_PORT" "$REMOTE" "mkdir -p '$DEPLOY_PATH'"

    # rsync が使えれば rsync、なければ scp
    if command -v rsync &>/dev/null; then
        rsync -avz --delete \
            -e "ssh -p $DEPLOY_PORT" \
            "$SITE_DIR/" \
            "$REMOTE:$DEPLOY_PATH/"
    else
        scp -P "$DEPLOY_PORT" -r "$SITE_DIR/"* "$REMOTE:$DEPLOY_PATH/"
    fi

    echo ""
    echo "==> デプロイ完了!"
    echo "    https://$DEPLOY_HOST$(echo "$DEPLOY_PATH" | sed "s|.*/var/www/[^/]*||; s|.*/html||")"
}

# ── メイン ──────────────────────────────────
case "${1:-}" in
    --build-only)
        do_build
        ;;
    --deploy-only)
        do_deploy
        ;;
    *)
        do_build
        do_deploy
        ;;
esac
