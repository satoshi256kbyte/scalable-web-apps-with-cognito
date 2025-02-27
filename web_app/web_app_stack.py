from aws_cdk import Stack, Tags
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from constructs import Construct

from web_app.lib.cognito.simple_user_pool import SimpleUserPool
from web_app.lib.ec2.ec2_utils import create_web_ec2_instance
from web_app.lib.elb.elb_utils import create_alb_instance
from web_app.lib.rds.rds_utils import create_rds_instance
from web_app.lib.vpc.simple_web_app_vpc import SimpleWebAppVPC


class WebAppStack(Stack):

    app_name: str
    stage: str

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        app_name: str = self.node.try_get_context("app_name")
        if app_name is None:
            app_name = "web-app"
        stage = app_name.lower()

        stage: str = self.node.try_get_context("stage")
        if stage is None:
            raise ValueError("stage is required")
        stage = stage.lower()

        key_pair_param: str = self.node.try_get_context("key_pair")
        if key_pair_param is None:
            raise ValueError("key_pair is required")

        certificate_arn_param: str = self.node.try_get_context("certificate_arn")
        if certificate_arn_param is None:
            raise ValueError("certificate_arn is required")

        # 全体にタグを付与
        Tags.of(self).add("app_name", app_name)
        Tags.of(self).add("stage", stage)

        simple_vpc = SimpleWebAppVPC(self, app_name, stage)

        # EC2用のインスタンスプロファイル
        # セッションマネージャーを使うためのマネージドポリシーをアタッチ
        instance_profile = iam.Role(
            scope=self,
            id=f"{app_name}_{stage}_web_ec2_role",
            role_name=f"{app_name}-{stage}-web-ec2-role",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            description="for instance profile",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMManagedInstanceCore"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonS3ReadOnlyAccess"
                ),
            ],
        )

        # EC2はALB配下に2つ設置するのでEC2を2台起動
        ec2_instance_1 = create_web_ec2_instance(
            scope=self,
            app_name=app_name,
            stage=stage,
            suffix="1",
            vpc=simple_vpc.get_vpc(),
            security_group=simple_vpc.get_web_sg(),
            instance_profile=instance_profile,
            key_pair_name=key_pair_param,
        )
        ec2_instance_2 = create_web_ec2_instance(
            scope=self,
            app_name=app_name,
            stage=stage,
            suffix="2",
            vpc=simple_vpc.get_vpc(),
            security_group=simple_vpc.get_web_sg(),
            instance_profile=instance_profile,
            key_pair_name=key_pair_param,
        )

        _ = create_rds_instance(
            scope=self,
            app_name=app_name,
            stage=stage,
            vpc=simple_vpc.get_vpc(),
            security_group=simple_vpc.get_db_sg(),
        )
        
        # Cognitoユーザープールを作成
        simple_user_pool = SimpleUserPool(self, app_name, stage)

        _ = create_alb_instance(
            scope=self,
            app_name=app_name,
            stage=stage,
            vpc=simple_vpc.get_vpc(),
            security_group=simple_vpc.get_elb_sg(),
            ec2_instances=[ec2_instance_1, ec2_instance_2],
            user_pool=simple_user_pool.get_user_pool(),
            user_pool_client=simple_user_pool.get_user_pool_client(),
            user_pool_domain=simple_user_pool.get_user_pool_domain(),
            certificate_arn=certificate_arn_param,
        )

        fn = _lambda.Function(
            self,
            id=f"{app_name}_{stage}_lambda_handler",
            function_name=f"{app_name}-{stage}-lambda-handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="hello_world.handler",
            code=_lambda.Code.from_asset("src"),
        )

        # API Gatewayを作成
        # ALBに設定したものと同じCognito認証を設定する
        cognito_authorizer = apigw.CognitoUserPoolsAuthorizer(
            self,
            id=f"{app_name}_{stage}_cognito_authorizer",
            cognito_user_pools=[simple_user_pool.get_user_pool()],
            authorizer_name=f"{app_name}-{stage}-cognito-authorizer",
        )

        rest_api = apigw.RestApi(
            self,
            id=f"{app_name}_{stage}_api",
            rest_api_name=f"{app_name}-{stage}-api",
        )

        rest_api.root.add_method(
            "GET",
            apigw.LambdaIntegration(fn),
            authorizer=cognito_authorizer,
        )
