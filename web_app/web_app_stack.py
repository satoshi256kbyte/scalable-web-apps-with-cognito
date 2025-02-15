from aws_cdk import Stack, Tags
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticloadbalancingv2 as elb
from aws_cdk import aws_elasticloadbalancingv2_targets as tg
from aws_cdk import aws_iam as iam
from aws_cdk import aws_rds as rds
from constructs import Construct


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

        # 全体にタグを付与
        Tags.of(self).add("app_name", app_name)
        Tags.of(self).add("stage", stage)

        # VPC
        # パブリックサブネット、NATゲートウェイに接続したプライベートサブネット、DB用のプライベートサブネットを作成
        # DB用のプライベートサブネットはNATゲートウェイには接続しない
        vpc = ec2.Vpc(
            self,
            id=f"{app_name}_{stage}_vpc",
            vpc_name=f"{app_name}-{stage}-vpc",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name=f"{app_name}-{stage}-public-subnet",
                    subnet_type=ec2.SubnetType.PUBLIC,
                ),
                ec2.SubnetConfiguration(
                    name=f"{app_name}-{stage}-protected-subnet",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT,
                ),
                ec2.SubnetConfiguration(
                    name=f"{app_name}-{stage}-private-subnet",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                ),
            ],
        )

        # ALB、EC2、RDSそれぞれのセキュリティグループ
        alb_sg = ec2.SecurityGroup(
            self,
            id=f"{app_name}_{stage}_alb_sg",
            security_group_name=f"{app_name}-{stage}-alb-sg",
            vpc=vpc,
            allow_all_outbound=True,
        )
        alb_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
        )
        ec2_sg = ec2.SecurityGroup(
            self,
            id=f"{app_name}_{stage}_web_ec2_sg",
            security_group_name=f"{app_name}-{stage}-web-ec2-sg",
            vpc=vpc,
            allow_all_outbound=True,
        )
        ec2_sg.add_ingress_rule(
            peer=alb_sg,
            connection=ec2.Port.tcp(80),
        )
        rds_sg = ec2.SecurityGroup(
            self,
            id=f"{app_name}_{stage}_rds_sg",
            security_group_name=f"{app_name}-{stage}-rds-sg",
            vpc=vpc,
            allow_all_outbound=True,
        )
        rds_sg.add_ingress_rule(
            peer=ec2_sg,
            connection=ec2.Port.tcp(3306),
        )

        # EC2用のインスタンスプロファイル
        # セッションマネージャーを使うためのマネージドポリシーをアタッチ
        instance_profile: iam.Role = iam.Role(
            self,
            id=f"{app_name}_{stage}_web_ec2_role",
            role_name=f"{app_name}-{stage}-web-ec2-role",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            description="for instance profile",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMManagedInstanceCore"
                ),
            ],
        )

        # EC2はALB配下に2つ設置するのでEC2を2台起動
        ec2_instance_1 = self.create_web_ec2_instance(
            app_name, stage, "1", vpc, instance_profile, ec2_sg
        )
        ec2_instance_2 = self.create_web_ec2_instance(
            app_name, stage, "2", vpc, instance_profile, ec2_sg
        )

        _ = self.create_rds_instance(app_name, stage, vpc, rds_sg)
        _ = self.create_alb(app_name, stage, vpc, [ec2_instance_1, ec2_instance_2])

    def create_web_ec2_instance(
        self,
        app_name: str,
        stage: str,
        suffix: str,
        vpc: ec2.Vpc,
        instance_profile: iam.Role,
        ec2_sg: ec2.SecurityGroup,
    ) -> ec2.Instance:
        """Webサーバー用のEC2インスタンスを作成する

        Args:
            app_name (str): アプリケーション名
            stage (str): ステージ名
            vpc (ec2.Vpc): VPC
            suffix (str): インスタンス名のサフィックス
            instance_profile (iam.Role): インスタンスプロファイル
            ec2_sg (ec2.SecurityGroup): EC2インスタンス用のセキュリティグループ
        Returns:
            ec2.SecurityGroup: EC2インスタンス
        """

        key_pair_param: str = self.node.try_get_context("key_pair")

        return ec2.Instance(
            self,
            id=f"{app_name}_{stage}_web_ec2_{suffix}",
            instance_name=f"{app_name}-{stage}-web-ec2-{suffix}",
            vpc=vpc,
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3A, ec2.InstanceSize.MICRO
            ),
            machine_image=ec2.MachineImage.latest_amazon_linux(
                generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2023
            ),
            key_name=key_pair_param,
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/xvda", volume=ec2.BlockDeviceVolume.ebs(10)
                )
            ],
            role=instance_profile,
            security_group=ec2_sg,
        )

    # RDSインスタンスを作るメソッド
    def create_rds_instance(
        self,
        app_name: str,
        stage: str,
        vpc: ec2.Vpc,
        rds_sg: ec2.SecurityGroup,
    ) -> rds.DatabaseInstance:
        """RDSインスタンスを作成する

        Args:
            app_name (str): アプリケーション名
            stage (str): ステージ名
            vpc (ec2.Vpc): VPC
            rds_sg (ec2.SecurityGroup): RDS用のセキュリティグループ
        Returns:
            rds.DatabaseInstance: RDSインスタンス
        """

        db_subnet_group = rds.SubnetGroup(
            self,
            id=f"{app_name}_{stage}_db_subnet_group",
            subnet_group_name=f"{app_name}-{stage}-db-subnet-group",
            description="DB subnet group",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
        )

        return rds.DatabaseInstance(
            self,
            id=f"{app_name}_{stage}_rds",
            database_name=f"{app_name}_{stage}_rds",
            instance_identifier=f"{app_name}-{stage}-rds",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_17_2
            ),
            vpc=vpc,
            security_groups=[rds_sg],
            subnet_group=db_subnet_group,
        )

    # ALBを作るメソッド
    # ターゲットのEC2インスタンスはリストで受け取る

    def create_alb(
        self, app_name: str, stage: str, vpc: ec2.Vpc, ec2_instances: list[ec2.Instance]
    ) -> elb.ApplicationLoadBalancer:
        """ALBを作成する

        Args:
            app_name (str): アプリケーション名
            stage (str): ステージ名
            vpc (ec2.Vpc): VPC
            ec2_instances (List[ec2.Instance]): ターゲットとなるEC2インスタンスのリスト
        Returns:
            elb.ApplicationLoadBalancer: ALB
        """
        alb: elb.ApplicationLoadBalancer = elb.ApplicationLoadBalancer(
            self,
            id=f"{app_name}_{stage}_alb",
            load_balancer_name=f"{app_name}-{stage}-alb",
            vpc=vpc,
            internet_facing=True,
        )

        listener = alb.add_listener("listener", port=80)
        listener.add_targets(
            "target",
            port=80,
            targets=[
                tg.InstanceIdTarget(instance_id=ec2_instance.instance_id)
                for ec2_instance in ec2_instances
            ],
            health_check=elb.HealthCheck(
                path="/index.html",
            ),
        )

        return alb
