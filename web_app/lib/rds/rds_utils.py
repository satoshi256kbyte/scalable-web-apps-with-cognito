from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_rds as rds
from constructs import Construct


def create_rds_instance(
    scope: Construct,
    app_name: str,
    stage: str,
    vpc: ec2.Vpc,
    security_group: ec2.SecurityGroup,
) -> rds.DatabaseInstance:
    """RDSインスタンスを作成する

    Args:
        scope (Construct): 親のConstruct
        app_name (str): アプリケーション名
        stage (str): ステージ名
        vpc (ec2.Vpc): VPC
        security_group (ec2.SecurityGroup): RDS用のセキュリティグループ
    Returns:
        rds.DatabaseInstance: RDSインスタンス
    """

    db_subnet_group = rds.SubnetGroup(
        scope,
        id=f"{app_name}_{stage}_db_subnet_group",
        subnet_group_name=f"{app_name}-{stage}-db-subnet-group",
        description="DB subnet group",
        vpc=vpc,
        vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
    )

    return rds.DatabaseInstance(
        scope,
        id=f"{app_name}_{stage}_rds",
        database_name=f"{app_name}_{stage}_rds",
        instance_identifier=f"{app_name}-{stage}-rds",
        engine=rds.DatabaseInstanceEngine.postgres(
            version=rds.PostgresEngineVersion.VER_17_2
        ),
        instance_type=ec2.InstanceType.of(
            instance_class=ec2.InstanceClass.BURSTABLE4_GRAVITON,
            instance_size=ec2.InstanceSize.MICRO,
        ),
        vpc=vpc,
        security_groups=[security_group],
        subnet_group=db_subnet_group,
    )
