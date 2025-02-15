## AWS CDK のインストール

asdfはインストール済みとします。
本記事執筆時点（2025年2月）ではAWS CDKはNode.jsの22系までしか動作確認されてないようなので、22系の最新版をインストールします。

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

作成した`Pipfile`でライブラリをインストールします。

```bash
pip install pipenv
pipenv install --dev
```

