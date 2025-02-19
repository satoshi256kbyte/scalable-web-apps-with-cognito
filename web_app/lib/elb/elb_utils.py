from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticloadbalancingv2 as elb
from aws_cdk import aws_elasticloadbalancingv2_actions as actions
from aws_cdk import aws_elasticloadbalancingv2_targets as tg
from constructs import Construct


def create_alb_instance(
    scope: Construct,
    app_name: str,
    stage: str,
    vpc: ec2.Vpc,
    security_group: ec2.SecurityGroup,
    ec2_instances: list[ec2.Instance],
    user_pool: cognito.UserPool,
    user_pool_client: cognito.UserPoolClient,
    user_pool_domain: cognito.UserPoolDomain,
    certificate_arn: str,
) -> elb.ApplicationLoadBalancer:
    """ALBを作成する

    Args:
        scope (Construct): 親のConstruct
        app_name (str): アプリケーション名
        stage (str): ステージ名
        vpc (ec2.Vpc): VPC
        security_group (ec2.SecurityGroup): ALB用のセキュリティグループ
        ec2_instances (List[ec2.Instance]): ターゲットとなるEC2インスタンスのリスト
        user_pool (cognito.UserPool): Cognitoユーザープール
        user_pool_client (cognito.UserPoolClient): Cognitoユーザープールクライアント
        user_pool_domain (cognito.UserPoolDomain): Cognitoユーザープールドメイン
        certificate_arn (str): 証明書のARN
    Returns:
        elb.ApplicationLoadBalancer: ALB
    """
    alb: elb.ApplicationLoadBalancer = elb.ApplicationLoadBalancer(
        scope,
        id=f"{app_name}_{stage}_alb",
        load_balancer_name=f"{app_name}-{stage}-alb",
        vpc=vpc,
        security_group=security_group,
        internet_facing=True,
    )

    certificate: acm.Certificate = acm.Certificate.from_certificate_arn(
        scope, f"{app_name}_{stage}_certificate", certificate_arn
    )

    # ターゲットグループの作成
    target_group: elb.ApplicationTargetGroup = elb.ApplicationTargetGroup(
        scope,
        id=f"{app_name}_{stage}_target_group",
        target_group_name=f"{app_name}-{stage}-target-group",
        port=80,
        vpc=vpc,
        protocol=elb.ApplicationProtocol.HTTP,
        targets=[
            tg.InstanceIdTarget(instance_id=ec2_instance.instance_id)
            for ec2_instance in ec2_instances
        ],
        health_check=elb.HealthCheck(
            path="/health_check.html",
            protocol=elb.Protocol.HTTP,
        ),
    )

    listener = alb.add_listener("listener", port=443, certificates=[certificate])
    # `/member/`から始まるURLの場合、Cognito認証を適用
    listener.add_action(
        id=f"{app_name}_{stage}_auth_action",
        priority=1,  # 優先順位（低いほど優先される）
        conditions=[
            elb.ListenerCondition.path_patterns(["/member/*"]),
        ],
        action=actions.AuthenticateCognitoAction(
            user_pool=user_pool,
            user_pool_client=user_pool_client,
            user_pool_domain=user_pool_domain,
            next=elb.ListenerAction.forward([target_group]),
        ),
    )

    # それ以外のURLはそのままターゲットグループにフォワード
    listener.add_target_groups(
        id=f"{app_name}_{stage}_default_action", target_groups=[target_group]
    )

    return alb
