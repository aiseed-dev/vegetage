# field-timelapse — 畑の定点タイムラプス(スマホ手持ち)

畑を見回るついでにスマホで撮った写真を、**特徴点マッチングで基準の構図にぴたりと重ね**、
撮影日入りのタイムラプス動画(MP4)にする。定点カメラも三脚も要らない。

```
スマホで撮る → 写真がフォルダに同期される → 新しい写真だけ位置合わせ → 動画を作り直す
```

## しくみ

1. 写真の向き(EXIF)を直し、撮影日時(EXIF の DateTimeOriginal)を読む
2. SIFT で特徴点を取り、基準の写真との対応を RANSAC で絞って、射影変換(ホモグラフィ)を求める
   - 作物は日に日に育つので、**基準の写真**と**撮影日がいちばん近い位置合わせ済みの写真**の両方に合わせてみて、対応点が多いほうを採る
   - 推定した変換が手持ちのズレとしておかしい(縮尺が大きく違う、ねじれている)ときは、移動・回転・拡大縮小だけの変換で推定し直す
   - それでも合わない写真は動画に入れず、`report.txt` に理由を書く
3. 基準の構図に変形して保存する。端に出る黒い余白は1つ前のコマで埋め、四辺を少し切る
4. 撮影日の順に並べ、左下に撮影日、左上に被写体の名前を入れて、ffmpeg で MP4 にする

基準の写真は、その被写体でいちばん古い写真(指定もできる)。
処理の記録(`state.json`)を残すので、2回目からは**新しい写真だけ**を処理する。

## 準備(初回だけ)

```bash
sudo apt install ffmpeg                  # 入っていなければ
cd timelapse
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/python -m pytest -q            # 4 passed なら OK
```

## フォルダの作り方

被写体(撮る場所・株)ごとにフォルダを分ける。スマホの写真をそのフォルダへ同期する(Nextcloud・Syncthing・手で移す、何でもよい)。

```
~/Nextcloud/畑の写真/            ← これを ROOT として渡す
├── オリーブ1/
│   ├── IMG_1234.HEIC
│   └── …
├── アーティチョーク/
└── _timelapse/                   ← 出力(自動で作られる)
    ├── オリーブ1/
    │   ├── timelapse.mp4         ← できあがり
    │   ├── report.txt            ← 何枚使えたか、合わなかった写真と理由
    │   ├── aligned/              ← 位置合わせ済みの写真
    │   └── state.json            ← 処理の記録(消すと最初からやり直し)
    └── アーティチョーク/
```

- 対応する写真: JPEG・PNG・HEIC(iPhone)
- 名前が `_` や `.` で始まるフォルダは見ない
- 出力を同期フォルダの外に置きたいときは `--out ~/timelapse-out`

## 使い方

```bash
cd timelapse
.venv/bin/field-timelapse build ~/Nextcloud/畑の写真          # 全部の被写体を処理
.venv/bin/field-timelapse build ~/Nextcloud/畑の写真 --subject オリーブ1
.venv/bin/field-timelapse status ~/Nextcloud/畑の写真         # 被写体ごとの状況
```

| オプション | 意味 | 既定 |
|---|---|---|
| `--fps` | 1秒に何日分を見せるか | 8 |
| `--size` | 動画の長辺(画素) | 1920 |
| `--crop` | 四辺を切る割合(端の揺れを隠す) | 0.03 |
| `--no-date` | 撮影日を入れない | 入れる |
| `--reference ファイル名` | 基準の写真を指定(`--subject` と一緒に) | いちばん古い写真 |
| `--rebuild` | 記録を消して最初から作り直す | — |
| `--out` | 出力先 | `<ROOT>/_timelapse` |

## 自動で回す(写真が増えたら作り直す)

```bash
.venv/bin/field-timelapse watch ~/Nextcloud/畑の写真      # 手で試すとき(Ctrl+C で止まる)
```

5分ごとにフォルダを見て、写真が増えていたら処理する。同期の途中を拾わないよう、最後の写真が変わってから2分待つ(`--interval` と `--settle` で変えられる)。

常駐させるときは systemd のユーザーサービスにする:

```bash
# 1. systemd/field-timelapse.service の PHOTOS= を、写真のフォルダに書き換える
cp systemd/field-timelapse.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now field-timelapse
journalctl --user -u field-timelapse -f        # ログを見る
loginctl enable-linger $USER                   # ログアウト中も動かすなら
```

止める: `systemctl --user disable --now field-timelapse`

## 撮り方のコツ(位置合わせが効きやすくなる)

- **毎回だいたい同じ場所・同じ高さ**から撮る。足元に目印(杭・石)を置くと楽
- **動かないものを画面に入れる**: 支柱、杭、畝の端、フェンス、木の幹、遠くの建物。合わせる手がかりになる
- 縦か横かを毎回そろえる。ズームは使わない(いつも等倍)
- 画面いっぱいに葉だけ、空だけ、地面だけ、は合わせにくい
- 逆光・夜は特徴点が減る。同じくらいの時間帯に撮ると、見た目もそろう

## 合わなかったとき

`status` か `report.txt` に、合わなかった写真と理由が出る。

| 理由 | 対処 |
|---|---|
| 対応点が少ない | 撮る範囲が大きく違う・ピンぼけ・暗い。撮り直すか、その写真は外す(フォルダから消せば記録からも消える) |
| 縮尺が大きく違う | 近寄りすぎ・離れすぎ。同じ距離で撮る |
| 基準の構図と重なりが少ない | 向きが大きく違う。基準の写真の向きに合わせて撮る |
| 季節が進んで、だんだん合わなくなってきた | 新しめの写真を基準にして作り直す: `build ROOT --subject 名前 --reference IMG_xxxx.jpg` |

撮影日時が EXIF に無い写真(スクリーンショット・加工した写真など)は、ファイルの日時で並べ、`report.txt` に一覧を出す。

## 開発

```bash
.venv/bin/python -m pytest -q
```

テストは、畑の写真(`web/pages/images/`)を景色とみなして、手持ちのズレ(回転 ±4°・距離 ±7%・移動 ±5%・あおり)と明るさの違い、作物の変化を加えた写真を作り、
推定した変換と本当の変換の誤差を画素で測る(今のところ 0.1px 未満)。

まだやっていないこと: 気象・観測データの焼き込み(EXIF の撮影日時で結び付けられる)。
