from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticloadbalancingv2 as elb
from aws_cdk import aws_elasticloadbalancingv2_targets as tg
from aws_cdk import aws_iam as iam
from aws_cdk import aws_rds as rds
from constructs import Construct


class WebAppStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # EC2のキーペア名を外部から指定
        key_pair_param: str = self.node.try_get_context("key_pair")
        if key_pair_param is None:
            raise ValueError("key_pair is required")

        # EC2用のインスタンスプロファイル
        # セッションマネージャーを使うためのマネージドポリシーをアタッチ
        instance_profile = iam.Role(
            self,
            "ec2_profile",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            description="for instance profile",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMManagedInstanceCore"
                ),
            ],
        )

        # VPC
        # パブリックサブネット、NATゲートウェイに接続したプライベートサブネット、DB用のプライベートサブネットを作成
        # DB用のプライベートサブネットはNATゲートウェイには接続しない
        vpc = ec2.Vpc(
            self,
            "web_vpc",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public_subnet", subnet_type=ec2.SubnetType.PUBLIC
                ),
                ec2.SubnetConfiguration(
                    name="protected_subnet", subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT
                ),
                ec2.SubnetConfiguration(
                    name="db_subnet", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
                ),
            ],
        )

        # ALB、EC2、RDSそれぞれのセキュリティグループ
        alb_sg = ec2.SecurityGroup(
            self,
            "alb_sg",
            vpc=vpc,
            allow_all_outbound=True,
        )
        alb_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
        )
        ec2_sg = ec2.SecurityGroup(
            self,
            "ec2_sg",
            vpc=vpc,
            allow_all_outbound=True,
        )
        ec2_sg.add_ingress_rule(
            peer=alb_sg,
            connection=ec2.Port.tcp(80),
        )
        rds_sg = ec2.SecurityGroup(
            self,
            "rds_sg",
            vpc=vpc,
            allow_all_outbound=True,
        )
        rds_sg.add_ingress_rule(
            peer=ec2_sg,
            connection=ec2.Port.tcp(3306),
        )

        # EC2
        # WEBサーバー用に2台起動
        ec2_instance_1 = ec2.Instance(
            self,
            "web_ec2_instance_1",
            vpc=vpc,
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3A, ec2.InstanceSize.MICRO
            ),
            machine_image=ec2.MachineImage.latest_amazon_linux(
                generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2023
            ),
            instance_name="web-instance",
            key_name=key_pair_param,
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/xvda", volume=ec2.BlockDeviceVolume.ebs(10)
                )
            ],
            role=instance_profile,
            security_group=ec2_sg,
        )
        ec2_instance_2 = ec2.Instance(
            self,
            "web_ec2_instance_2",
            vpc=vpc,
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3A, ec2.InstanceSize.MICRO
            ),
            machine_image=ec2.MachineImage.latest_amazon_linux(
                generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2023
            ),
            instance_name="web-instance",
            key_name=key_pair_param,
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/xvda", volume=ec2.BlockDeviceVolume.ebs(10)
                )
            ],
            role=instance_profile,
            security_group=ec2_sg,
        )

        db_subnet_group = rds.SubnetGroup(
            self,
            id="db_subnet_group",
            description="DB subnet group",
            subnet_group_name="db_subnet_group",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
        )

        _ = rds.DatabaseInstance(
            self,
            "web-rds",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_17_2
            ),
            vpc=vpc,
            security_groups=[rds_sg],
            subnet_group=db_subnet_group,
        )

        alb = elb.ApplicationLoadBalancer(
            self,
            "alb",
            vpc=vpc,
            internet_facing=True,
        )
        listener = alb.add_listener("listener", port=80)
        listener.add_targets(
            "target",
            port=80,
            targets=[
                tg.InstanceIdTarget(instance_id=ec2_instance_1.instance_id),
                tg.InstanceIdTarget(instance_id=ec2_instance_2.instance_id),
            ],
            health_check=elb.HealthCheck(
                path="/index.html",
            ),
        )
