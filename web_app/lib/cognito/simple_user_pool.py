from aws_cdk import aws_cognito as cognito
from constructs import Construct


class SimpleUserPool(Construct):
    """一般的なAmazon Cognitoユーザープールを構築するモジュール"""

    _user_pool: cognito.UserPool
    _user_pool_client: cognito.UserPoolClient
    _user_pool_domain: cognito.UserPoolDomain

    def __init__(self, scope: Construct, app_name: str, stage: str) -> None:
        """コンストラクタ

        Args:
            scope (Construct): 親のConstruct
            app_name (str): アプリケーション名
            stage (str): ステージ名
        """
        super().__init__(scope, f"{app_name}_{stage}_simple_user_pool")

        self._user_pool = cognito.UserPool(
            self,
            id=f"{app_name}_{stage}_user_pool",
            user_pool_name=f"{app_name}-{stage}-user-pool",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(
                email=True,
                username=False,
            ),
            auto_verify=cognito.AutoVerifiedAttrs(
                email=True,
            ),
        )

        self._user_pool_client: cognito.UserPoolClient = cognito.UserPoolClient(
            self,
            id=f"{app_name}_{stage}_user_pool_client",
            user_pool=self._user_pool,
            user_pool_client_name=f"{app_name}-{stage}-user-pool-client",
            generate_secret=True,
        )

        self._user_pool_domain: cognito.UserPoolDomain = cognito.UserPoolDomain(
            self,
            id=f"{app_name}_{stage}_user_pool_domain",
            user_pool=self._user_pool,
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=f"{app_name}-{stage}-auth",
            ),
        )

    def get_user_pool(self) -> cognito.UserPool:
        """ユーザープールを取得する"""
        return self._user_pool

    def get_user_pool_client(self) -> cognito.UserPoolClient:
        """ユーザープールクライアントを取得する"""
        return self._user_pool_client

    def get_user_pool_domain(self) -> cognito.UserPoolDomain:
        """ユーザープールドメインを取得する"""
        return self._user_pool_domain
