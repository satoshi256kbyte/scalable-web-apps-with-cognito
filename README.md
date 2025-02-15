
# Amazon Cognito で構築する スケーラブルな Web アプリケーション

## 開発環境準備

### 前提条件
OSはLinuxを想定しています。
以下ツールがセットアップ済みであることを前提とします。

* [AWS CLI](https://aws.amazon.com/cli/)
* [AWS CDK](https://docs.aws.amazon.com/ja_jp/cdk/v2/guide/home.html)
* [asdf](https://asdf-vm.com/)
* [Pipenv](https://pipenv.pypa.io/en/latest/)

### ライブラリのインストール

```bash
pipenv install --dev
```

### テストの実行

```bash
pipenv run pytest
```

### Lint＆フォーマット

```bash
pipenv run lint
```

```bash
pipenv run format
```

### デプロイ

#### 初回のデプロイ時のみのコマンド

```bash
cdk bootstrap
```

#### デプロイ

```bash
pipenv install
cdk deploy -c key_pair=YOUR_KEY_PAIR_NAME
```

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

## [補足]各種ツールのインストールとプロジェクトの作成手順

### asdfとpipenvのインストール


#### asdfのインストール

https://asdf-vm.com/ja-jp/guide/getting-started.html

```bash
git clone https://github.com/asdf-vm/asdf.git ~/.asdf --branch v0.14.0
```

#### Pythonのインストール

```bash
asdf plugin add python
asdf install python 3.13.0
asdl local python 3.13.0
```

#### Pipenvのインストール

```bash
pip install pipenv
```

### AWS CDK のインストール

執筆時点（2025年2月）ではAWS CDKはNode.jsの22系までしか動作確認されてないようなので、22系の最新版をインストールします。

asdfにNode.jsプラグインを追加します。

```bash
asdf plugin-add nodejs
```

asdfでNode.jsのバージョンリストを確認し、22系の最新版をインストールします。

```bash
asdf list all nodejs
asdf install nodejs 22.14.0
```

[AWS CDKの公式ページ](https://docs.aws.amazon.com/ja_jp/cdk/v2/guide/getting_started.html)に従い、CDKをインストールします。

```bash
npm install -g aws-cdk
```

### AWS CDKでプロジェクトを作成

AWS CDKでプロジェクトを作成します。
言語はPythonを選択します。

```bash
mkdir web-app && cd web-app
cdk init app --language python
```

仮装環境を作成します。

```bash
source .venv/bin/activate
```

私は`requirements.txt`と`requirements-dev.txt`をそのまま使うのは避けたいので、これらから`Pipfile`を生成します。

```pipfile
[packages]
aws-cdk-lib = "==2.178.2"
constructs = ">=10.0.0,<11.0.0"

[dev-packages]
pytest = "==6.2.5"
```
