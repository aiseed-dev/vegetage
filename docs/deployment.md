# Vegetage サーバー設定マニュアル (GCE / Ubuntu) — 旧手順

**現在は Cloudflare Pages への移行作業中。新規デプロイは
[`web-publish.md`](web-publish.md) を参照。** このドキュメントは
aiseed.page のドメイン切替が完了し GCE を停止するまでの参考として残す。

このドキュメントは、VegetageアプリケーションをGoogle Compute Engine (GCE) 上のUbuntuサーバーにデプロイするための手順をまとめたものです。

## 1. 前提条件

*   Google Cloud Platform (GCP) アカウントが設定済みであること。
*   `gcloud` コマンドラインツールがローカルマシンにインストール・認証済みであること。
*   プロジェクトのソースコードがGitHubリポジトリにプッシュされていること。

## 2. GCEインスタンスの作成と設定

1.  **GCEインスタンスの作成:**
    *   **リージョン:** `asia-northeast1` (東京) を推奨
    *   **マシンタイプ:** `e2-micro` または `e2-small`
    *   **ブートディスク:** Ubuntu 22.04 LTS
    *   **ファイアウォール:**
        *   `HTTP トラフィックを許可する` にチェック
        *   `HTTPS トラフィックを許可する` にチェック

2.  **静的IPアドレスの予約:**
    インスタンス作成後、GCPコンソールの「VPCネットワーク」>「IPアドレス」から、インスタンスに割り当てられた外部IPアドレスを「静的」に予約します。

## 3. サーバー環境の基本設定

GCEインスタンスにSSHで接続し、以下のコマンドを実行します。

```bash
# パッケージリストの更新とアップグレード
sudo apt update && sudo apt upgrade -y

# 必要なツールのインストール (Git, Nginx, Python)
sudo apt install git nginx python3-pip python3-venv -y
```

## 4. プロジェクトのデプロイ

1.  **ソースコードのクローン:**
    ```bash
    # /var/www ディレクトリにプロジェクトを配置するのが一般的
    cd /var/www
    sudo git clone https://github.com/your-username/vegetage.git
    cd vegetage
    ```

2.  **データディレクトリの配置:**
    AIが生成したJSONデータファイルをサーバーに配置します。
    ```bash
    # データ格納用の親ディレクトリを作成
    sudo mkdir -p /var/data/vegetage/
    
    # ローカルからGCS経由、または直接scpでデータディレクトリをコピー
    # 例: sudo scp -r local/path/to/data_ja /var/data/vegetage/
    ```
    最終的に以下の構造になるようにデータを配置します。
    *   `/var/data/vegetage/ja/species/`
    *   `/var/data/vegetage/ja/varieties/`
    *   `/var/data/vegetage/ja/species_index.json`
    *   `/var/data/vegetage/ja/varieties_index.json`
    
    _注意: FastAPIのコード内で、このデータディレクトリパス (`/var/data/vegetage/ja`) を正しく参照するようにしてください。_

## 5. バックエンド (FastAPI) の設定

1.  **Python仮想環境のセットアップ:**
    ```bash
    # プロジェクトのルートディレクトリに移動
    cd /var/www/vegetage/backend # FastAPIのコードがあるディレクトリ

    # 仮想環境を作成
    sudo python3 -m venv venv

    # 仮想環境を有効化
    source venv/bin/activate

    # 必要なライブラリをインストール
    pip install -r requirements.txt
    ```

2.  **UvicornをSystemdサービスとして登録 (推奨):**
    サーバーが再起動してもFastAPIが自動で起動するように、`systemd` サービスとして登録します。

    `sudo nano /etc/systemd/system/vegetage-api.service` を作成し、以下の内容を記述します。

    ```ini
    [Unit]
    Description=Vegetage API Service
    After=network.target

    [Service]
    User=www-data # Nginxと同じユーザーで実行するのが一般的
    Group=www-data
    WorkingDirectory=/var/www/vegetage/backend
    ExecStart=/var/www/vegetage/backend/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
    Restart=always

    [Install]
    WantedBy=multi-user.target
    ```

3.  **サービスの有効化と起動:**
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable vegetage-api
    sudo systemctl start vegetage-api

    # 動作確認
    sudo systemctl status vegetage-api 
    ```

## 6. フロントエンド (Flutter Web) のビルドと配置

1.  **ローカルマシンでFlutter Webをビルド:**
    ```bash
    # あなたのローカルのFlutterプロジェクトディレクトリで実行
    flutter build web --release
    ```

2.  **ビルド済みファイルをサーバーにアップロード:**
    `build/web` ディレクトリの中身を、サーバーの `/var/www/vegetage/frontend` ディレクトリにアップロードします。（ディレクトリは任意）

## 7. Webサーバー (Nginx) の設定

Nginxをリバースプロキシとして設定し、フロントエンドとバックエンドを振り分けます。

`sudo nano /etc/nginx/sites-available/default` を編集し、内容を以下のように書き換えます。

```nginx
server {
    listen 80;
    # server_name your.domain.com; # ドメインがある場合
    server_name YOUR_STATIC_IP_ADDRESS; # IPアドレスを直接指定

    # APIリクエストのプロキシ設定
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Flutter Webアプリの配信設定
    location / {
        root /var/www/vegetage/frontend; # Flutter Webのファイルを置いた場所
        try_files $uri $uri/ /index.html;
    }
}
```

**設定のテストと再起動:**
```bash
sudo nginx -t # 設定ファイルに文法エラーがないかテスト
sudo nginx -s restore
```

## 8. デプロイ完了

以上で設定は完了です。
ブラウザで `http://YOUR_STATIC_IP_ADDRESS` にアクセスし、Flutter Webアプリが表示され、アプリ内からAPIへの通信が正常に行えることを確認してください。

---

このマニュアルをリポジトリに含めておくことで、あなた自身が後で手順を再確認する際にも役立ちますし、他の人がこの素晴らしいプロジェクトを再現しようとする際の、最高のガイドになります。